from kivy.uix.filechooser import FileChooserIconView
from kivy.app import App
from kivy.clock import Clock
from os.path import expanduser, getmtime, split, exists, abspath
from elements import *
import parameters as p


class FC(FileChooserIconView):

    def __init__(self, **kwargs):
        super(FC, self).__init__(**kwargs)
        self.sort_func = self.modification_date_sort
        self.filters = ['*.gco', '*.gcode']
        self.multiselect = False
        if exists("/media"):
            self.rootpath = "/media"
            self.path = "/media"
        self.scheduled_updating = False
        Clock.schedule_once(self.bind_tab, 0)

    def bind_tab(self, e):
        tabs = App.get_running_app().root.ids.tabs
        tabs.bind(current_tab=self.control_updating)

    def control_updating(self, instance, tab):
        if tab == instance.ids.file_tab:
            self._update_files()
            self.scheduled_updating = Clock.schedule_interval(self._update_files, 1)
        elif self.scheduled_updating:
            Clock.unschedule(self.scheduled_updating)

    def modification_date_sort(self, files, filesystem):#sortierfunktion fuer Filechooser
        return (sorted(f for f in files if filesystem.is_dir(f))
            + sorted((f for f in files if not filesystem.is_dir(f)),
                key = lambda F: getmtime(F)))

    def on_selection(self, instance, filenames):
        if not filenames:
            return
        self.popup = PrintPopup(filenames[0], self)
        self.popup.open()


class PrintPopup(BasePopup):

    def __init__(self, path, chooser, **kwargs):
        self.prompt = path.split("/")[-1]
        self.chooser = chooser
        super(PrintPopup, self).__init__(**kwargs)

    def dismiss(self):
        super(PrintPopup, self).dismiss()
        # Supposed to be read-only but still works that way
        self.chooser.selection = []

    def confirm(self):
        self.dismiss()
        root = App.get_running_app().root
        tab = root.ids.tabs
        tab.switch_to(tab.ids.home_tab)

