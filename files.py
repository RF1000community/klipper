import logging
import os
from os.path import getmtime, basename, dirname, exists, abspath, join
import re
import shutil

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview import RecycleView
from kivy.properties import BooleanProperty, OptionProperty, StringProperty

from elements import BasePopup
import parameters as p


class GC(RecycleView):
    path = StringProperty()
    btn_back_visible = BooleanProperty(False)
    def __init__(self, **kwargs):
        self.app = App.get_running_app()
        self.filament_crossection = 3.141592653 * (self.app.filament_diameter/2.)**2
        if os.path.exists(p.sdcard_path):
            self.path = p.sdcard_path
        else:
            self.path = "/"
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
            if len(os.listdir(join(self.path, "USB-Device"))) > 0:
                logging.info("USB folders:".format(os.listdir(join(self.path, "USB-Device"))))
                usb = [{'name': "USB-Device", 'item_type': 'usb', 'path': (join(self.path, "USB-Device")), 'details':""}]
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
        super(PrintPopup, self).dismiss()
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
