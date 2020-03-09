# coding: utf-8
from datetime import date
import json
import logging
from os.path import basename, exists
import time

from kivy.app import App
from kivy.event import EventDispatcher
from kivy.properties import (ListProperty, NumericProperty, StringProperty,
    BooleanProperty, OptionProperty, ObjectProperty)
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior

import parameters as p


class Timeline(RecycleView):
    path = StringProperty()
    # Initially is None, then always the last selected view object
    selected = ObjectProperty(None)
    def __init__(self, **kwargs):
        super(Timeline, self).__init__(**kwargs)
        self.app = App.get_running_app()
        self.load_all(in_background=False)
        self.app.bind(queued_files=self.load_all)
        self.app.bind(print_state=self.load_all)
        self.app.history.bind(history=self.load_all)

    def load_all(self, instance=None, value=None, in_background=True):
        queue = []
        #TEST
        testq = ["/path/{}.gco".format(i) for i in range(10)]
        for i, e in enumerate(testq): #self.app.queued_files):
            new = {}
            new["name"] = basename(e)
            new["details"] = (self.app.print_state.capitalize() if i == 0 else "{}.".format(i))
            new["path"] = e
            new["status"] = "queued"
            queue.insert(0, new) # next queue item is displayed last

        history = []
        if self.app.history.history != []:
            # latest date in history
            prev_date = date.fromtimestamp(self.app.history.history[0][2])
            for e in self.app.history.history:
                new_date = date.fromtimestamp(e[2])
                # This print happened on a later day than the previous
                if new_date != prev_date:
                    # Format date like "25. Aug 1991"
                    history.insert(0, {"details": prev_date.strftime("%d. %b %Y")})
                    prev_date = new_date
                new = {}
                new["path"], new["status"], new["timestamp"] = e
                new["name"] = basename(e[0])
                new["details"] = e[1].capitalize() # "stopped" or "done"
                history.insert(0, new) # history is sorted last file at end
            # Also show the newest date, but not if the last print happened today
            if new_date != date.today():
                history.insert(0, {"details": new_date.strftime("%d. %b %Y")})

        if self.app.print_state in {"printing", "paused"}:
            queue[-1]["status"] = self.app.print_state
        #TEST: Breaks status details a bit, but shows an example of printing files
        queue.append({"name": "print.gco", "path": "/sdcard/print.gco", "status": "paused", "details": "Paused"})

        if len(queue) > 1:
            queue.insert(0, {"name": "Queue:"})
        if len(history) >= 1:
            history.insert(0, {"name": "History:"})

        if len(queue) + len(history) == 0: # Give message in case of empty list
            self.data = [{"details": "No printjobs scheduled or finished"}]
        else:
            self.data = queue + history
        self.refresh_from_data()
        if not in_background and 'fc_box' in self.ids:
            self.ids.fc_box.selected_nodes = []
            self.scroll_y = 1

    def send_queue(self, queue):
        """
        Send the updated queue back to the virtual sdcard
        Will fail in testing
        """
        sdcard = self.app.sdcard
        sdcard.clear_queue() # Clears everything except for the first entry
        self.app.queued_files = queue
        for path in self.queued_files[1:]:
            sdcard.add_printjob(path)

    def move_up(self):
        """Move the selected file up one step in the queue"""
        i = self.ids.fc_box.selected_nodes[0]
        queue = self.app.queued_files
        if len(queue) > i:
            to_move = queue.pop(i)
            queue.insert(i - 1, to_move)
            self.ids.fc_box.selected_nodes = [i - 1]
            self.send_queue(queue)

    def move_down(self):
        """Move the selected file down one step in the queue"""
        i = self.ids.fc_box.selected_nodes[0]
        queue = self.app.queued_files
        if len(queue) > i:
            to_move = queue.pop(i)
            queue.insert(i + 1, to_move)
            self.ids.fc_box.selected_nodes = [i + 1]
            self.send_queue(queue)

    def remove(self):
        """Remove the selcted file from the queue"""
        i = self.ids.fc_box.selected_nodes[0]
        queue = self.app.queued_files
        if i == 0:
            StopPopup().open()
        elif len(queue) > i:
            to_remove = queue.pop(i)
            self.ids.fc_box.selected_nodes = []
            self.send_queue(queue)

class TimelineBox(LayoutSelectionBehavior, RecycleBoxLayout):
    # Adds selection behaviour to the view
    pass

class TimelineItem(RecycleDataViewBehavior, Label):
    name = StringProperty()
    path = StringProperty()
    details = StringProperty()
    status = OptionProperty("header", options=["header", "queued", "printing", "paused", "stopped", "done"])
    timestamp = NumericProperty(0)
    index = None
    selected = BooleanProperty(False)
    pressed = BooleanProperty(False)

    def refresh_view_attrs(self, rv, index, data):
        # Catch and handle the view changes
        self.index = index
        # Default has to be explicitly set for some reason
        default_data = {"name": "", "path": "", "details": "",
                "status": "header", "timestamp": 0}
        default_data.update(data)
        return super(TimelineItem, self).refresh_view_attrs(rv, index, default_data)

    def on_touch_down(self, touch):
        # Add selection on touch down
        if super(TimelineItem, self).on_touch_down(touch):
            return True
        if self.status == "header":
            return False
        if self.collide_point(*touch.pos):
            self.pressed = True
            self.parent.select_with_touch(self.index, touch)
            return True

    def on_touch_up(self, touch):
        was_pressed = self.pressed
        self.pressed = False
        if super(TimelineItem, self).on_touch_up(touch):
            return True
        if self.collide_point(*touch.pos) and was_pressed:
            return True
        return False

    def apply_selection(self, rv, index, is_selected):
        # Respond to the selection of items in the view
        self.selected = is_selected
        if is_selected:
            rv.selected = self


class History(EventDispatcher):
    """
    Manage print history file

    The history file is json-formatted as a list of lists each containing
    the elements
        [path, status, timestamp],
    whith path being the path of the gcode file,
    status being a string defining the outcome of the print, one of
        "done", "stopped",
    timestamp being the time of completion in seconds since epoch.
    """
    history = ListProperty()

    def __init__(self):
        self.history = self.read()

    def trim_history(self):
        """Remove all entries of deleted files, return number of removed entries"""
        history = self.history
        to_remove = []
        for e in history:
            if not exists(e[0]):
                to_remove.append(e)
        if to_remove != []:
            for e in to_remove:
                history.remove(e)
            self.write(history)
            self.history = history
            return len(to_remove)
        return 0

    def read(self):
        """Read the history file and return it as a list object"""
        try:
            with open(p.history_file, "r") as fp:
                history = json.load(fp)
        except (IOError, ValueError): # No file or incorrect JSON
            logging.info("History: Couldn't read file at {}".format(p.history_file))
            history = []
        if not self.verify_history(history):
            logging.warning("History: Malformed history file")
            history = []
        return history

    def verify_history(self, history):
        """Only return True when the entire history has a correct structure"""
        try:
            for e in history:
                if not (isinstance(e[0], (unicode, str)) and        # path
                        (e[1] == "done" or e[1] == "stopped") and   # status
                        isinstance(e[2], (float, int))):            # timestamp
                    return False
        except:
            return False
        return True

    def write(self, history):
        """Write the object to the history file"""
        try:
            with open(p.history_file, "w") as fp:
                json.dump(history, fp, indent=True)
        except IOError:
            return

    def add(self, path, status):
        """Add a new entry to the history with the path and status string specified"""
        self.history.append([path, status, time.time()])
        self.write(self.history)
