from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.popup import Popup
from kivy.app import App
from os.path import expanduser, getmtime, split, dirname, exists, abspath
import parameters as p


class FC(FileChooserIconView):

    def __init__(self, **kwargs):
        super(FC, self).__init__(**kwargs)
        self.sort_func = self.modification_date_sort
        # Default path
        self.path = self.get_starting_path()

    def get_starting_path(self):
        if exists(expanduser(p.fc_starting_path)):
            return abspath(expanduser(p.fc_starting_path))
        return expanduser('~/')

    def modification_date_sort(self, files, filesystem):#sortierfunktion fuer Filechooser
        return (sorted(f for f in files if filesystem.is_dir(f)) 
            + sorted((f for f in files if not filesystem.is_dir(f)), 
                key = lambda F: getmtime(F)))

    def on_selection(self, instance, filenames):
        if not filenames:
            return
        self.popup = PrintPopup(filenames[0], self)
        self.popup.open()


class PrintPopup(Popup):
    
    def __init__(self, filename, chooser, **kwargs):
        self.prompt = "Start printing of\n%s/[b]%s[/b]"%split(filename)
        super(PrintPopup, self).__init__(**kwargs)
        self.chooser = chooser

    def dismiss(self):
        super(PrintPopup, self).dismiss()
        # Supposed to be read-only but still works that way
        self.chooser.selection = [] 

    def confirm(self):
        self.dismiss()
        tab = App.get_running_app().root
        tab.switch_to(tab.ids.home_tab)

