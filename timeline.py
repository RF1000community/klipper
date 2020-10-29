# coding: utf-8
from datetime import date
from os.path import splitext, basename

from kivy.app import App
from kivy.properties import (NumericProperty, StringProperty, BooleanProperty,
        OptionProperty, ObjectProperty)
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior

from .elements import StopPopup
from . import parameters as p


class Timeline(RecycleView):
    path = StringProperty()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.reactor = self.app.reactor
        self.load_all(in_background=False)
        self.app.bind(jobs=self.load_all, state=self.load_all, print_state=self.load_all)

    def load_all(self, instance=None, value=None, in_background=True):
        queue = [{'name': job.name, 'path': job.path, 'state': job.state} 
            for job in reversed(self.app.jobs)]

        history = []
        if self.app.history and self.app.history.history != []:
            # latest date in history
            prev_date = date.fromtimestamp(self.app.history.history[0][2])
            for job in self.app.history.history:
                new_date = date.fromtimestamp(job[2])
                # This print happened on a later day than the previous
                if new_date != prev_date:
                    # Format date like "25. Aug 1991"
                    history.append({"name": prev_date.strftime("%d. %b %Y")})
                    prev_date = new_date
                new = {"path": job[0],
                    "state": job[1],
                    "timestamp": job[2],
                    "name": splitext(basename(job[0]))[0]}
                history.append(new)
            # Also show the newest date, but not if the last print happened today
            if new_date != date.today():
                history.append({"name": new_date.strftime("%d. %b %Y")})
            history.reverse() # sort history to last file at end (bottom)

        if not (queue or history): # Give message in case of empty list
            self.data = [{"name": "No printjobs scheduled or finished", "state": 'message'}]
        else:
            self.data = queue + history + [{}] # for a dividing line after last element
        self.refresh_from_data()
        if not in_background and 'tl_box' in self.ids:
            self.ids.tl_box.clear_selection()
            self.scroll_y = 1

    def move(self, offset):
        """Move the selected file up or down the queue. E.g. -1 will print it sooner"""
        selected = self.ids.tl_box.selected_nodes
        if not selected: return
        i = len(self.app.sdcard.jobs) - selected[0] - 1

        def move(e):
            if  0 < i+offset < len(self.app.sdcard.jobs):
                to_move = self.app.sdcard.jobs.pop(i)
                self.app.sdcard.jobs.insert(i + offset, to_move)
                self.app.sdcard.queue_modified()
        # do the check twice, since it's easy to press this button again when it should have already disappeared
        if  0 < i+offset < len(self.app.sdcard.jobs):
            self.reactor.register_async_callback(move)
            self.ids.tl_box.select_node(selected[0] - offset)

    def remove(self):
        """Remove the selcted file from the queue"""
        selected = self.ids.tl_box.selected_nodes
        if not selected: return
        i = len(self.app.sdcard.jobs) - selected[0] - 1

        def remove(e):
            if  0 < i < len(self.app.sdcard.jobs):
                self.app.sdcard.jobs.pop(i)
                self.app.sdcard.queue_modified()

        if i == 0:
            StopPopup().open()
        else: # negative values would occur for history items below current
            self.ids.tl_box.clear_selection()
            self.reactor.register_async_callback(remove)


class TimelineBox(LayoutSelectionBehavior, RecycleBoxLayout):
    # Adds selection behaviour to the view, modified to also store selected Widget (selected_object), not just index (selected_nodes)
    selected_object = ObjectProperty(None, allownone=True)
    def select_node(self, node):
        super().select_node(node)
        self.selected_object = self.recycleview.view_adapter.get_visible_view(node) # set after super().select.. it deselects before selecting
    def deselect_node(self, node):
        if node in self.selected_nodes: # check before super().deselect...
            self.selected_object = None
        super().deselect_node(node)


class TimelineItem(RecycleDataViewBehavior, Label):
    name = StringProperty()
    path = StringProperty()
    state = OptionProperty("header", options=
        ["header", "message", "queued", "printing", "pausing", "paused", "stopping", "stopped", "done"])
    timestamp = NumericProperty(0)
    index = None
    selected = BooleanProperty(False)
    pressed = BooleanProperty(False)
    thumbnail = StringProperty("")

    def refresh_view_attrs(self, rv, index, data):
        # Catch and handle the view changes
        self.index = index
        # Default has to be explicitly set for some reason
        default_data = {'name': "", 'path': "", 'selected': False, "state": 'header', "timestamp": 0}
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
