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
from kivy import kivy_data_dir
from kivy.lang import Builder
from kivy.app import App
from kivy.config import Config
from kivy.clock import Clock
from kivy.properties import OptionProperty, BooleanProperty, DictProperty, NumericProperty
from os.path import join, abspath, expanduser, basename, splitext
from subprocess import Popen
import threading
import logging
import site

from elements import UltraKeyboard
from files import *
from home import *
from nm_dbus import *
import parameters as p
from settings import *
from status import *


#add parent directory to sys.path so main.kv (parser.py) can import from it
site.addsitedir(p.kgui_dir)

#this needs an absolute path otherwise config will only be loaded when working directory is the parent directory
if testing: Config.read(join(p.kgui_dir, "config-test.ini"))
else:       Config.read(join(p.kgui_dir, "config.ini"))

#load a custom style.kv with changes to filechooser and more
Builder.unload_file(join(kivy_data_dir, "style.kv"))
Builder.load_file(join(p.kgui_dir, "style.kv"))

#add threading.thread => inherits start() method to run() in new thread
class mainApp(App, threading.Thread): #Handles Communication with Klipper

    #Property for controlling the state as shown in the statusbar.
    state = OptionProperty("initializing", options=[
        # Every string set has to be in this list
        "busy",
        "ready",
        "printing",
        "pausing",
        "paused",
        "print finished",
        "error",
        "error disconnected",
        "initializing",
        ])
    homed = DictProperty({}) #updated by handle_homed event handler
    temp = DictProperty({}) #{'B':[setpoint, current], 'T0': ....} updated by scheduled update_home -> get_temp
    printer_objects_available = BooleanProperty(False) #updated with handle_connect
    print_title = StringProperty() #updated by on_state watching state chages to 'printing'
    print_time = StringProperty() #updated by handle_print_time_calc
    progress = NumericProperty() #updated by scheduled update_home
    #self.progress = self.sdcard.get_status(e)['progress']
    pos = ListProperty([0,0,0]) #updated by scheduled update_home
    #tuning  #updated by upate_printing
    speed = NumericProperty(100)
    flow = NumericProperty(100)
    fan_speed = NumericProperty(0)
    z_adjust = NumericProperty(0)
    acceleration = NumericProperty(2000)
    pressure_advance = NumericProperty(0)
    #config
    default_pressure_advance = NumericProperty(0)
    default_acceleration = NumericProperty(2000)

    def __init__(self, config = None, **kwargs): #runs in klippy thread
        logging.info("Kivy app initializing...")
        self.network_manager = NetworkManager()
        self.temp = {'T0':(0,0), 'T1':(0,0), 'B':(0,0)}
        self.homed = {'x':False, 'y':False, 'z':False}
        self.scheduled_updating = None
        if not testing:
            self.kgui_config = config
            self.printer = config.get_printer()
            self.reactor = self.printer.get_reactor()
            self.klipper_config_manager = self.printer.objects['configfile']
            self.klipper_config = self.klipper_config_manager.read_main_config()

            #read config
            p.invert_z_controls = self.kgui_config.get('invert_z_controls', False)
            stepper_config = {'x': self.klipper_config.getsection('stepper_x'),
                              'y': self.klipper_config.getsection('stepper_y'),
                              'z': self.klipper_config.getsection('stepper_z')}
            self.pos_max = {i:stepper_config[i].getfloat('position_max', 200) for i in ('x','y','z')}
            self.pos_min = {i:stepper_config[i].getfloat('position_min', 0) for i in ('x','y','z')}#maybe use position_min, position_max = rail.get_range()
            #count how many extruders exist before drawing homescreen
            for i in range(1, 10):
                try: klipper_config.getsection('extruder' + str(i))
                except: self.extruder_count = i; break
            #check whether the right sdcard path is configured
            configured_sdpath = expanduser(self.klipper_config.getsection("virtual_sdcard").get("path", None))
            if abspath(configured_sdpath) != abspath(p.sdcard_path):
                logging.warning("virtual_sdcard path misconfigured: is {} and not {}".format(configured_sdpath, p.sdcard_path))
            #register event handlers
            self.printer.register_event_handler("klippy:connect", self.handle_connect) #printer_objects are available
            self.printer.register_event_handler("klippy:ready", self.handle_ready) #connect handlers have run
            self.printer.register_event_handler("klippy:disconnect", self.handle_disconnect)
            self.printer.register_event_handler("klippy:shutdown", self.handle_shutdown)
            self.printer.register_event_handler("klippy:exception", self.handle_klippy_exception)
            self.printer.register_event_handler("homing:homed_rails", self.handle_homed)
            self.printer.register_event_handler("toolhead:sync_print_time", self.handle_calc_print_time)
        else:
            self.pos_max = {'x':200, 'y':0}
            self.pos_min = {'x':0, 'y':0}
            self.extruder_count = 3
        super(mainApp, self).__init__(**kwargs)

    def handle_connect(self): #runs in klippy thread
        self.fan = self.printer.lookup_object('fan', None)
        self.gcode = self.printer.lookup_object('gcode')
        self.sdcard = self.printer.lookup_object('virtual_sdcard', None)
        self.toolhead = self.printer.lookup_object('toolhead')
        self.bed_mesh = self.printer.lookup_object('bed_mesh', None)
        self.extruders = []
        for i in range(0,10):
		    ext = self.printer.lookup_object('extruder{}'.format('' if i==0 else i), None)
		    if ext: self.extruders.append(ext)
        self.heater_manager = self.printer.lookup_object('heater', None)
        self.heaters = {}
        if 'heater_bed' in self.heater_manager.heaters: self.heaters['B'] = self.heater_manager.heaters['heater_bed']
        for i in range(self.extruder_count):
            self.heaters['T'+str(i)] = self.heater_manager.heaters['extruder' + '' if i==0 else i]

        self.printer_objects_available = True
        Clock.schedule_once(self.bind_updating, 0)
        Clock.schedule_once(self.control_updating, 0)
        Clock.schedule_interval(self.update_always, 0.3)

    def handle_ready(self):
        self.state = "ready"

    def handle_disconnect(self):
        self.state = "error disconnected"
        logging.info("run handle_disconnect -> shutdown gui")
        self.handle_shutdown()

    def handle_shutdown(self): # is called when system shuts down
        logging.info("handled shutdown ")
        self.stop()

    def handle_homed(self, homing, rails):
        for rail in rails:
            self.homed[rail.steppers[0].get_name(short=True)] = True

    def handle_calc_print_time(self, curtime, est_print_time, print_time):
        hours = int(est_print_time//3600)
        minutes = int(est_print_time%3600)/60
        self.print_time = "{}:{:02} remaining".format(hours, minutes)
        self.progress = print_time/float(est_print_time)
    
    def handle_klippy_exception(self, exc):
        self.state = "error"
        ErrorPopup(message=exc).open()
        
### KLIPPER THREAD ^
########################################################################################
### KGUI    THREAD v
        
    def run(self):
        logging.info("Kivy app.run")
        super(mainApp, self).run()

    def on_start(self, *args):
        self.notify = Notifications()
        if self.network_manager.available:
            self.network_manager.start()
        try:
            self.root_window.set_vkeyboard_class(UltraKeyboard)
        except:
            logging.warning("root_window wasnt available")

    def on_stop(self, *args):
        # Stop networking dbus event loop
        self.network_manager.loop.quit()

    def bind_updating(self, *args):
        self.root.ids.tabs.bind(current_tab=self.control_updating)
        self.root.ids.tabs.ids.home_tab.ids.hs_manager.bind(current=self.control_updating)

    def control_updating(self, *args):
        tab = self.root.ids.tabs.current_tab
        if self.scheduled_updating is not None:
            Clock.unschedule(self.scheduled_updating)
        if tab == self.root.ids.tabs.ids.home_tab:
            if tab.ids.hs_manager.current == "homescreen":
                self.update_home()
                self.scheduled_updating = Clock.schedule_interval(self.update_home, 1)
            if tab.ids.hs_manager.current == "printingscreen":
                self.update_printing()
                self.scheduled_updating = Clock.schedule_interval(self.update_printing, 1.5)
        if tab == self.root.ids.tabs.ids.set_tab:
            self.update_setting()
            self.scheduled_updating = Clock.schedule_interval(self.update_setting, 2)
            
    def update_always(self, *args):
        if not self.sdcard:
            logging.warning("sdcard not found")
            return
        s = 'ready'
        if 'Printer is ready' != self.printer.get_state_message():
		    s = 'initializing'
        if self.gcode.is_processing_data:
            s = 'busy'
        if self.sdcard.current_file:
            if self.sdcard.must_pause_work:
                s = 'pausing' if self.sdcard.work_timer else 'paused'
            elif self.sdcard.current_file and self.sdcard.work_timer:
                s = 'printing'
        self.state = s

    def update_home(self, *args):
        self.get_pos()
        self.get_temp()
        self.get_homing_state()

    def update_printing(self, *args):
        self.get_pressure_advance()
        self.get_acceleration()
        self.get_z_adjust()
        self.get_speed()
        self.get_flow()
        self.get_fan()
        self.get_temp()

    def update_setting(self, *args):
        self.get_config('printer', 'max_accel', 'default_acceleration', 'int')
        self.get_config('extruder', 'pressure_advance', 'default_pressure_advance')


    def on_state(self, instance, state):
        if state == 'printing' or state == 'busy':
            file = self.sdcard.current_file
            if file: 
                self.print_title = splitext(basename(file.name))[0] #remove file extension
                self.notify.show("Started printing", "Started printing {}".format(basename(file.name)))
            
##################################################################
### TUNING

    def get_z_adjust(self):
        self.z_adjust = self.gcode.homing_position[2]
    def send_z_adjust(self, offset):
        self.z_adjust = offset
        def set_z_offset(e):  
            #keeps the difference between base_position and homing_position the same
            #works like this: if base_position = 5, put origin of gcode coordinate system at + 5, 
            #used for z tuning or G92 zeroing
            delta = offset - self.gcode.homing_position[2] #difference between old and new offset
            self.gcode.base_position[2] += delta
            self.gcode.homing_position[2] = offset
            #Move to offset
            self.gcode.last_position[2] += delta
            self.gcode.move_with_transform(self.gcode.last_position, 5) #sets speed for adjustment move
        self.reactor.register_async_callback(set_z_offset)

    def get_speed(self):
        self.speed = self.gcode.speed_factor*60*100 #speed factor also converts from mm/sec to mm/min
    def send_speed(self, val):
        self.speed = val
        val = val/(60.*100.)
        def set_speed(e):
            self.gcode.speed = self.gcode._get_gcode_speed() * val
            self.gcode.speed_factor = val
        self.reactor.register_async_callback(set_speed)

    def get_flow(self):
        self.flow = self.gcode.extrude_factor*100
    def send_flow(self, val):
        self.flow = val
        def set_flow(e):
            new_extrude_factor = val/100.
            last_e_pos = self.gcode.last_position[3]
            e_value = (last_e_pos - self.gcode.base_position[3]) / self.gcode.extrude_factor
            self.gcode.base_position[3] = last_e_pos - e_value * new_extrude_factor
            self.gcode.extrude_factor = new_extrude_factor
        self.reactor.register_async_callback(set_flow)

    def get_fan(self):
        self.fan_speed = self.fan.last_fan_value * 100 / self.fan.max_power
    def send_fan(self, speed):
        self.fan_speed = speed
        self.reactor.register_async_callback(lambda e: self.fan.set_speed(self.toolhead.get_last_move_time(), speed/100.))
    
    def get_pressure_advance(self):#gives pressure_advance value of 1. extruder for now
        self.pressure_advance = self.extruders[0].get_status(self.reactor.monotonic())['pressure_advance']
    def send_pressure_advance(self, val):
        self.pressure_advance = val
        def set_pressure_advance(e):
            for extruder in self.extruders:
                extruder._set_pressure_advance(val, extruder.pressure_advance_smooth_time)
        self.reactor.register_async_callback(set_pressure_advance)

    def get_acceleration(self):
        self.acceleration = self.toolhead.max_accel
    def send_acceleration(self, val):
        self.acceleration = val
        self.toolhead.max_accel = val
        self.reactor.register_async_callback(lambda e: self.toolhead._calc_junction_deviation())

### TUNING
#####################################################################

    def get_config(self, section, option, property_name, ty=None):
        logging.info("wrote {} from section {} to {}".format(option, section, property_name))
        if testing:
            setattr(self, property_name, 77)
            return
        def read_config(e):
            Section = self.klipper_config.getsection(section)
            if ty == 'int':
                val = Section.getint(option)
            else:
                val = Section.get(option)
            setattr(self, property_name, val)
        self.reactor.register_async_callback(read_config)
    
    def set_config(self, section, option, value):
        logging.info("trying to set config section {} option {} to value {}".format(section, option, value))
        self.reactor.register_async_callback(lambda e: self.klipper_config_manager.set(section, option, value))

    def write_config(self, section, option, value):
        logging.info( 'trying to write section: {} option: {}, value: {} to config'.format(section, option, value))
        def write_conf(e):
            self.klipper_config_manager.set(section, option, value)
            self.klipper_config_manager.cmd_SAVE_CONFIG(None)
        self.reactor.register_async_callback(write_conf)

    def write_pressure_advance(self, val):
        for i in range(self.extruder_count):
            self.write_config('extruder{}'.format(i if i != '0' else ''), 'pressure_advance', val)

    def get_temp(self, dt=None):
        # schedule reading temp in klipper thread which schedules displaying the read value in kgui thread
        def read_temp(e):
            if self.heater_manager is not None:
                t = {}
                for heater_id, sensor in self.heater_manager.get_gcode_sensors():
                    current, target = sensor.get_temp(self.reactor.monotonic()) #get temp at current point in time
                    self.temp[heater_id] = (target, current)
        self.reactor.register_async_callback(read_temp)

    def send_temp(self, temp, heater_id):
        self.reactor.register_async_callback((lambda e: self.heaters[heater_id].set_temp(self.toolhead.get_last_move_time(), temp)))

    def get_homing_state(self):
        homed_axes_string = self.toolhead.get_status(self.reactor.monotonic())['homed_axes']
        for axis in self.homed.keys():
            self.homed[axis] = axis in homed_axes_string

    def send_home(self, axis):
        self.reactor.register_async_callback((lambda e: self.gcode.cmd_G28(axis.upper())))

    def send_motors_off(self):
        reactor.register_async_callback(lambda e: self.gcode.run_script_from_command("M18"))

    def get_pos(self):
        def read_pos(e):
            pos = self.toolhead.get_position()
            self.pos = pos
        self.reactor.register_async_callback(read_pos)

    def send_pos(self, x=None, y=None, z=None, e=None, speed=15):  
        def set_pos(e):
            pos = self.toolhead.get_position()
            new_pos = [x,y,z,e]
            homed_axes = self.toolhead.get_status(self.reactor.monotonic())['homed_axes']
            new_pos = [new_pos[i] if p in homed_axes else None for i, p in enumerate('xyze')] #check whether axes are still homed
            pos = [p if p is not None else pos[i] for i, p in enumerate(new_pos)] #replace coordinates not given with current pos
            self.toolhead.drip_move(pos, speed)
        self.reactor.register_async_callback(set_pos)

    def send_z_up(self):
        self.send_pos(z=self.pos_min['z'])
    def send_z_down(self):
        self.send_pos(z=self.pos_max['z'])
    def send_z_stop(self):
        self.reactor.register_async_callback((lambda e: self.toolhead.signal_drip_mode_end()))

    def send_calibrate(self):
        self.reactor.register_async_callback((lambda e: self.bed_mesh.calibrate.cmd_BED_MESH_CALIBRATE(0)))

    def send_start(self, file=None):
        if file:
            filename = basename(file) # remove path
            self.print_title = splitext(filename)[0] #remove file extension
            self.state = "printing"
            params = {'#original': "M23 " + filename}
        def start(e):
            try:
                if file: self.sdcard.cmd_M23(params)
                self.sdcard.cmd_M24(None)
            except:
                self.notify.show("Couldn't start Print, sdcard busy")
        self.reactor.register_async_callback(start)

    def send_stop(self):
        self.state = "print finished"
        self.notify.show("Printing stopped", level="error")
        self.reactor.register_async_callback(self.sdcard.cmd_M25)
    
    def send_play(self):
        self.state = "printing"
        self.gcode.run_script_from_command("RESTORE_GCODE_STATE STATE=PAUSE_STATE MOVE=1")
        self.reactor.register_async_callback(self.sdcard.cmd_M24)#works because cmd_M24 takes one argument but doesnt read it 

    def send_pause(self):
        self.state = "paused"
        self.notify.show("Paused", "Print paused", delay=4)
        self.reactor.register_async_callback(self.sdcard.cmd_M25)
        self.gcode.run_script_from_command("SAVE_GCODE_STATE STATE=PAUSE_STATE")

    def poweroff(self):
        Popen(['sudo','systemctl', 'poweroff'])
    def reboot(self):
        Popen(['sudo','systemctl', 'reboot'])
    def restart_klipper(self):
        """Quit and restart klipper and GUI"""
        logging.info("attempting a firmware restart")
        self.reactor.register_async_callback(self.gcode.cmd_FIRMWARE_RESTART, 10)
    def quit(self):
        """Stop klipper and GUI, returns to tty"""
        Popen(['sudo', 'systemctl', 'stop', 'klipper.service'])

#Entry point, order of execution: __init__()  run()  main.kv  setup_after_run()  handle_connect()  handle_ready()
def load_config(config):
    kgui_object = mainApp(config)
    kgui_object.start()
    return kgui_object

if __name__ == "__main__":
    mainApp().run()
