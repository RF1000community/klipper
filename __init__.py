#!/usr/bin/env python3
# coding: utf-8
import logging
import site
import threading
import os
import traceback
from os.path import join, dirname
from datetime import datetime, timedelta
from subprocess import Popen

TESTING = "KGUI_TESTING" in os.environ
if not TESTING:
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'sdl2'

from kivy import kivy_data_dir
from kivy.app import App
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock
from kivy.config import Config
from kivy.lang import Builder
from kivy.properties import (OptionProperty, BooleanProperty, DictProperty,
        NumericProperty, ListProperty, StringProperty, ObjectProperty)
logging.root = logging.getLogger("klippy") # Kivy can fuck right off and not overwrite the root logger
from .elements import UltraKeyboard, CriticalErrorPopup, ErrorPopup
from .freedir import freedir
from .nm_dbus import NetworkManager
from . import parameters as p
from .status import Notifications
# Imports for KvLang Builder
from . import files, home, settings, status, timeline, update

if not TESTING:
    site.addsitedir(dirname(dirname(p.kgui_dir)))
    from reactor import ReactorCompletion


# inherit from threading.thread => inherits start() method to run() in new thread
class mainApp(App, threading.Thread): #Handles Communication with Klipper

    # Property for controlling the state as shown in the statusbar.
    state = OptionProperty("startup", options=[
        # Every string set has to be in this list
        "ready",
        "startup",
        "shutdown",
        "error",
        "error disconnected"
        ])
    # this is more of a UI-state, it may be 'done' even though virtual_sdcard has no printjobs
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
    homed = DictProperty() #updated by handle_home_end/start event handler
    temp = DictProperty() #{'B':[setpoint, current], 'T0': ...} updated by scheduled update_home -> get_temp
    connected = BooleanProperty(False) #updated with handle_connect
    jobs = ListProperty()
    print_title = StringProperty()
    print_time = StringProperty() #updated by get_printjob_progress
    print_done_time = StringProperty()
    progress = NumericProperty(0) #updated by scheduled update_home
    pos = ListProperty([0, 0, 0, 0]) #updated by scheduled update_home
    toolhead_busy = BooleanProperty(False)
    z_move_completion = ObjectProperty(None, allownone=True)
    ext_move_completion = ObjectProperty(None, allownone=True)
    #tuning, updated by upate_printing
    speed = NumericProperty(100)
    flow = NumericProperty(100)
    fan_speed = NumericProperty(0)
    z_adjust = NumericProperty(0)
    acceleration = NumericProperty(2000)
    pressure_advance = NumericProperty(0)
    #config
    config_pressure_advance = NumericProperty(0)
    config_acceleration = NumericProperty(2000)

    def __init__(self, config = None, **kwargs):
        logging.info("Kivy app initializing...")
        self.network_manager = NetworkManager()
        self.notify = Notifications()
        self.temp = {'T0':[0,0], 'T1':[0,0], 'B':[0,0]}
        self.homed = {'x':False, 'y':False, 'z':False}
        self.warned_not_homed = {'x':False, 'y':False, 'z':False}
        self.scheduled_updating = None
        self.filament_manager = None
        self.curaconnection = None
        self.bed_mesh = True # initialize as True so it shows up on load, maybe dissapears after handle_connect
        self.sdcard = None
        self.print_stats = None
        if not TESTING:
            self.kgui_config = config
            self.printer = config.get_printer()
            self.reactor = self.printer.get_reactor()
            self.klipper_config_manager = self.printer.objects['configfile']
            self.klipper_config = self.klipper_config_manager.read_main_config()
            self.print_history = self.printer.load_object(config, 'print_history') # beware this is not the 'right' config
            self.gcode_metadata = self.printer.load_object(config, 'gcode_metadata')
            # read config
            self.z_speed = self.kgui_config.getfloat('manual_z_speed', 3)
            self.ext_speed = self.kgui_config.getfloat('manual_extrusion_speed', 2)
            self.invert_z_controls = self.kgui_config.getboolean('invert_z_controls', False)
            self.xy_homing_controls = self.kgui_config.getboolean('xy_homing_controls', True)
            stepper_config = {'x': self.klipper_config.getsection('stepper_x'),
                              'y': self.klipper_config.getsection('stepper_y'),
                              'z': self.klipper_config.getsection('stepper_z')}
            self.pos_max = {i:stepper_config[i].getfloat('position_max', 200) for i in 'xyz'}
            self.pos_min = {i:stepper_config[i].getfloat('position_min', 0) for i in 'xyz'}
            self.filament_diameter = self.klipper_config.getsection("extruder").getfloat("filament_diameter", 1.75)
            # maintain this by keeping default the same as klipper
            self.min_extrude_temp = self.klipper_config.getsection("extruder").getint("min_extrude_temp", 170)
            # count how many extruders exist before drawing homescreen
            for i in range(1, 10):
                try: klipper_config.getsection(f"extruder{i}")
                except: self.extruder_count = i; break
            # register event handlers
            self.printer.register_event_handler("klippy:connect", self.handle_connect) # printer_objects are available
            self.register_ui_event_handler("klippy:ready", self.handle_ready) # connect handlers have run
            self.register_ui_event_handler("klippy:disconnect", self.handle_disconnect)
            self.register_ui_event_handler("klippy:shutdown", self.handle_shutdown)
            self.register_ui_event_handler("klippy:critical_error", self.handle_critical_error)
            self.register_ui_event_handler("klippy:error", self.handle_error)
            self.register_ui_event_handler("homing:home_rails_end", self.handle_home_end)
            self.register_ui_event_handler("virtual_sdcard:printjob_start", self.handle_printjob_start)
            self.register_ui_event_handler("virtual_sdcard:printjob_end", self.handle_printjob_end)
            self.register_ui_event_handler("virtual_sdcard:printjob_change", self.handle_printjob_change)
            self.register_ui_event_handler("virtual_sdcard:printjob_added", self.handle_printjob_added)
            self.clean()
        else:
            site.addsitedir(dirname(p.kgui_dir))
            import filament_manager
            self.filament_manager = filament_manager.load_config(None)
            import gcode_metadata
            self.gcode_metadata = gcode_metadata.load_config(None)
            self.pos_max = {'x':200, 'y':0}
            self.pos_min = {'x':0, 'y':0}
            self.filament_diameter = 1.75
            self.xy_homing_controls = True
            self.extruders = [None, None]
            self.extruder_count = 2
            self.printer = self.reactor = self.print_history = None
        self.kv_file = join(p.kgui_dir, "kv/main.kv") # tell the app class where the root kv file is
        super().__init__(**kwargs)

    def clean(self):
        ndel, freed = freedir(p.sdcard_path)
        if ndel:
            self.notify.show("Disk space freed", f"Deleted {ndel} files, freeing {freed} MiB")
            self.print_history.trim_history()

    def handle_connect(self): # runs in klippy thread
        self.fan_manager = self.printer.lookup_object('fan', None)
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode_move = self.printer.lookup_object('gcode_move')
        self.sdcard = self.printer.lookup_object('virtual_sdcard')
        self.print_stats = self.printer.lookup_object('print_stats')
        self.toolhead = self.printer.lookup_object('toolhead')
        self.bed_mesh = self.printer.lookup_object('bed_mesh', None)
        self.filament_manager = self.printer.lookup_object('filament_manager', None)
        self.heater_manager = self.printer.lookup_object('heaters', None)
        self.curaconnection = self.printer.lookup_object('klipper_cura_connection', None)
        self.heaters = {}
        self.extruders = []
        if 'heater_bed' in self.heater_manager.heaters: 
            self.heaters['B'] = self.heater_manager.heaters['heater_bed']
        for i in range(self.extruder_count):
            self.heaters[f"T{i}"] = self.heater_manager.heaters[f"extruder{'' if i==0 else i}"]
            self.extruders.append(self.printer.lookup_object(f"extruder{'' if i==0 else i}"))
        Clock.schedule_once(self.ui_handle_connect, 0)

# KLIPPY THREAD ^
########################################################################################
# KGUI   THREAD v

    def ui_handle_connect(self, dt):
        self.connected = True
        self.root.ids.tabs.bind(current_tab=self.control_updating)
        self.root.ids.tabs.ids.home_tab.ids.hs_manager.bind(current=self.control_updating)
        self.control_updating()

    def handle_ready(self):
        self.state = "ready"

    # is called when system shuts down all work, either
    # to halt so the user can see what he did wrong
    # or to fully exit afterwards
    def handle_shutdown(self):
        pass

    def handle_disconnect(self):
        self.connected = False
        self.stop()

    def handle_critical_error(self, message):
        self.state = "error"
        CriticalErrorPopup(message = message).open()

    def handle_error(self, message):
        ErrorPopup(message = message).open()

    def handle_home_end(self, homing_state, rails):
        for rail in rails:
            self.homed[rail.steppers[0].get_name(short=True)] = True

    def handle_printjob_change(self, jobs):
        """ this monitors changes of 2 things:
            - the configuration of printjobs
            - the state of 1. printjob
            due to pass-by-reference states may be skipped """
        if len(jobs): # update print_state, unless there's no printjob
            self.print_state = jobs[0].state
        elif len(self.jobs): # if the job is already removed we still want to update state
            self.print_state = self.jobs[0].state
        self.jobs = jobs

    def handle_printjob_added(self, job):
        self.notify.show("Added Printjob", f"Added {job.name} to print Queue", delay=4)

    def handle_printjob_start(self, job):
        self.notify.show("Started printing", f"Started printing {job.name}", delay=5)
        self.print_title = job.name
        # this only works if we are in a printing state (we rely on this being called after handle_printjob_change)
        self.get_printjob_progress()

    def handle_printjob_end(self, job):
        if 'done' == job.state:
            self.progress = 1
            self.print_done_time = ""
            self.print_time = "finished in " + self.format_time(job.get_printed_time())
            Clock.schedule_once(lambda dt: self.hide_printjob(job.name), 3600) # show finished job for 1h
        else:
            self.hide_printjob(job.name)

    def hide_printjob(self, name):
        if not self.jobs and self.print_title == name:
            self.print_title = ""
            self.print_done_time = ""
            self.print_time = ""
            self.progress = 0
            self.print_state = "no printjob"
            self.reset_tuning() # tuning values are only reset once print_queue has run out

    def run(self):
        logging.info("Kivy app.run")
        super().run()

    def on_start(self, *args):
        if self.network_manager.available:
            self.network_manager.start()
        try:
            self.root_window.set_vkeyboard_class(UltraKeyboard)
        except:
            logging.warning("root_window wasnt available")

    def on_stop(self, *args):
        # Stop networking dbus event loop
        self.network_manager.stop()

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
        self.get_printjob_progress() # also update estimated end time when paused
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
        self.get_config('extruder', 'pressure_advance', 'config_pressure_advance', 'float')
        self.get_config('printer', 'max_accel', 'config_acceleration', 'float')

    def format_time(self, seconds):
        seconds = int(seconds)
        days = seconds // 86400
        seconds %= 86400
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        if days:
            return f"{days} days {hours} {'hr' if hours==1 else 'hrs'} {minutes} min"
        if hours:
            return f"{hours} {'hr' if hours==1 else 'hrs'} {minutes} min"
        if minutes:
            return f"{minutes} min"
        return f"{seconds} sec"

    def get_printjob_progress(self, *args):
        if self.print_state in ('printing', 'pausing', 'paused'):
            est_remaining, progress = self.print_stats.get_print_time_prediction()
            if progress is None: # no prediction could be made yet
                self.progress = 0
                self.print_time = ""
                self.print_done_time = ""
            else:
                remaining = timedelta(seconds=est_remaining)
                done = datetime.now() + remaining
                tomorrow = datetime.now() + timedelta(days=1)
                self.progress = progress
                logging.info(f"got printjob progress of {progress}, remaining {remaining.total_seconds()}")
                self.print_time = self.format_time(remaining.total_seconds()) + " remaining"
                if done.day == datetime.now().day:
                    self.print_done_time = done.strftime("%-H:%M")
                elif done.day == tomorrow.day:
                    self.print_done_time = done.strftime("tomorrow %-H:%M")
                else:
                    self.print_done_time = done.strftime("%a %-H:%M")

########################################################################################
# TUNING

    def reset_tuning(self):
        self.send_flow(100)
        self.send_speed(100)
        self.send_z_adjust(0)
        self.send_fan(0)
        self.send_acceleration(self.klipper_config.getsection('printer').getfloat('max_accel', above=0.))
        self.reset_pressure_advance()

    def get_z_adjust(self):
        self.z_adjust = self.gcode_move.homing_position[2]
    def send_z_adjust(self, offset):
        self.z_adjust = offset
        self.reactor.register_async_callback(lambda e: 
            self.gcode.run_script_from_command(f"SET_GCODE_OFFSET Z={offset} MOVE=1 MOVE_SPEED=5"))

    def get_speed(self):
        self.speed = self.gcode_move.speed_factor*60*100 #speed factor also converts from mm/sec to mm/min
    def send_speed(self, val):
        self.speed = val
        val = val/(60.*100.)
        def set_speed(e):
            self.gcode_move.speed = self.gcode_move._get_gcode_speed() * val
            self.gcode_move.speed_factor = val
        self.reactor.register_async_callback(set_speed)

    def get_flow(self):
        self.flow = self.gcode_move.extrude_factor*100
    def send_flow(self, val):
        self.flow = val
        def set_flow(e):
            new_extrude_factor = val/100.
            last_e_pos = self.gcode_move.last_position[3]
            e_value = (last_e_pos - self.gcode_move.base_position[3]) / self.gcode_move.extrude_factor
            self.gcode_move.base_position[3] = last_e_pos - e_value * new_extrude_factor
            self.gcode_move.extrude_factor = new_extrude_factor
        self.reactor.register_async_callback(set_flow)

    def get_fan(self):
        self.fan_speed = self.fan_manager.fan.last_fan_value * 100 / self.fan_manager.fan.max_power
    def send_fan(self, speed):
        self.fan_speed = speed
        self.reactor.register_async_callback(lambda e: self.fan_manager.fan.set_speed_from_command(speed/100))
 
    def get_pressure_advance(self):#gives pressure_advance value of 1. extruder for now
        self.pressure_advance = self.extruders[0].get_status(self.reactor.monotonic())['pressure_advance']
    def send_pressure_advance(self, val):
        self.pressure_advance = val
        def set_pressure_advance(e):
            for extruder in self.extruders:
                extruder._set_pressure_advance(val, extruder.pressure_advance_smooth_time)
        self.reactor.register_async_callback(set_pressure_advance)
    def reset_pressure_advance(self):
        def reset_pressure_advance(e):
            for extruder in self.extruders:
                pa = self.klipper_config.getsection(extruder.name).getfloat('pressure_advance', 0., minval=0.)
                extruder._set_pressure_advance(pa, extruder.pressure_advance_smooth_time)
        self.reactor.register_async_callback(reset_pressure_advance)

    def get_acceleration(self):
        self.acceleration = self.toolhead.max_accel
    def send_acceleration(self, val): # with dynamic acceleration control (M204) this becomes useless (sets limit)
        self.acceleration = val
        self.toolhead.max_accel = val
        self.reactor.register_async_callback(lambda e: self.toolhead._calc_junction_deviation())

# TUNING
########################################################################################

    def get_config(self, section, option, property_name, ty=None):
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

    def write_config(self, section, option, value):
        logging.info(f"trying to write config section: {section} option: {option}, value: {value}")
        def write_conf(e):
            self.klipper_config_manager.set(section, option, value)
            self.klipper_config_manager.cmd_SAVE_CONFIG(None)
        self.reactor.register_async_callback(write_conf)

    def write_pressure_advance(self, val):
        for i in range(self.extruder_count):
            self.write_config(f"extruder{'' if i==0 else i}", "pressure_advance", val)

    def get_temp(self, dt=None):
        # schedule reading temp in klipper thread which schedules displaying the read value in kgui thread
        def read_temp(e):
            if self.heater_manager is not None:
                t = {}
                for tool_id, sensor in self.heater_manager.gcode_id_to_sensor.items():
                    current, target = sensor.get_temp(self.reactor.monotonic())
                    self.temp[tool_id] = [target, current]
        self.reactor.register_async_callback(read_temp)

    def send_temp(self, temp, tool_id):
        def change_temp(e):
            self.heaters[tool_id].set_temp(temp)
            self.temp[tool_id][0] = temp
        self.reactor.register_async_callback(change_temp)

    def get_homing_state(self):
        homed_axes_string = self.toolhead.kin.get_status(self.reactor.monotonic())['homed_axes']
        for axis in self.homed.keys():
            self.homed[axis] = axis in homed_axes_string

    def send_home(self, axis):
        self.reactor.register_async_callback(lambda e: self.gcode.run_script_from_command("G28" + axis.upper()))

    def send_motors_off(self):
        self.reactor.register_async_callback(lambda e: self.gcode.run_script_from_command("M18"))

    def get_toolhead_busy(self, e): # run in klippy thread
        print_time, est_print_time, lookahead_empty = self.toolhead.check_busy(e)
        idle_time = est_print_time - print_time
        return bool(not lookahead_empty or idle_time <= 0)

    def get_pos(self):
        def set_pos(pos, busy):
            self.pos = pos
            self.toolhead_busy = busy
        def read_pos(e):
            pos = self.toolhead.get_position()
            busy = self.get_toolhead_busy(e)
            Clock.schedule_once(lambda dt: set_pos(pos, busy))

        self.reactor.register_async_callback(read_pos)

    def send_pos(self, x=None, y=None, z=None, e=None, speed=15):  
        def set_pos(e):
            new_pos = [x,y,z,e]
            homed_axes = self.toolhead.get_status(self.reactor.monotonic())['homed_axes']
            # check whether axes are still homed
            new_pos = [new if name in homed_axes else None for new, name in zip(new_pos, 'xyze')]
            new_pos = self._fill_coord(new_pos)
            self.toolhead.move(new_pos, speed)
        self.reactor.register_async_callback(set_pos)

    # def send_rel_pos(self, x=0, y=0, z=0, e=0, speed=15): # only execute this in klipper thread  
    #     cur_pos = self.toolhead.get_position()
    #     new_pos = [x,y,z,e]
    #     homed_axes = self.toolhead.get_status(self.reactor.monotonic())['homed_axes']
    #     for i, (new, name) in enumerate(zip(new_pos, "xyze")):
    #         if name == "e":
    #             cur_pos[i] += new
    #         elif name in homed_axes:
    #             cur_pos[i] += new
    #             if cur_pos[i] > self.pos_max[name]: # don't exceed physical limits
    #                 cur_pos[i] = self.pos_max[name]
    #             if cur_pos[i] < self.pos_min[name]:
    #                 cur_pos[i] = self.pos_min[name]
    #     self.toolhead.move(cur_pos, speed)

    def _fill_coord(self, new_pos):
        """ Fill in any None entries in 'new_pos' with current toolhead position """
        pos = list(self.toolhead.get_position())
        for i, new in enumerate(new_pos):
            if new is not None:
                pos[i] = new
        return pos

    def send_z_go(self, up=True):
        def note_z_abort(dt):
            self.z_move_completion = None
        def start_z(e):
            if self.get_toolhead_busy(e):
                Clock.schedule_once(note_z_abort)
            else:
                pos = self.toolhead.get_position()
                if self.homed['z']:
                    pos[2] = (self.pos_max['z'] if up else self.pos_min['z'])
                else:
                    pos[2] += (self.pos_max['z'] - self.pos_min['z']) * (1 if up else -1)

                self.toolhead.flush_step_generation()
                kin = self.toolhead.get_kinematics()
                steppers = kin.get_steppers()

                for s in steppers:
                    s.set_tag_position(s.get_commanded_position())

                self.z_start_mcu_pos = [(s, s.get_mcu_position()) for s in steppers]
                self.toolhead.dwell(0.050)
                self.toolhead.drip_move(pos, self.z_speed, self.z_move_completion, force=True)

        if not (self.homed['z'] or self.warned_not_homed['z']):
            self.notify.show("Axis not homed", "Proceed with care!", level="warning", delay=3)
            self.warned_not_homed['z'] = True
        self.toolhead_busy = True
        self.z_move_completion = ReactorCompletion(self.reactor)
        self.reactor.register_async_callback(start_z)

    def send_z_stop(self):
        def note_stop_z(dt):
            self.get_pos()
            self.z_move_completion = None
        def stop_z(e):
            # this works similar to homing.py
            self.z_move_completion.complete(True)
            self.reactor.pause(self.reactor.monotonic() + 0.200)
            #self.reactor.pause(self.reactor.NOW)
            self.toolhead.flush_step_generation()
            #                   v--start_pos     v--end_pos
            end_mcu_pos = [(s, spos, s.get_mcu_position()) for s, spos in self.z_start_mcu_pos]
            for s, spos, epos in end_mcu_pos:
                md = (epos - spos) * s.get_step_dist()
                s.set_tag_position(s.get_tag_position() + md)
            self.toolhead.set_position(self._fill_coord(self.toolhead.get_kinematics().calc_tag_position()))
            self.get_pos()
            Clock.schedule_once(note_stop_z)

        if self.z_move_completion:
            self.reactor.register_async_callback(stop_z)

    def send_extrude(self, tool_id, direction=1):
        def note_ext_abort(dt):
            self.ext_move_completion = None
        def start_ext(e):
            if self.get_toolhead_busy(e):
                Clock.schedule_once(note_ext_abort)
            else:
                pos = self.toolhead.get_position()
                pos[3] += 49 * direction
                self.toolhead.flush_step_generation()
                self.toolhead.dwell(0.10)
                self.toolhead.drip_move(pos, self.ext_speed, self.ext_move_completion, force=True)

        self.toolhead_busy = True
        self.ext_move_completion = ReactorCompletion(self.reactor)
        self.reactor.register_async_callback(start_ext)

    def send_extrude_stop(self):
        def note_stop_ext(dt): # this needs to be assigned in the ui thread, only after the move is completed
            self.get_pos()
            self.ext_move_completion = None
        def stop_ext(e):
            self.ext_move_completion.complete(True)
            self.reactor.pause(self.reactor.monotonic() + 0.200)
            self.toolhead.flush_step_generation()
            for extruder in self.extruders:
                extruder.sync_stepper(extruder.stepper)
            Clock.schedule_once(note_stop_ext)

        if self.ext_move_completion:
            self.reactor.register_async_callback(stop_ext)

    def send_calibrate(self):
        self.reactor.register_async_callback(lambda e: self.bed_mesh.calibrate.cmd_BED_MESH_CALIBRATE(None))

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
    def restart(self):
        """Quit and restart klipper and GUI"""
        self.reactor.register_async_callback(lambda e: self.printer.request_exit('restart'), 0)
    def firmware_restart(self):
        """Quit and restart klipper and GUI"""
        self.reactor.register_async_callback(lambda e: self.printer.request_exit('firmware_restart'), 0)
    def quit(self):
        """Stop klipper and GUI, returns to tty"""
        self.reactor.register_async_callback(lambda e: self.printer.request_exit("exit"), 0)
    def register_ui_event_handler(self, event_name, event_handler):
        """using lambdaception to register klippy event handlers to run in the UI thread"""
        if self.printer:
            self.printer.register_event_handler(
                event_name, lambda *args, **kwargs: Clock.schedule_once(lambda dt: event_handler(*args, **kwargs), 0))

# Catch KGUI exceptions and display popups
class PopupExceptionHandler(ExceptionHandler):
    def handle_exception(self, exception):
        if not TESTING:
            logging.info("UI-Exception, popup invoked")
            tr = ''.join(traceback.format_tb(exception.__traceback__))
            App.get_running_app().handle_critical_error(tr + "\n\n" + repr(exception))
            logging.exception(exception)
            return ExceptionManager.PASS

########################################################################################
# KLIPPY THREAD v

ExceptionManager.add_handler(PopupExceptionHandler())

# Read custom Kivy config. This needs an absolute path otherwise
# config will only be loaded when working directory is the parent directory
if TESTING:
    Config.read(join(p.kgui_dir, "config_test.ini"))
else:
    Config.read(join(p.kgui_dir, "config.ini"))

# Load kv-files:
# Add parent directory to sys.path so kv-files (kivy/../parser.py) can import from it
site.addsitedir(p.kgui_dir)
# load a custom style.kv with changes to popup and more
Builder.unload_file(join(kivy_data_dir, "style.kv"))
# All files to read (order is important), main.kv is read first, automatically
kv_files = ("style.kv", "overwrites.kv", "elements.kv", "home.kv", "timeline.kv", "files.kv", "settings.kv")
for fname in kv_files:
    Builder.load_file(join(p.kgui_dir, "kv", fname))


# Entry point, order of execution: __init__()  run()  main.kv  on_start()  handle_connect()  handle_ready()
def load_config(config):
    kgui_object = mainApp(config)
    kgui_object.start()
    return kgui_object
