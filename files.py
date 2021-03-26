import os
from math import log10

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import BooleanProperty, OptionProperty, StringProperty
from kivy.uix.label import Label
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview import RecycleView

from .elements import PrintPopup
from . import parameters as p
from . import printer_cmd

class Filechooser(RecycleView):

    path = StringProperty()
    btn_back_visible = BooleanProperty(False)

    def __init__(self, **kwargs):
        self.app = App.get_running_app()
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
        self.app.root.ids.tabs.bind(current_tab=self.control_updating)

    def control_updating(self, instance, tab):
        if tab == instance.ids.file_tab:
            self.load_files(in_background = True)
            self.update_timer = Clock.schedule_interval(self.update, 0.5)
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
        # If p.usb_mount_dir folder is not empty => a usb stick is plugged in
        # (usbmount mounts to this directory)
        usb_state = (p.usb_mount_dir in content and
                len(os.listdir(os.path.join(self.path, p.usb_mount_dir))) > 0)
        # Only update if files have changed (loop takes 170ms, listdir 0.3ms)
        if (not in_background) or self.content != content or self.usb_state != usb_state:
            for base in content:
                # Hidden files/directories (don't show)
                if base.startswith("."):
                    continue
                path = os.path.join(self.path, base)
                dict_ = {'name': base, 'path': path, 'thumbnail': '', 'details': ''}
                # Gcode/ufp files
                if os.path.isfile(path):
                    ext = os.path.splitext(base)[1]
                    if ext in {'.gco', '.gcode', '.ufp'}:
                        dict_['item_type'] = "file"
                        if self.app.gcode_metadata:
                            md = self.app.gcode_metadata.get_metadata(path)
                            weight = md.get_filament(measure="weight")
                            if weight is not None:
                                precision = max(1-int(log10(weight)), 0)
                                dict_['details'] = f"{weight:.{precision}f}g"
                            dict_['thumbnail'] = md.get_thumbnail_path()
                        files.append(dict_)
                # USB Stick
                elif base == p.usb_mount_dir:
                    if usb_state:
                        dict_['item_type'] = "usb"
                        usb.append(dict_)
                # Folders
                elif os.path.isdir(path):
                    dict_['item_type'] = "folder"
                    folders.append(dict_)

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
        """Move up one directory"""
        self.path = os.path.dirname(self.path)
        self.load_files()


class FilechooserGrid(LayoutSelectionBehavior, RecycleGridLayout):
    # Adds selection behaviour to the view
    pass


class FilechooserItem(RecycleDataViewBehavior, Label):
    item_type = OptionProperty('file', options = ['file', 'folder', 'usb'])
    name = StringProperty()
    path = StringProperty()
    details = StringProperty()
    index = None
    thumbnail = StringProperty(allownone=True)
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
