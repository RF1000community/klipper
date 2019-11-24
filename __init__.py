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
from kivy.properties import OptionProperty, BooleanProperty, DictProperty
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

#add threading.thread => inherits start() method to run() in new thread
class mainApp(App, threading.Thread):

    # Property for controlling the state as shown in the statusbar.
    state = OptionProperty("ready", options=[
        # Every string set has to be in this list
        "ready",
        "printing",
        "paused",
        "error",
        "error disconnected",
        "initializing",
        ])
    homed_z = BooleanProperty(False)
    printer_objects_available = BooleanProperty(False)
    temp = DictProperty({}) #[setpoint, current, "setpoint", "current"]
    print_title = StringProperty()
    print_time = StringProperty()

    def __init__(self, config = None, **kwargs):# runs in klippy thread
        logging.info("Kivy app initializing...")
        self.temp = {'T0':(0,0,'--','--'),
                     'T1':(0,0,'--','--'),
                      'B':(0,0,'--','--')}
        if not testing:
            self.kgui_config = config
            self.printer = config.get_printer()
            self.klipper_config = self.printer.objects['configfile'].read_main_config()
            stepper_conf = (self.klipper_config.getsection('stepper_x'),
                            self.klipper_config.getsection('stepper_y'),
                            self.klipper_config.getsection('stepper_z'))
            self.pos_max = [stepper_conf[i].getint('position_max') for i in (0,1,2)]
            try: self.pos_min = [stepper_conf[i].getint('position_min') for i in (0,1)]
            except: self.pos_min = (0,0)
            self.reactor = self.printer.get_reactor()
            self.printer.register_event_handler("klippy:connect", self.handle_connect) # all printer_objects are available
            self.printer.register_event_handler("klippy:ready", self.handle_ready) # all the connect handlers have run
            self.printer.register_event_handler("klippy:disconnect", self.handle_disconnect)
            self.printer.register_event_handler("homing:homed_rails", self.handle_homed)
            self.printer.register_event_handler("klippy:shutdown", self.handle_shutdown)
            self.printer.register_event_handler("toolhead:sync_print_time", self.handle_calc_print_time)
        else:
            self.pos_max = (200,200)
            self.pos_min = (0,0)
        super(mainApp, self).__init__(**kwargs)

    def run(self):
        logging.info("Kivy app.run")
        Clock.schedule_once(self.setup_after_run, 0)
        super(mainApp, self).run()

    def handle_connect(self): # the handlers are not thread safe!
        self.gcode = self.printer.lookup_object('gcode')
        self.toolhead = self.printer.lookup_object('toolhead')
        self.sdcard = self.printer.lookup_object('virtual_sdcard', None)
        self.fan = self.printer.lookup_object('fan', None)
        self.extruder0 = self.printer.lookup_object('extruder0', None)
        self.extruder1 = self.printer.lookup_object('extruder1', None)
        self.bed_mesh = self.printer.lookup_object('bed_mesh', None)
        self.heaters = self.printer.lookup_object('heater', None)
        self.heater = {}
        try: self.heater['B'] = self.printer.lookup_object('heater_bed', None)
        except: logging.info("heated bed not found")
        try: self.heater['T0'] = self.heaters.lookup_heater('extruder0')
        except: logging.info("T0 not found")
        try: self.heater['T1'] = self.heaters.lookup_heater('extruder0')
        except: logging.info("T1 not found")

        self.printer_objects_available = True
        Clock.schedule_interval(self.get_temp, 0.7)
    
    def handle_ready(self):
        self.state = "ready"
    
    def handle_disconnect(self):
        self.state = "error disconnected"
        
    def handle_shutdown(self):
        logging.info("handled shutdown @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        self.stop()
        
    def handle_homed(self, homing, rails):
        for rail in rails:
            if rail.name == 'z':
                self.homed_z = True
                
    def handle_calc_print_time(self, curtime, est_print_time, print_time):
        p_time = str(est_print_time)
        self.print_time = p_time

    def get_pressure_advance(self):
        return 0.1
    def send_pressure_advance(self, val):
        pass

    def get_config(self, section, element):
        def read_config(section, element):
            Section = self.klipper_config.getsection(section)
            #wip
        self.reactor.register_async_callback(read_config(section, elements))

    def write_config(self):
        pass

    def get_z_adjust(self):
        return 0.1
    def send_z_adjust(self, val):
        pass

    def get_speed(self):
        return 77
    def send_speed(self,val):
        print("send {} as speed".format(val))

    def get_flow(self):
        return 107
    def send_flow(self, val):
        print("send {} as flow".format(val))

    def get_fan(self):
        return 77
    def send_fan(self, speed):
        logging.info("KGUI send {} as fan speed".format(speed))
        self.reactor.register_async_callback(lambda e: self.fan.set_speed(self.toolhead.get_last_move_time(), speed))

    def get_temp(self, dt=None):
        # schedule reading temp in klipper thread which schedules displaying the read value in kgui thread
        def read_temp(e):
            if self.heaters is not None:
                t = {}
                for heater_id, sensor in self.heaters.get_gcode_sensors():
                    current, target = sensor.get_temp(self.reactor.monotonic()) #get temp at current point in time
                    if target == 0: target_str = "Off"
                    else: target_str = str(target)+"°C"
                    t[heater_id] = (target, current, target_str, "{:4.1f}".format(current))
                self.temp.update(t)
        self.reactor.register_async_callback(read_temp)
                
    def send_temp(self, temp, heater_id):
        logging.info("KGUI set Temperature of {} to {}".format(heater_id, temp))
        self.reactor.register_async_callback((lambda e: self.heater[heater_id].set_temp(self.toolhead.get_last_move_time(), temp)))

    def send_pos(self, x=None, y=None, z=None, e1=None, e2=None):
        def set_pos(e, pos):
            current_pos = self.toolhead.get_position()
            xyz = [current_pos[i] if p is None else p for i,p in enumerate(pos)]
            self.toolhead.set_position(xyz) # resets all queued moves and sets pos
        pos = (x,y,z,e1,e2)
        self.reactor.register_async_callback(set_pos(pos=pos))
    
    def get_pos(self):
        def read_pos():
            pos = self.toolhead.get_pos()
            self.pos = pos
        self.reactor.register_async_callback(read_pos)
    
    def send_up_Z(self):
        self.send_pos(z=0)
    def send_down_Z(self):
        z = self.pos_max[2]
        self.send_pos(z=z)
    def send_stop_Z(self):
        self.reactor.register_async_callback((lambda e: self.toolhead.move_queue.flush()))
    def send_home_Z(self):
        self.reactor.register_async_callback((lambda e: self.gcode.cmd_G28("Z")))

    def send_stop(self):
        print("stop print")
        self.state = "ready"
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
        self.reactor.register_async_callback((lambda e: self.bed_mesh.calibrate.cmd_BED_MESH_CALIBRATE(0)))

    def send_acc(self, val):
        print("Sent Accelleration of {} to printer".format(val))
    def request_acc(self):
        return 36

    def poweroff(self):
        Popen(['sudo','systemctl', 'poweroff'])
    def reboot(self):
        Popen(['sudo','systemctl', 'reboot'])
    def restart_klipper(self):
        self.reactor.register_async_callback((lambda e: self.gcode.cmd_FIRMWARE_RESTART(0)))
        self.stop()
        """
        def restart(e=None):
            self.printer.run_result = 'fimrmware_restart'
            self.printer.reactor.end()
        self.reactor.register_async_callback(restart())"""
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
    mainApp().run()

