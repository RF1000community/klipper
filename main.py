#!/usr/bin/env python3

from sys import argv
if '-t' in argv:
    testing = True
    argv.remove('-t')
else:
    testing = False
import os
#os.environ['KIVY_WINDOW'] = 'pygame' 
from os.path import dirname, join
from kivy import kivy_data_dir
from kivy.lang import Builder
from kivy.app import App
from kivy.config import Config
from settings import *
from home import *
from files import *
import parameters as p
from kivy.config import Config

if testing: Config.read('testconfig.ini')
else: Config.read('config.ini')
#Config.write()

Builder.unload_file(join(kivy_data_dir, 'style.kv'))
Builder.load_file("style.kv")

#Clock.schedule_interval(FC._update_files, 1)
class mainApp(App):
    pass


if __name__ == '__main__':
    print('main runs')
    mainApp().run()
