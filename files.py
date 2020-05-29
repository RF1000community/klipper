import os
import re
from zipfile import ZipFile

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import BooleanProperty, OptionProperty, StringProperty
from kivy.uix.label import Label
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview import RecycleView

from .elements import BasePopup, PrintPopup
from . import parameters as p
from pytictoc import TicToc

class Filechooser(RecycleView):
    path = StringProperty()
    btn_back_visible = BooleanProperty(False)
    def __init__(self, **kwargs):
        self.app = App.get_running_app()
        self.filament_crossection = 3.141592653 * (self.app.filament_diameter/2.)**2
        self.content = []
        self.usb_state = False
        self.update_timer = None
        if os.path.exists(p.sdcard_path):
            self.path = p.sdcard_path
        else:
            self.path = "/"
        super().__init__(**kwargs)
        Clock.schedule_once(self.bind_tab, 0)
        self.load_files()

    def bind_tab(self, e):
        tabs = self.app.root.ids.tabs
        tabs.bind(current_tab=self.control_updating)

    def control_updating(self, instance, tab):
        if tab == instance.ids.file_tab:
            self.load_files(in_background = True)
            self.update_timer = Clock.schedule_interval(self.update, 1.782)
        elif self.update_timer:
            Clock.unschedule(self.update_timer)
            self.update_timer = None

    def update(self, dt):
        self.load_files(in_background=True)

    def load_files(self, in_background = False):
        usb = []
        files = []
        folders = []
        content = os.listdir(self.path)
        # if USB-Device folder is not empty => a usb stick is plugged in (usbmount mounts them to this directory)
        usb_state = "USB-Device" in content and len(os.listdir(os.path.join(self.path, "USB-Device"))) > 0
        # only update if files have changed
        if (not in_background) or self.content != content or self.usb_state != usb_state:
            for base in content:
                # Hidden files/directories (don't show)
                if base.startswith("."):
                    continue
                path = os.path.join(self.path, base)
                dict_ = {'name': base, 'path': path, 'thumbnail': "", 'details': ""}
                # Gcode/ufp files
                if os.path.isfile(path):
                    ext = os.path.splitext(base)[1]
                    dict_['item_type'] = "file"
                    if ext in (".gco", ".gcode"):
                        dict_['details'] = self.get_details(path)
                        files.append(dict_)
                    elif ext == ".ufp":
                        dict_['details'] = self.get_ufp_details(path)
                        dict_['thumbnail'] = self.get_ufp_thumbnail(path)
                        files.append(dict_)
                    continue
                # USB Stick
                if base == "USB-Device":
                    if usb_state:
                        dict_['item_type'] = "usb"
                        usb.append(dict_)
                    continue
                # Folders
                if os.path.isdir(path):
                    dict_['item_type'] = "folder"
                    folders.append(dict_)
                    continue

            # Sort files by modification time (last modified first)
            files.sort(key=lambda d: os.path.getmtime(d["path"]), reverse=True)
            # Sort folders alphabetically
            folders.sort(key=lambda d: d["name"].lower())

            self.data = usb + folders + files
            self.refresh_from_data()
            if not in_background:
                self.scroll_y = 1
            self.content = content
            self.usb_state = usb_state

    def back(self):
        self.path = os.path.dirname(self.path)
        self.load_files()

    def parse_filament_use(self, match, slicer_idx):
        match2 = re.search(r'\d*\.\d*', match.group())
        if match2:
            filament = float(match2.group())
            if slicer_idx == 4:
                filament *= 1000 # Cura gives meters -> convert to mm
            weight = self.filament_crossection*filament*0.00124 #density in g/mm^3
            return f"{weight:4.0f}g"
        return "---"

    filament = [
        r'Ext.*=.*mm',                          # Kisslicer
        r';.*filament used =',                  # Slic3r
        r';.*Filament length: \d+.*\(',         # S3d
        r'.*filament\sused\s=\s.*mm',           # Slic3r PE
        r';Filament used: \d*.\d+m',            # Cura
        r';Material#1 Used:\s\d+\.?\d+',        # ideamaker
        r'.*filament\sused\s.mm.\s=\s[0-9\.]+'  # PrusaSlicer 
        ]

    def get_details(self, path):
        # Pass the filepath. Returns the filament use of a gcode file 
        # Return value is shown below Name of each file
        with open(path, 'rb') as gcode_file:
            # search in the first 100 lines
            for i in range(100):
                line = gcode_file.readline().decode()
                for i, regex in enumerate(self.filament):
                    match = re.search(regex, line)
                    if match:
                        return self.parse_filament_use(match, i)
            # search in the last 5 blocks
            bytes_to_read = -5 * 1024
            try:
                gcode_file.seek(bytes_to_read, os.SEEK_END)
            except:
                return "--"
            while True:
                line = gcode_file.readline().decode()
                if not line:
                    return "--"
                for i, regex in enumerate(self.filament):
                    match = re.search(regex, line)
                    if match:
                        return self.parse_filament_use(match, i)
            return "--"

    def get_ufp_details(self, path):
        with ZipFile(path).open("/3D/model.gcode", 'r') as gcode_file:
            # search in the first 100 lines, we expect cura gcode
            for i in range(100):
                line = gcode_file.readline().decode()
                match = re.search(self.filament[4], line)
                if match:
                    return self.parse_filament_use(match, 4)
        return "--"

    def get_ufp_thumbnail(self, path):
        thumbnail_path = path.replace('.ufp', '.png')
        if not os.path.exists(thumbnail_path):
            zip_obj = ZipFile(path)
            with open(thumbnail_path, 'wb') as thumbnail:
                thumbnail.write(zip_obj.read("/Metadata/thumbnail.png"))
        return thumbnail_path

class FilechooserGrid(LayoutSelectionBehavior, RecycleGridLayout):
    # Adds selection behaviour to the view
    pass

class FilechooserItem(RecycleDataViewBehavior, Label):
    item_type = OptionProperty('file', options = ['file', 'folder', 'usb'])
    name = StringProperty()
    path = StringProperty()
    details = StringProperty()
    index = None
    thumbnail = StringProperty("")
    pressed = BooleanProperty(False)

    def refresh_view_attrs(self, rv, index, data):
        # Catch and handle the view changes
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        # Add selection on touch down
        if super().on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            self.pressed = True
            return True

    def on_touch_up(self, touch):
        was_pressed = self.pressed
        self.pressed = False
        if super().on_touch_up(touch):
            return True
        if self.collide_point(*touch.pos) and was_pressed:
            fc = self.parent.parent
            if self.item_type == 'file':
                self.popup = PrintPopup(self.path, filechooser=fc)
                self.popup.open()
            elif self.item_type == 'folder' or self.item_type == 'usb':
                fc.path = self.path
                fc.load_files()
            return True
        return False

    def apply_selection(self, rv, index, is_selected):
        # Respond to the selection of items in the view
        self.selected = is_selected

class DeletePopup(BasePopup):
    """Popup to confirm file deletion"""
    def __init__(self, path, filechooser=None, timeline=None, **kwargs):
        self.path = path
        self.filechooser = filechooser
        self.timeline = timeline
        super().__init__(**kwargs)

    def confirm(self):
        """Deletes the file and closes the popup"""
        os.remove(self.path)
        app = App.get_running_app()

        # Update the files in the filechooser instance
        if app.history:
            app.history.trim_history()
        if self.timeline:
            self.timeline.load_all(in_background=False)
        elif self.filechooser:
            self.filechooser.load_files(in_background=True)
        self.dismiss()
        app.notify.show("File deleted", "Deleted " + os.path.basename(self.path), delay=4)
