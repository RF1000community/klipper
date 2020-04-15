#!/usr/bin/env python2
# coding: utf-8
import logging
import site
import threading
import os
from os.path import join, abspath, expanduser, basename, splitext, dirname
from datetime import datetime, timedelta
from subprocess import Popen

TESTING = __name__ == "__main__"
if not TESTING:
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'gl'

from kivy import kivy_data_dir
from kivy.app import App
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock
from kivy.config import Config
from kivy.lang import Builder
from kivy.properties import OptionProperty, BooleanProperty, DictProperty, NumericProperty

from elements import UltraKeyboard
from files import *
from freedir import freedir
from timeline import *
from home import *
from settings import *
from status import *
from update import *
from kconfig_ui import *
import parameters as p

if not TESTING:
    site.addsitedir(dirname(dirname(p.kgui_dir)))
    from reactor import ReactorCompletion


# inherit from threading.thread => inherits start() method to run() in new thread
class mainApp(App, threading.Thread): #Handles Communication with Klipper

    # Property for controlling the state as shown in the statusbar.
    state = OptionProperty("initializing", options=[
        # Every string set has to be in this list
        "initializing",
        "ready",
        "error",
        "error disconnected"
        ])
    print_state = OptionProperty("no printjob", options=[
        "no printjob",
        "queued",
        "printing",
        "pausing",
        "paused",
        "stopping",
        "stopped",
        "done",
        ])
    homed = DictProperty({}) #updated by handle_homed event handler
    temp = DictProperty({}) #{'B':[setpoint, current], 'T0': ...} updated by scheduled update_home -> get_temp
    printer_objects_available = BooleanProperty(False) #updated with handle_connect
    jobs = ListProperty()
    print_time = StringProperty() #updated by get_printjob_progress
    print_done_time = StringProperty()
    print_title = StringProperty()
    progress = NumericProperty(0) #updated by scheduled update_home
    pos = ListProperty([0,0,0,0]) #updated by scheduled update_home
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

    def __init__(self, config = None, **kwargs):
        logging.info("Kivy app initializing...")
        self.notify = Notifications()
        self.temp = {'T0':(0,0), 'T1':(0,0), 'B':(0,0)}
        self.homed = {'x':False, 'y':False, 'z':False}
        self.scheduled_updating = None
        self.z_timer = None
        self.extrude_timer = None
        self.filament_manager = None
        self.bed_mesh = True #initialize as True so it shows up on load, maybe dissapears after handle_connect
        self.sdcard = None
        self.history = None
        self.printjob_progress = None
        if not TESTING:
            self.clean()
            self.kgui_config = config
            self.printer = config.get_printer()
            self.reactor = self.printer.get_reactor()
            self.klipper_config_manager = self.printer.objects['configfile']
            self.klipper_config = self.klipper_config_manager.read_main_config()
            #read config
            self.invert_z_controls = self.kgui_config.getboolean('invert_z_controls', False)
            self.xy_homing_controls = self.kgui_config.getboolean('xy_homing_controls', True)
            stepper_config = {'x': self.klipper_config.getsection('stepper_x'),
                              'y': self.klipper_config.getsection('stepper_y'),
                              'z': self.klipper_config.getsection('stepper_z')}
            self.pos_max = {i:stepper_config[i].getfloat('position_max', 200) for i in ('x','y','z')}
            self.pos_min = {i:stepper_config[i].getfloat('position_min', 0) for i in ('x','y','z')}#maybe use position_min, position_max = rail.get_range()
            self.filament_diameter = self.klipper_config.getsection("extruder").getfloat("filament_diameter", 1.75)
            self.min_extrude_temp = self.klipper_config.getsection("extruder").getint("min_extrude_temp", 170) # mantain this by keeping default the same as klipper            
            #count how many extruders exist before drawing homescreen
            for i in range(1, 10):
                try: klipper_config.getsection('extruder{i}'.format(**locals()))
                except: self.extruder_count = i; break
            #register event handlers
            self.printer.register_event_handler("klippy:connect", self.handle_connect) #printer_objects are available
            self.printer.register_event_handler("klippy:ready", self.handle_ready) #connect handlers have run
            self.printer.register_event_handler("klippy:disconnect", self.handle_disconnect)
            self.printer.register_event_handler("klippy:shutdown", self.handle_shutdown)
            self.printer.register_event_handler("klippy:exception", self.handle_exception)
            self.printer.register_event_handler("homing:home_rails_end", self.handle_homed)
            self.printer.register_event_handler("virtual_sdcard:printjob_change", self.handle_printjob_change)
        else:
            site.addsitedir(dirname(p.kgui_dir))
            import filament_manager
            self.filament_manager = filament_manager.load_config(None)
            self.pos_max = {'x':200, 'y':0}
            self.pos_min = {'x':0, 'y':0}
            self.filament_diameter = 1.75
            self.xy_homing_controls = True
            self.extruders = [None, None]
            self.extruder_count = 2
        self.kv_file = join(p.kgui_dir, "kv/main.kv") # tell the app class where the root kv file is
        super(mainApp, self).__init__(**kwargs)

    def clean(self):
        ndel, freed = freedir(p.sdcard_path)
        if ndel:
            self.notify.show("Disk space freed", "Deleted {} files, freeing {} MiB".format(ndel, freed))

    def handle_connect(self): #runs in klippy thread
        self.fan = self.printer.lookup_object('fan', None)
        self.gcode = self.printer.lookup_object('gcode')
        self.sdcard = self.printer.lookup_object('virtual_sdcard')
        self.history = self.printer.lookup_object('printjob_history')
        self.printjob_progress = self.printer.lookup_object('printjob_progress')
        self.toolhead = self.printer.lookup_object('toolhead')
        self.bed_mesh = self.printer.lookup_object('bed_mesh', None)
        self.filament_manager = self.printer.lookup_object('filament_manager', None)
        self.heater_manager = self.printer.lookup_object('heater', None)
        self.heaters = {}
        if 'heater_bed' in self.heater_manager.heaters: 
            self.heaters['B'] = self.heater_manager.heaters['heater_bed']
        for i in range(self.extruder_count):
            self.heaters['T{}'.format(i)] = self.heater_manager.heaters['extruder{}'.format('' if i==0 else i)]
        self.extruders = []
        for i in range(self.extruder_count):
            self.extruders.append(self.printer.lookup_object('extruder{}'.format('' if i==0 else i)))

        self.printer_objects_available = True
        Clock.schedule_once(self.bind_updating, 0)
        Clock.schedule_once(self.control_updating, 0)

    def handle_ready(self):
        self.state = "ready"

    # is called when system shuts down all work, either
    # to halt so the user can see what he did wrong
    # or to fully exit afterwards
    def handle_shutdown(self):
        self.state = "error"

    def handle_exception(self, message):
        self.state = "error"
        ErrorPopup(message = message).open()

    def handle_disconnect(self):
        self.state = "error disconnected"

    def handle_homed(self, rails):
        for rail in rails:
            self.homed[rail.steppers[0].get_name(short=True)] = True

    def handle_printjob_change(self):
        jobs = self.sdcard.jobs

        # check if queue has increased
        if len(jobs) > max(len(self.jobs), 1):
            self.notify.show("Added Printjob", "Added {} to print Queue".format(jobs[-1].name))

        self.jobs = jobs

        # get current print_state
        if len(self.jobs):
            self.print_title = self.jobs[0].name
            state = self.jobs[0].state
        else:
            state = "no printjob"

        # react to state change
        if self.print_state != state:
            if state == 'no printjob':
                Clock.schedule_once(lambda dt: self.hide_printjob(jobs[0].name), 3600) # show old printjob for 1h then throw it out
            elif state == 'printing' and self.print_state not in ('paused', 'pausing'):
                self.notify.show("Started printing", "Started printing {}".format(self.jobs[0].name), delay=4)
            elif state == 'done':
                self.progress = 1
                self.print_done_time = "done" 
                self.print_time = ""
            elif state == 'stopped':
                self.print_done_time = "stopped"
                self.print_time = ""
            self.print_state = state

    def hide_printjob(self, name):
        if self.print_state == 'no printjob' and self.print_title == name:
            self.print_title = ""

### KLIPPY THREAD ^
########################################################################################
### KGUI   THREAD v

    def run(self):
        logging.info("Kivy app.run")
        Clock.schedule_once(self.setup_after_run, 1)
        super(mainApp, self).run()

    def setup_after_run(self, dt):
        try:
            self.root_window.set_vkeyboard_class(UltraKeyboard)
        except:
            logging.warning("root_window wasnt available")

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
            self.scheduled_updating = Clock.schedule_interval(self.update_setting, 2.2)

    def update_home(self, *args):
        self.get_homing_state()
        self.get_temp()
        self.get_pos()

    def update_printing(self, *args):
        self.get_printjob_progress()
        self.get_pressure_advance()
        self.get_acceleration()
        self.get_z_adjust()
        self.get_speed()
        self.get_flow()
        self.get_temp()
        self.get_fan()

    def update_setting(self, *args):
        self.get_config('extruder', 'pressure_advance', 'default_pressure_advance', 'float')
        self.get_config('printer', 'max_accel', 'default_acceleration', 'float')

    def get_printjob_progress(self, *args):
        def format_time(seconds):
            minutes = int((seconds % 3600) // 60)
            hours  =  int(seconds // 3600)
            if hours:
                return "{hours} hours, {minutes} minutes".format(**locals())
            else:
                return "{minutes} minutes".format(**locals())

        est_remaining, progress = self.printjob_progress.get_print_time_prediction()
        if progress is None: # no prediction could be made yet
            logging.info("progresss is none")
            self.progress = 0
            self.print_time = ""
            self.print_done_time = ""
        else:
            remaining = timedelta(seconds = est_remaining)
            done = datetime.now() + remaining
            tomorrow = datetime.now() + timedelta(days=1)
            self.progress = progress
            self.print_time = format_time(remaining.total_seconds()) + " remaining"
            if done.day == datetime.now().day:
                self.print_done_time = done.strftime("ca. %-H:%M")
            elif done.day == tomorrow.day:
                self.print_done_time = done.strftime("tomorrow %-H:%M") # "ca. doesnt fit on screen
            else:
                self.print_done_time = done.strftime("ca. %a %-H:%M")

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
        if TESTING:
            setattr(self, property_name, 77)
            return
        def read_config(e):
            Section = self.klipper_config.getsection(section)
            if ty == 'int': # int option might be dangerous since a .0 brakes it, e.g. when overridding config
                val = Section.getint(option)
            elif ty == 'float':
                val = Section.getfloat(option)
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
            self.write_config('extruder{}'.format(i if i != 0 else ''), 'pressure_advance', val)

    def get_temp(self, dt=None):
        # schedule reading temp in klipper thread which schedules displaying the read value in kgui thread
        def read_temp(e):
            if self.heater_manager is not None:
                t = {}
                for tool_id, sensor in self.heater_manager.get_gcode_sensors():
                    current, target = sensor.get_temp(self.reactor.monotonic()) #get temp at current point in time
                    self.temp[tool_id] = (target, current)
        self.reactor.register_async_callback(read_temp)

    def send_temp(self, temp, tool_id):
        def change_temp(e):
            self.heaters[tool_id].set_temp(temp)
            current = self.temp[tool_id]
            self.temp[tool_id] = (temp, current[1])
        self.reactor.register_async_callback(change_temp)

    def get_homing_state(self):
        homed_axes_string = self.toolhead.get_status(self.reactor.monotonic())['homed_axes']
        for axis in self.homed.keys():
            self.homed[axis] = axis in homed_axes_string

    def send_home(self, axis):
        self.reactor.register_async_callback((lambda e: self.gcode.cmd_G28(axis.upper())))

    def send_motors_off(self):
        self.reactor.register_async_callback(lambda e: self.gcode.run_script_from_command("M18"))

    def get_pos(self):
        def read_pos(e):
            self.pos = self.toolhead.get_position()
        self.reactor.register_async_callback(read_pos)

    def send_pos(self, x=None, y=None, z=None, e=None, speed=15):  
        def set_pos(e):
            pos = self.toolhead.get_position()
            new_pos = [x,y,z,e]
            homed_axes = self.toolhead.get_status(self.reactor.monotonic())['homed_axes']
            new_pos = [new_pos[i] if p in homed_axes else None for i, p in enumerate('xyze')] #check whether axes are still homed
            pos = [p if p is not None else pos[i] for i, p in enumerate(new_pos)] #replace coordinates not given with current pos
            self.toolhead.move(pos, speed)
        self.reactor.register_async_callback(set_pos)


    def send_rel_pos(self, x=0, y=0, z=0, e=0, speed=15): # only execute this in klipper thread  
        cur_pos = self.toolhead.get_position()
        new_pos = [x,y,z,e]
        homed_axes = self.toolhead.get_status(self.reactor.monotonic())['homed_axes']
        for i, (new, name) in enumerate(zip(new_pos, "xyze")):
            if name == "e":
                cur_pos[i] += new
            elif name in homed_axes:
                cur_pos[i] += new
                if cur_pos[i] > self.pos_max[name]: # don't exceed physical limits
                    cur_pos[i] = self.pos_max[name]
                if cur_pos[i] < self.pos_min[name]:
                    cur_pos[i] = self.pos_min[name]
        self.toolhead.move(cur_pos, speed)

    def send_z_up(self, direction=1):
        def start_z(e):
            pos = self.toolhead.get_position()
            pos[2] = (self.pos_max['z'] if direction==1 else self.pos_min['z'])

            self.toolhead.flush_step_generation()
            kin = self.toolhead.get_kinematics()
            steppers = kin.get_steppers()

            for s in steppers:
                s.set_tag_position(s.get_commanded_position())

            self.z_start_mcu_pos = [(s, s.get_mcu_position()) for s in steppers]

            self.z_move_completion = ReactorCompletion(self.reactor)
            self.reactor.register_async_callback(lambda e: self.toolhead.drip_move(pos, 1, self.z_move_completion))
        self.reactor.register_async_callback(start_z)

    def send_z_stop(self):
        def stop_z(e):
            self.z_move_completion.complete(True)
            # Determine stepper halt positions
            self.reactor.register_async_callback(set_z_pos, 10)

        def set_z_pos(e):
            logging.info("set position")
            self.toolhead.flush_step_generation()
            #                   v--start_pos     v--end_pos
            end_mcu_pos = [(s, spos, s.get_mcu_position()) for s, spos in self.z_start_mcu_pos]
            for s, spos, epos in end_mcu_pos:
                logging.info("s{}, spos{}, epos {}".format(s, spos, epos))
                md = (epos - spos) * s.get_step_dist()
                s.set_tag_position(s.get_tag_position() + md)
            logging.info("tag pos = {}".format(self.toolhead.get_kinematics().calc_tag_position()))
            self.toolhead.set_position(self.toolhead.get_kinematics().calc_tag_position())

        self.reactor.register_async_callback(stop_z)
        
    def send_extrude(self, tool_id, direction=1):
        self.reactor.register_async_callback(lambda evt: self.send_rel_pos(e=10, speed=5))

    def send_extrude_stop(self):
        pass

    def send_calibrate(self):
        self.reactor.register_async_callback((lambda e: self.bed_mesh.calibrate.cmd_BED_MESH_CALIBRATE(None)))

    def send_print(self, filepath):
        self.reactor.register_async_callback(lambda e: self.sdcard.add_printjob(filepath))

    def send_stop(self):
        self.reactor.register_async_callback(lambda e: self.sdcard.stop_printjob())

    def send_pause(self):
        self.reactor.register_async_callback(lambda e: self.sdcard.pause_printjob())

    def send_resume(self):
        self.reactor.register_async_callback(lambda e: self.sdcard.resume_printjob())

    def poweroff(self):
        Popen(['sudo','systemctl', 'poweroff'])
    def reboot(self):
        Popen(['sudo','systemctl', 'reboot']) 
    def restart_klipper(self):
        """Quit and restart klipper and GUI"""
        self.reactor.register_async_callback(lambda e: self.printer.request_exit('firmware_restart') , 0)
    def quit(self):
        """Stop klipper and GUI, returns to tty"""
        self.reactor.register_async_callback(lambda e: self.printer.request_exit("exit"), 0)

########################################################################################
### KLIPPY THREAD v

class PopupExceptionHandler(ExceptionHandler):
    logging.info("handle_exception")
    def handle_exception(self, exception):
        if not TESTING:
            App.get_running_app().handle_exception(repr(exception))
            logging.exception(exception)
            return ExceptionManager.PASS

def set_kivy_config():
    # This needs an absolute path otherwise config will only be loaded when
    # working directory is the parent directory
    if TESTING:
        Config.read(join(p.kgui_dir, "config_test.ini"))
    else:
        Config.read(join(p.kgui_dir, "config.ini"))
        # Read the display rotation value
        try:
            with open("/boot/config.txt", "r") as file_:
                lines = file_.read().splitlines()
        except IOError:
            # Assume 90 degree rotation (config default) in case
            # /boot/config.txt isn't found
            rotation = 1
        else:
            rotation_string = [i for i in lines if i.startswith("display_hdmi_rotate")][0]
            # The number should always be at index 20
            rotation = int(rotation_string[20])
        # rotation should only be 1 for 90deg or 3 for 270deg
        # Set the input config option to rotate the touchinput explicitly for kivy
        if rotation == 3:
            Config.set("input", "device_%(name)s",
                "probesysfs,provider=mtdev,param=rotation=270,param=invert_y=1")

    #load a custom style.kv with changes to filechooser and more
    Builder.unload_file(join(kivy_data_dir, "style.kv"))

    # All files to read (order is important)
    # main.kv is read automatically
    kv_files = ("style.kv", "overwrites.kv", "elements.kv", "home.kv", "timeline.kv", "files.kv", "settings.kv")
    for fname in kv_files:
        Builder.load_file(join(p.kgui_dir, "kv", fname))

# Catch KGUI exceptions and display popup
ExceptionManager.add_handler(PopupExceptionHandler())
# Add parent directory to sys.path so kv-files (kivy/../parser.py) can import from it
site.addsitedir(p.kgui_dir)
# Read custom Kivy config file, set rotation and load custom style.kv
set_kivy_config()

# Entry point, order of execution: __init__()  run()  main.kv  setup_after_run()  handle_connect()  handle_ready()
def load_config(config):
    kgui_object = mainApp(config)
    kgui_object.start()
    return kgui_object

if TESTING:
    mainApp().run()
