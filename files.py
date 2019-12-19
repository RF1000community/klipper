from os import remove
from os.path import getmtime, basename, dirname, exists, abspath, join
import shutil

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.filechooser import FileChooserIconView

from elements import *
import parameters as p


class FC(FileChooserIconView):

    def __init__(self, **kwargs):
        super(FC, self).__init__(**kwargs)
        self.sort_func = self.modification_date_sort
        self.filters = ['*.gco', '*.gcode']
        self.multiselect = False
        self.app = App.get_running_app()
        if exists(p.sdcard_path):
            self.rootpath = p.sdcard_path
            self.path = p.sdcard_path
        self.scheduled_updating = False
        Clock.schedule_once(self.bind_tab, 0)

    def bind_tab(self, e):
        tabs = self.app.root.ids.tabs
        tabs.bind(current_tab=self.control_updating)

    def control_updating(self, instance, tab):
        if tab == instance.ids.file_tab:
            self._update_files()
            self.scheduled_updating = Clock.schedule_interval(self._update_files, 5)
        elif self.scheduled_updating:
            Clock.unschedule(self.scheduled_updating)

    def modification_date_sort(self, files, filesystem):#sortierfunktion fuer Filechooser
        return (sorted((f for f in files if filesystem.is_dir(f)), reverse=True) #folders
              + sorted((f for f in files if not filesystem.is_dir(f)), key=getmtime, reverse=True)) #files

    def on_selection(self, instance, filenames):
        if not filenames:
            return
        self.popup = PrintPopup(filenames[0], creator=self)
        self.popup.open()


class PrintPopup(BasePopup):

    def __init__(self, path, **kwargs):
        from os import symlink
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
        if dirname(self.path) != p.sdcard_path:
            new_path = join(p.sdcard_path, basename(self.path))
            if 'USB-Device' in self.path:
                app.notify.show("Copying {} to Printer...".format(basename(self.path)))
                shutil.copy(self.path, new_path)
            else:
                symlink(self.path, new_path)

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
        remove(self.creator.path)
        # Update the files in the filechooser instance
        self.creator.creator._update_files()
        self.dismiss()
