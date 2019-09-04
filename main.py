#!/usr/bin/env python2


from time import time
from os.path import dirname, join
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty, ObjectProperty, OptionProperty
from kivy.clock import Clock
from kivy.animation import Animation



from kivy.app import App
from kivy.config import Config
from kivy.uix.screenmanager import Screen
from kivy.uix.screenmanager import ScreenManager
from kivy.lang import Builder
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.filechooser import FileChooser, FileChooserIconView, FileChooserController
from kivy.resources import resource_add_path
import os
import subprocess
from settings import *

Config.set('graphics', 'resizable', '0') 
Config.set('graphics', 'width', 600)
Config.set('graphics', 'height', 1024)
Config.set('graphics', 'fullscreen', '0')#set to 1 or 'auto' for raspi
#resource_add_path(os.getcwd())
#resource_remove_path('')


def modification_date_sort(files, filesystem):#sortierfunktion fuer Filechooser
    return (sorted(f for f in files if filesystem.is_dir(f)) 
    + sorted((f for f in files if not filesystem.is_dir(f)), key = lambda F: os.path.getmtime(F)))
class FC(FileChooserIconView):
    sort_func = ObjectProperty(modification_date_sort)
    #is orig. defined in FileChooserController, which FileCHooserIc.. is a child from
    


mainkv = Builder.load_file("main.kv")
Builder.load_file("style.kv")

#Clock.schedule_interval(FC._update_files, 1)
class KlipperGui(App):
    def build(self):
        self.mainkv = mainkv
        return mainkv



#subprocess.check_output("cat /etc/services", shell=True)
    
if __name__ == '__main__':
    print 'main runs'
    KlipperGui().run()
