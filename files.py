import logging
import os
from os.path import getmtime, basename, dirname, exists, abspath, join
import shutil, re

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ListProperty, ObjectProperty, NumericProperty, DictProperty, StringProperty, BooleanProperty, OptionProperty

from elements import *
import parameters as p


class FC(RecycleView):
    path = StringProperty()
    btn_back_visible = BooleanProperty(False)
    def __init__(self, **kwargs):
        self.app = App.get_running_app()
        self.filament_crossection = 3.141592653 * (self.app.filament_diameter/2.)**2
        self.cache = [None, None, None]
        self.cache_ready = False
        if os.path.exists(p.sdcard_path):
            self.path = p.sdcard_path
        else:
            self.path = "/"
        super(FC, self).__init__(**kwargs)
        Clock.schedule_once(self.bind_tab, 0)
        self.load_files()
    
    def bind_tab(self, e):
        tabs = self.app.root.ids.tabs
        tabs.bind(current_tab=self.control_updating)

    def control_updating(self, instance, tab):
        if tab == instance.ids.file_tab:
            pass

    def load_files(self, in_background = False):


        root, _folders, _files = next(os.walk(self.path))
        # filter usb
        usb = []
        if "USB Device" in _folders:
            _folders.remove("USB Device")
            # Check if folder is not empty -> a usb stick is plugged in
            r, d, f = next(os.walk(join(root, "USB Device")))
            if len(d) + len(f) > 0:
                usb = [{'name': "USB Device", 'item_type': 'usb', 'path': (join(root, "USB Device")), 'details':""}]
        folders = [(f, join(root, f)) for f in _folders]
        # filter files
        files = []
        for f in _files:
            if ".gco" in os.path.splitext(f)[1]:
                files.append((f, join(root, f)))
        # sort
        files = self.modification_date_sort(files)
        folders = sorted(folders)
        # generate dicts
        folders = [{'name': f[0], 'item_type': "folder", 'path': f[1], 'details': ""} for f in folders]
        files =   [{'name': f[0], 'item_type': "file",   'path': f[1], 'details': self.get_details(f[1])} for f in files]

        self.btn_back_visible = self.path != p.sdcard_path


        new_data = usb + folders + files
        if self.data != new_data:
            self.data = new_data
            self.refresh_from_data()
            if not in_background:
                self.scroll_y = 1
    
    def load_queue(self, in_background=False):
        queue = [{'name': e[0], 'details': "", 'item_type': "queue", 'path': e[1]} for e in queue]

        self.data = queue 
        self.refresh_from_data()
        if not in_background:
            self.scroll_y = 1

    def back(self):
        self.path = dirname(self.path)
        self.load_files()
    
    def modification_date_sort(self, files):
        return sorted((f for f in files), key=lambda f: os.path.getmtime(f[1]), reverse=True)
    
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
                        return "{:4.1f}g".format(weight)
        return ""

class FCBox(LayoutSelectionBehavior, RecycleBoxLayout):
    # Adds selection behaviour to the view
    pass

class FCItem(RecycleDataViewBehavior, Widget):
    item_type = OptionProperty('file', options = ['file', 'folder', 'usb', 'queue'])
    name = StringProperty()
    path = StringProperty()
    details = StringProperty()
    index = None
    selected = BooleanProperty(False)
    highlighted = BooleanProperty(False)
    selectable = BooleanProperty(True) #TODO check if needed

    def refresh_view_attrs(self, rv, index, data):
        # Catch and handle the view changes
        self.index = index
        return super(FCItem, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        # Add selection on touch down
        if super(FCItem, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            if self.item_type == 'file':
                self.popup = PrintPopup(self.name, creator=self)
                self.popup.open()
            elif self.item_type == 'queue':
                return self.parent.select_with_touch(self.index, touch)
            else:
                self.parent.parent.path = self.path
                self.parent.parent.load_files()

    def apply_selection(self, rv, index, is_selected):
        # Respond to the selection of items in the view
        self.selected = is_selected

class PrintPopup(BasePopup):

    def __init__(self, path, **kwargs):
        self.path = path
        # Extract only the filename from the path
        self.prompt = basename(self.path)
        super(PrintPopup, self).__init__(**kwargs)

    def dismiss(self):
        super(PrintPopup, self).dismiss()
        # Deselects the file in the filechooser when canceled
        # Supposed to be read-only but still works that way
        self.creator.selection = []

    def confirm(self):
        app = App.get_running_app()
        self.dismiss()
        new_path = self.path
        if 'USB Device' in self.path:
            new_path = join(p.sdcard_path, basename(self.path))
            app.notify.show("Copying {} to Printer...".format(basename(self.path)))
            shutil.copy(self.path, new_path)

        app.send_start(new_path)
        tabs = app.root.ids.tabs
        tabs.switch_to(tabs.ids.home_tab)


    def delete(self):
        """Open a confirmation dialog to delete the file"""
        super(PrintPopup, self).dismiss() # dismiss bypassing deselection
        self.confirm_del = DelPopup(creator=self)
        self.confirm_del.open()


class DelPopup(BasePopup):
    """Popup to confirm file deletion"""

    def dismiss(self):
        super(DelPopup, self).dismiss()
        # Deselect in the filechooser
        self.creator.creator.selection = []

    def confirm(self):
        """Deletes the file and closes the popup"""
        os.remove(self.creator.path)
        # Update the files in the filechooser instance
        self.creator.creator._update_files()
        self.dismiss()

        app = App.get_running_app()
        app.notify.show("File deleted", "Deleted " + basename(self.creator.path), delay=4)
