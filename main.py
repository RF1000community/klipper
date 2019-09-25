#!/usr/bin/env python2
# coding: utf-8

from sys import argv
if '-t' in argv:
    testing = True
    argv.remove('-t')
else:
    testing = False
import os
if not testing: 
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'gl'
from os.path import dirname, join
from kivy import kivy_data_dir
from kivy.lang import Builder
from kivy.app import App
from kivy.config import Config
from kivy.clock import Clock
from elements import UltraKeyboard
from settings import *
from home import *
from files import *
import parameters as p

if testing: Config.read('testconfig.ini')
else: Config.read('config.ini')
#Config.write()

Builder.unload_file(join(kivy_data_dir, 'style.kv'))
Builder.load_file("style.kv")

#Clock.schedule_interval(FC._update_files, 1)
class mainApp(App):
    
    def run(self):
        Clock.schedule_once(self.change_vkeyboard, 0)
        super(mainApp, self).run()

    def change_vkeyboard(self, dt):
        self.root_window.set_vkeyboard_class(UltraKeyboard)

if __name__ == '__main__':
    print('main runs')
    mainApp().run()
