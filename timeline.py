# coding: utf-8
import json
import logging
from datetime import date
from os.path import splitext, basename, exists

from kivy.app import App
from kivy.properties import (ListProperty, NumericProperty, StringProperty,
    BooleanProperty, OptionProperty, ObjectProperty)
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior

from . import parameters as p
from .elements import StopPopup

class Timeline(RecycleView):
    path = StringProperty()
    # Initially is None, then always the last selected view object
    selected = ObjectProperty(None)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.load_all(in_background=False)
        self.app.bind(jobs=self.load_all)
        self.app.bind(state=self.load_all)
        self.app.bind(print_state=self.load_all)

    def load_all(self, instance=None, value=None, in_background=True):
        queue = [{'name': job.name, 'path': job.path, 'state': job.state} 
            for job in reversed(self.app.jobs)]

        history = []
        if self.app.history and self.app.history.history != []:
            # latest date in history
            prev_date = date.fromtimestamp(self.app.history.history[0][2])
            for job in self.app.history.history: #TODO use reversed instead of insert for speed
                new_date = date.fromtimestamp(job[2])
                # This print happened on a later day than the previous
                if new_date != prev_date:
                    # Format date like "25. Aug 1991"
                    history.insert(0, {"name": prev_date.strftime("%d. %b %Y")})
                    prev_date = new_date
                new = {"path": job[0],
                    "state": job[1],
                    "timestamp": job[2],
                    "name": splitext(basename(job[0]))[0]}
                history.insert(0, new)
            # history is sorted last file at end
            # Also show the newest date, but not if the last print happened today
            if new_date != date.today():
                history.insert(0, {"name": new_date.strftime("%d. %b %Y")})

        if len(queue) + len(history) == 0: # Give message in case of empty list
            self.data = [{"name": "No printjobs scheduled or finished", "state": 'message'}]
        else:
            self.data = queue + history + [{}] # for a dividing line afer last element
        self.refresh_from_data()
        if not in_background and 'tl_box' in self.ids:
            self.ids.tl_box.selected_nodes = []
            self.scroll_y = 1

    def send_queue(self, queue):
        """
        Send the updated queue back to the virtual sdcard
        Will fail in testing
        """
        self.app.sdcard.clear_queue() # Clears everything except for the first entry
        for path in queue[1:]:
            self.app.sdcard.add_printjob(path)

    def move_up(self):
        """Move the selected file up one step in the queue"""
        i = self.ids.tl_box.selected_nodes[0]
        queue = self.app.jobs
        if len(queue) > i:
            to_move = queue.pop(i)
            queue.insert(i - 1, to_move)
            self.ids.tl_box.selected_nodes = [i - 1]
            self.send_queue(queue)

    def move_down(self):
        """Move the selected file down one step in the queue"""
        i = self.ids.tl_box.selected_nodes[0]
        queue = self.app.jobs
        if len(queue) > i:
            to_move = queue.pop(i)
            queue.insert(i + 1, to_move)
            self.ids.tl_box.selected_nodes = [i + 1]
            self.send_queue(queue)

    def remove(self):
        """Remove the selcted file from the queue"""
        i = self.ids.tl_box.selected_nodes[0]
        queue = self.app.jobs
        if i == 0:
            StopPopup().open()
        elif len(queue) > i:
            queue.pop(i)
            self.ids.tl_box.selected_nodes = []
            self.send_queue(queue)

class TimelineBox(LayoutSelectionBehavior, RecycleBoxLayout):
    # Adds selection behaviour to the view
    pass

class TimelineItem(RecycleDataViewBehavior, Label):
    name = StringProperty()
    path = StringProperty()
    state = OptionProperty("header", options=["header", "message", "queued", "printing", "pausing", "paused", "stopping", "stopped", "done"])
    timestamp = NumericProperty(0)
    index = None # TODO ?
    selected = BooleanProperty(False)
    pressed = BooleanProperty(False)
    thumbnail = StringProperty("")

    def refresh_view_attrs(self, rv, index, data):
        # Catch and handle the view changes
        self.index = index
        # Default has to be explicitly set for some reason
        default_data = {"name": "", "path": "", "selected": False,
                "state": "header", "timestamp": 0}
        default_data.update(data)
        return super().refresh_view_attrs(rv, index, default_data)

    def on_touch_down(self, touch):
        # Add selection on touch down
        if super().on_touch_down(touch):
            return True
        if self.state == "header":
            return False
        if self.collide_point(*touch.pos):
            self.pressed = True
            self.parent.select_with_touch(self.index, touch)
            return True

    def on_touch_up(self, touch):
        was_pressed = self.pressed
        self.pressed = False
        if super().on_touch_up(touch):
            return True
        if self.collide_point(*touch.pos) and was_pressed:
            return True
        return False

    def apply_selection(self, rv, index, is_selected):
        # Respond to the selection of items in the view
        self.selected = is_selected
        if is_selected:
            rv.selected = self
