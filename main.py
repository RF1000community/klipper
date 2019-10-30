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
from os.path import join
from elements import UltraKeyboard
from settings import *
from home import *
from files import *
import parameters as p
import threading
import logging

if testing: Config.read(join(p.kgui_dir, 'testconfig.ini')) #this needs an absolute path otherwise config will only be loaded when working directory is parent directory of main.py
else:       Config.read(join(p.kgui_dir, 'config.ini'))

Builder.unload_file(join(kivy_data_dir, 'style.kv'))
Builder.load_file(join(p.kgui_dir, "style.kv"))

class mainApp(App, threading.Thread): #add threading.thread => inherits start() method to start in new thread
    def __init__(self, config = None, **kwargs):
        logging.info("Kivy app initializing...")
        self.config = config
        super(mainApp,self).__init__(**kwargs)

    def run(self):
        logging.info("Kivy app.run")
        Clock.schedule_once(self.change_vkeyboard, 0)
        super(mainApp, self).run()

    def recieve_speed(self):
        return 77
    def send_speed(self,val):
        print("send {} as speed".format(val))

    def recieve_flow(self):
        return 107
    def send_flow(self,val):
        print("send {} as flow".format(val))

    def recieve_fan(self):
        return 77
    def send_fan(self,val):
        print("send {} as fan".format(val))

    def recieve_temp_A(self):
        return 77
    def send_temp_A(self,val):
        k = self
        self.value = val#temporary should be recieve call afterwards
        print("send {} as Temp A".format(val))

    def recieve_temp_B(self):
        return 77
    def send_temp_B(self,val):
        print("send {} as Temp B".format(val))

    def recieve_temp_bed(self):
        return 77
    def send_temp_bed(self,val):
        print("send {} as Temp bed".format(val))


    def send_up_Z(self):
        print("move Z up")
    def send_down_Z(self):
        print("move Z down")
    def send_stop_Z(self):
        print("stop Z")
    def send_home_Z(self):
        print("Home Z Axis")

    def send_stop(self):
        print("stop print")
    def send_play(self):
        print("resume print")
    def send_pause(self):
        print("pause print")

    def send_calibrate(self):
        print("calibrate")

    def send_acc(self, val):
        print("Sent Accelleration of {} to printer".format(val))
    def request_acc(self):
        return 36

    def change_vkeyboard(self, dt):
        self.root_window.set_vkeyboard_class(UltraKeyboard)
    


if __name__ == '__main__':
    mainApp().run()
