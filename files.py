import json
import logging
import os
from os.path import getmtime, basename, dirname, exists, abspath, join
import shutil, re
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import (ListProperty, ObjectProperty, NumericProperty,
    DictProperty, StringProperty, BooleanProperty, OptionProperty)

from elements import *
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


class GC(RecycleView):
    path = StringProperty()
    btn_back_visible = BooleanProperty(False)
    def __init__(self, **kwargs):
        self.app = App.get_running_app()
        self.filament_crossection = 3.141592653 * (self.app.filament_diameter/2.)**2
        if os.path.exists(p.sdcard_path):
            self.path = p.sdcard_path
        else:
            self.path = os.getenv("HOME")
        super(GC, self).__init__(**kwargs)
        Clock.schedule_once(self.bind_tab, 0)
        self.load_files()

    def bind_tab(self, e):
        tabs = self.app.root.ids.tabs
        tabs.bind(current_tab=self.control_updating)

    def control_updating(self, instance, tab):
        if tab == instance.ids.file_tab:
            self.load_files(in_background = True)
            Clock.schedule_interval(self.update, 10)

    def update(self, dt):
        self.load_files(in_background=True)

    def load_files(self, in_background = False):
        content = os.listdir(self.path)
        # filter usb
        usb = []
        if "USB-Device" in content:
            content.remove("USB-Device")
            # Check if folder is not empty -> a usb stick is plugged in
            if len(os.listdir(join(root, "USB-Device"))) > 0:
                logging.info("USB folders:".format(os.listdir(join(root, "USB-Device"))))
                usb = [{'name': "USB-Device", 'item_type': 'usb', 'path': (join(root, "USB-Device")), 'details':""}]
        files = []
        folders = []
        for base in content:
            # Filter out hidden files/directories
            if base.startswith("."):
                continue
            path = os.path.join(self.path, base)
            dict_ = {"name": base, "path": path}
            if os.path.isdir(path):
                dict_["item_type"] = "folder"
                dict_["details"] = ""
                folders.append(dict_)
            # Filter only gcode files
            elif os.path.isfile(path) and os.path.splitext(base)[1].startswith(".gco"):
                dict_["item_type"] = "file"
                dict_["details"] = self.get_details(path) or "--"
                files.append(dict_)
        # Sort files by modification time (last modified first)
        files.sort(key=lambda d: os.path.getmtime(d["path"]), reverse=True)
        # Sort folders alphabetically
        folders.sort(key=lambda d: d["name"].lower())

        self.btn_back_visible = self.path != p.sdcard_path

        new_data = usb + folders + files
        if self.data != new_data:
            self.data = new_data
            self.refresh_from_data()
            if not in_background:
                self.scroll_y = 1

    def back(self):
        self.path = dirname(self.path)
        self.load_files()
    
    def get_details(self, path):
        # Pass the filepath. Returns the filament use of a gcode file 
        # Return value is shown below Name of each file
        filament = [
            r'Ext.*=.*mm',                          # Kisslicer
            r';.*filament used =',                  # Slic3r
            r';.*Filament length: \d+.*\(',         # S3d
            r'.*filament\sused\s=\s.*mm',           # Slic3r PE
            r';Filament used: \d*.\d+m',            # Cura
            r';Material#1 Used:\s\d+\.?\d+',        # ideamaker
            r'.*filament\sused\s.mm.\s=\s[0-9\.]+'  # PrusaSlicer 
            ]
        nlines = 100
        head = tail = []
        with open(path, 'rb') as gcode_file :
            # Read first 100 lines from beginning
            head = [gcode_file.readline() for i in range(nlines)]
            tail = []
            # Read further back until there are enough lines
            block_count = -1
            while len(tail) < nlines:
                offset = block_count * 1024
                try:
                    gcode_file.seek(offset, os.SEEK_END)
                    tail = gcode_file.readlines()
                except: # For the unlikely case that the file is too small
                    break
                block_count -= 1
        tail = tail[-100:]

        for line in (head + tail):
            for i, regex in enumerate(filament):
                match = re.search(regex, line)
                if match:
                    match2 = re.search(r'\d*\.\d*', match.group())
                    if match2:
                        filament = float(match2.group())
                        if i == 4:
                            filament *= 1000 # Cura gives meters -> convert to mm
                        weight = self.filament_crossection*filament*0.0011 #density in g/mm^3
                        return "{:4.0f}g".format(weight)
        return ""

class GCGrid(LayoutSelectionBehavior, RecycleGridLayout):
    # Adds selection behaviour to the view
    pass

class GCItem(RecycleDataViewBehavior, Label):
    item_type = OptionProperty('file', options = ['file', 'folder', 'usb'])
    name = StringProperty()
    path = StringProperty()
    details = StringProperty()
    index = None
    pressed = BooleanProperty(False)

    def refresh_view_attrs(self, rv, index, data):
        # Catch and handle the view changes
        self.index = index
        return super(GCItem, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        # Add selection on touch down
        if super(GCItem, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            self.pressed = True
            return True

    def on_touch_up(self, touch):
        was_pressed = self.pressed
        self.pressed = False
        if super(GCItem, self).on_touch_up(touch):
            return True
        if self.collide_point(*touch.pos) and was_pressed:
            gc = self.parent.parent
            if self.item_type == 'file':
                self.popup = PrintPopup(self.path, filechooser=gc)
                self.popup.open()
            elif self.item_type == 'folder' or self.item_type == 'usb':
                gc.path = self.path
                gc.load_files()
            return True
        return False

    def apply_selection(self, rv, index, is_selected):
        # Respond to the selection of items in the view
        self.selected = is_selected


class PrintPopup(BasePopup):

    def __init__(self, path, filechooser, **kwargs):
        self.path = path
        self.filechooser = filechooser
        super(PrintPopup, self).__init__(**kwargs)

    def confirm(self):
        app = App.get_running_app()
        self.dismiss()
        new_path = self.path
        if 'USB Device' in self.path:
            new_path = join(p.sdcard_path, basename(self.path))
            app.notify.show("Copying {} to Printer...".format(basename(self.path)))
            shutil.copy(self.path, new_path)

        app.send_print(new_path)
        tabs = app.root.ids.tabs
        tabs.switch_to(tabs.ids.home_tab)

    def delete(self):
        """Open a confirmation dialog to delete the file"""
        super(PrintPopup, self).dismiss() # dismiss bypassing deselection
        self.confirm_del = DelPopup(path = self.path, filechooser=self.filechooser)
        self.confirm_del.open()


class DelPopup(BasePopup):
    """Popup to confirm file deletion"""
    def __init__(self, path, filechooser, **kwargs):
        self.path = path
        self.filechooser = filechooser
        super(DelPopup, self).__init__(**kwargs)

    def confirm(self):
        """Deletes the file and closes the popup"""
        os.remove(self.path)
        # Update the files in the filechooser instance
        self.filechooser.load_files(in_background=True)
        self.dismiss()

        app = App.get_running_app()
        app.notify.show("File deleted", "Deleted " + basename(self.path), delay=4)

class StopPopup(BasePopup):
    pass


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
