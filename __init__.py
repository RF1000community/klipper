#!/usr/bin/env python2
# coding: utf-8

import os
from sys import argv
if '-t' in argv:
    testing = True
    argv.remove('-t')
else:
    testing = False
if not testing: 
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'gl'
from os.path import join
from kivy import kivy_data_dir
from kivy.lang import Builder
from kivy.app import App
from kivy.config import Config
from kivy.clock import Clock
from kivy.properties import OptionProperty, BooleanProperty
from os.path import join
from subprocess import Popen
import threading
import logging
import site

from elements import UltraKeyboard
from settings import *
from home import *
from files import *
from status import *
import parameters as p

#add parent directory to sys.path so main.kv (parser.py) can import from it
site.addsitedir(p.kgui_dir)

#this needs an absolute path otherwise config will only be loaded when working directory is the parent directory
if testing: Config.read(join(p.kgui_dir, "config-test.ini"))
else:       Config.read(join(p.kgui_dir, "config.ini"))

#load a custom style.kv with changes to filechooser and more
Builder.unload_file(join(kivy_data_dir, "style.kv"))
Builder.load_file(join(p.kgui_dir, "style.kv"))

#add threading.thread => inherits start() method to start in new thread
class mainApp(App, threading.Thread):

    # Property for controlling the state as shown in the statusbar.
    state = OptionProperty("normal", options=[
        # Every string set has to be in this list
        "normal",
        "printing",
        "paused",
        "error",
        "initializing",
        ])
    homed_z = BooleanProperty(False)
    printer_objects_available = BooleanProperty(False)

    def __init__(self, config = None, **kwargs):# runs in klippy thread
        logging.info("Kivy app initializing...")
        self.testing = testing
        if not testing:
            self.kgui_config_section = config
            self.printer = self.kgui_config_section.get_printer()
            self.reactor = self.printer.get_reactor()
            self.printer.register_event_handler("klippy:ready", self.handle_ready)
            self.printer.register_event_handler("homing:homed_rails", self.handle_homed)
            self.printer.register_event_handler("klippy:shutdown", self.handle_shutdown)
            self.klipper_config = self.printer.objects['configfile'].read_main_config()
            stepper_conf = (self.klipper_config.getsection('stepper_x'), self.klipper_config.getsection('stepper_y'))
            self.pos_max = (stepper_conf[0].getint('position_max'), stepper_conf[0].getint('position_max'))
            self.pos_min = (stepper_conf[0].getint('position_min'), stepper_conf[1].getint('position_min'))
        super(mainApp, self).__init__(**kwargs)

    def run(self):
        logging.info("Kivy app.run")
        Clock.schedule_once(self.setup_after_run, 0)
        super(mainApp, self).run()

    def handle_ready(self): # the handlers are not thread safe!
        self.gcode = self.printer.lookup_object('gcode')
        self.toolhead = self.printer.lookup_object('toolhead')
        self.sdcard = self.printer.lookup_object('virtual_sdcard', None)
        self.fan = self.printer.lookup_object('fan', None)
        self.extruder0 = self.printer.lookup_object('extruder0', None)
        self.extruder1 = self.printer.lookup_object('extruder1', None)
        self.heater_bed = self.printer.lookup_object('heater_bed', None)
        self.printer_objects_available = True
    def handle_shutdown(self):
        logging.info("hadnled shutdown @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        self.stop()
    def handle_homed(self, homing, rails):
        for rail in rails:
            if rail.name == 'z':
                self.homed_z = True

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
    def send_xyz(self, x=None, y=None, z=None):
        # resets all queued moves and sets pos
        xyz = [x,y,z]
        self.reactor.register_async_callback((lambda e: self.set_xyz(xyz)))
    def set_xyz(self, xyz):
        current_pos = self.toolhead.get_position()
        xyz = [current_pos[i] if a is None else a for i,a in enumerate(xyz)]
        self.toolhead.set_position(xyz)
   

    def send_up_Z(self):
        self.reactor.register_async_callback(lambda e: self.toolhead.move(self.toolhead.get_position()[0:2].append(0), 100))
    def send_down_Z(self):
        self.reactor.register_async_callback(lambda e: self.toolhead.move(self.toolhead.get_position()[0:2].append(1000), 100)) 
    def send_stop_Z(self):
        self.reactor.register_async_callback(lambda e: self.toolhead.move_queue.flush())
    def send_home_Z(self):
        self.reactor.register_async_callback(lambda e: self.gcode.cmd_G28("Z"))
    def send_stop(self):
        print("stop print")
        self.state = "normal"
        self.notify.show(message="Printing stopped", level="error")
    def send_play(self):
        print("resume print")
        self.state = "printing"
        self.notify.show("Printing", "Started printing now", log=False)
    def send_pause(self):
        print("pause print")
        self.state = "paused"
        self.notify.show("Paused", level="warning", delay=4, color=[0, 0, 0.5, 0.5])

    def send_calibrate(self):
        print("calibrate")

    def send_acc(self, val):
        print("Sent Accelleration of {} to printer".format(val))
    def request_acc(self):
        return 36

    def poweroff(self):
        Popen(['sudo','systemctl', 'poweroff'])
    def reboot(self):
        Popen(['sudo','systemctl', 'reboot'])
    def restart_klipper(self):
        def restart(e=None):
            self.printer.run_result = 'fimrmware_restart'
            self.printer.reactor.end()
        self.reactor.register_async_callback(restart())
    def quit(self):
        Popen(['sudo', 'systemctl', 'stop', 'klipper.service'])

    def setup_after_run(self, dt):
        self.root_window.set_vkeyboard_class(UltraKeyboard)
        self.notify = Notifications(padding=(10, 10), height=100)
    
def load_config(config): #Entry point
    kgui_object = mainApp(config)
    kgui_object.start()
    return kgui_object

if __name__ == "__main__":
    import time
    mainApp().run()

