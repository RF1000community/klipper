#!/usr/bin/env python3

from sys import argv
if '-t' in argv:
    testing = True
    argv.remove('-t')
else:
    testing = False
import os
#os.environ['KIVY_WINDOW'] = 'pygame' 
#os.environ['KCFG_input_device_%(name)s'] = 'probesysfs,provider=mtdev,param=rotation=90,param=invert_y=1'
from os.path import dirname, join
from kivy import kivy_data_dir
from kivy.lang import Builder
from kivy.app import App
from kivy.config import Config

from settings import *
from home import *
from files import *
import parameters as p


Config.set('graphics', 'resizable', '0') 
Config.set('graphics', 'width', p.screen_width)
Config.set('graphics', 'height', p.screen_height)
Config.set('graphics', 'fullscreen', 0 if testing else 1)#set to 1 or 'auto' for raspi
Config.set('kivy', 'keyboard_layout', 'en_US')
Config.set('kivy','keyboard_mode', 'dock')
Config.set('graphics','maxfps',30)
Config.set("kivy", "log_level", "debug")#temporary for debugging
Config.set('kivy','show_fps', 'True')
Config.set('input','device_%(name)s', 'probesysfs,provider=mtdev,param=rotation=90,param=invert_y=1')
#Config.set('input', 'provider','mtdev')
#Config.set('input','param','rotation=90,param=invert_y=1')
Builder.unload_file(join(kivy_data_dir, 'style.kv'))
Builder.load_file("style.kv")

#Clock.schedule_interval(FC._update_files, 1)
class mainApp(App):
    pass


if __name__ == '__main__':
    print('main runs')
    mainApp().run()
