from os import remove
from os.path import getmtime, basename, dirname, exists, abspath, join
import shutil, re

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
        self.filament_crossection = 3.141592653 * (self.app.filament_diameter/2.)**2 
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

""" Works but is way to slow, maybe do this after showing folder contents, and keep values to avoid recomputing when filechooser reloads
    def get_nice_size(self, path):
        '''Pass the filepath. Returns the filament use of a gcode file, instead of filesize.
           Or '' if it is a directory.
           Return value is shown below Name of each file
        '''
        if self.file_system.is_dir(path):
            return ''
        filament = [
            r'Ext.*=.*mm' ,									#	Kisslicer
            r';.*filament used =' ,							#	Slic3r
            r';.*Filament length: \d+.*\(' ,				#	S3d
            r'.*filament\sused\s=\s.*mm' ,					#	Slic3r PE
            r';Filament used: \d*.\d+m'	,					#	Cura
            r';Material#1 Used:\s\d+\.?\d+',				#	ideamaker
            r'.*filament\sused\s.mm.\s=\s[0-9\.]+'			#	PrusaSlicer
            ]
        with open(path, 'rb') as gcode_file :
            lines = gcode_file.readlines()
        for line in (lines[:100] + lines[-100:]):
            for i, regex in enumerate(filament):
                match = re.search(regex, line)
                if match:
                    match2 = re.search(r'\d*\.\d*', match.group())
                    if match2:
                        filament = float(match2.group())
                        import logging
                        logging.info("filament =  ====== {}".format(filament))
                        if i == 4: filament *= 1000 # Cura gives meters -> convert to mm
                        weight = self.filament_crossection*filament*0.0011 #density in g/mm^3
                        return "{:4.1f}g".format(weight)
        return ""
"""

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

        app = App.get_running_app()
        app.notify.show("File deleted", "Deleted " + basename(self.creator.path), delay=4)
