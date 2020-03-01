# coding: utf-8
import json
from os.path import basename
import time

from kivy.app import App
from kivy.event import EventDispatcher
from kivy.properties import (ListProperty, NumericProperty, StringProperty,
    BooleanProperty, OptionProperty)
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior

import parameters as p


class FC(RecycleView):
    path = StringProperty()
    def __init__(self, **kwargs):
        super(FC, self).__init__(**kwargs)
        self.app = App.get_running_app()
        self.load_queue(in_background=False)
        self.app.bind(queued_files=self.load_queue)
        self.app.bind(print_state=self.load_queue)
        self.app.history.bind(history=self.load_queue)

    def load_queue(self, instance=None, queue=None, in_background=True):
        queue = []
        for i, e in enumerate(self.app.queued_files):
            new = {}
            new["name"] = basename(e)
            new["details"] = (self.app.print_state.capitalize() if i == 0 else "{}.".format(i))
            new["path"] = e
            new["status"] = "queued"
            queue.insert(0, new) # next queue item is displayed last

        history = []
        for e in self.app.history.history:
            new = {}
            new["name"] = basename(e[0])
            new["details"] = e[1].capitalize() # "stopped" or "done"
            new["path"] = e[0]
            new["status"] = e[1]
            new["timestamp"] = e[2]
            history.insert(0, new) # history is sorted last file at end

        if self.app.print_state in {"printing", "paused"}:
            queue[-1]["status"] = self.app.print_state
        #TEST
        queue.append({"name": "print.gco", "path": "/home/gabriel/sdcard/print.gco",
            "status": "paused", "details": "Paused"})

        if len(queue) > 1:
            queue.insert(0, {"name": "Queue:"})
        if len(history) >= 1:
            history.insert(0, {"name": "History:"})

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

class FCBox(LayoutSelectionBehavior, RecycleBoxLayout):
    # Adds selection behaviour to the view
    pass

class FCItem(RecycleDataViewBehavior, Label):
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
        return super(FCItem, self).refresh_view_attrs(rv, index, default_data)

    def on_touch_down(self, touch):
        # Add selection on touch down
        if super(FCItem, self).on_touch_down(touch):
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
        if super(FCItem, self).on_touch_up(touch):
            return True
        if self.collide_point(*touch.pos) and was_pressed:
            return True
        return False

    def apply_selection(self, rv, index, is_selected):
        # Respond to the selection of items in the view
        self.selected = is_selected


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

    def read(self):
        """Read the history file and return it as a list object"""
        try:
            with open(p.history_file, "r") as fp:
                history = json.load(fp)
        except IOError: # File doesn't exist yet
            history = []
        return history

    def write(self, history):
        """Write the object to the history file"""
        with open(p.history_file, "w") as fp:
            json.dump(history, fp, indent=True)

    def add(self, path, status):
        """Add a new entry to the history with the path and status string specified"""
        self.history.append([path, status, time.time()])
        self.write(self.history)
