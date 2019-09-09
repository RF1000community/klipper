#!/usr/bin/env python2

from os.path import dirname, join
from kivy import kivy_data_dir
from kivy.lang import Builder
from kivy.app import App
from kivy.config import Config
import os

from settings import *
from home import *
from files import *
import parameters as p


Config.set('graphics', 'resizable', '0') 
Config.set('graphics', 'width', p.screen_width)
Config.set('graphics', 'height', p.screen_height)
Config.set('graphics', 'fullscreen', '0')#set to 1 or 'auto' for raspi
Config.set('kivy','keyboard_mode', 'dock')


Builder.unload_file(join(kivy_data_dir, 'style.kv'))
Builder.load_file("style.kv")


#Clock.schedule_interval(FC._update_files, 1)
class mainApp(App):
    def build(self):
        return self.root


if __name__ == '__main__':
    print('main runs')
    mainApp().run()
