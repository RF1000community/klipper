from asyncore import write
import logging
import site
import threading
import os
import traceback
from os.path import join, dirname
from subprocess import Popen

os.environ['KIVY_NO_CONSOLELOG'] = '1'  # Only use file logging

from kivy.config import Config

TESTING = "KGUI_TESTING" in os.environ

# Read custom Kivy config. This needs an absolute path otherwise
# config will only be loaded when working directory is the parent directory
if TESTING:
    Config.read(join(dirname(__file__), "config_test.ini"))
else:
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'sdl2'
    os.environ['KIVY_METRICS_DENSITY'] = str(Config.getint('graphics', 'width')/600)

from kivy import kivy_data_dir
from kivy.app import App
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import (OptionProperty, BooleanProperty, DictProperty,
                            NumericProperty, ListProperty, StringProperty)
from .elements import UltraKeyboard, CriticalErrorPopup, ErrorPopup
from .freedir import freedir
from .nm_dbus import NetworkManager
from .status import Notifications
from . import parameters as p
# Imports for KvLang Builder
from . import files, home, settings, status, timeline, update, printer_cmd

site.addsitedir(join(p.klipper_dir, "klippy/extras/")) # gcode_metadata
import gcode_metadata

class MainApp(App, threading.Thread):
    # Property for controlling the state as shown in the statusbar
    state = OptionProperty("startup", options=[
        # Every string set has to be in this list
        "startup",
        "ready",
        "error",
        ])
    # This is more of a UI-state, it may be 'finished' even though virtual_sdcard has no print jobs
    print_state = OptionProperty("no print job", options=[
        "no print job",
        "queued",
        "printing",
        "pausing",
        "paused",
        "aborting",
        "aborted",
        "finished",
        ])
    homed = DictProperty() # Updated by handle_home_end/start event handler
    temp = DictProperty() # {'heater_bed': [setpoint, current], 'extruder': ...}
    connected = BooleanProperty(False) # updated with handle_connect
    jobs = ListProperty()
    history = ListProperty()
    print_title = StringProperty()
    print_time = StringProperty()
    print_done_time = StringProperty()
    progress = NumericProperty(0)
    pos = ListProperty([0, 0, 0, 0])
    toolhead_busy = BooleanProperty(False)
    material = DictProperty()
    tbc_to_guid = DictProperty()
    cura_connected = BooleanProperty(False)
    thumbnail = StringProperty(p.kgui_dir + '/logos/transparent.png')
    led_brightness = NumericProperty()
    # Tuning
    speed = NumericProperty(100)
    flow = NumericProperty(100)
    fan_speed = NumericProperty(0)
    z_offset = NumericProperty(0)
    acceleration = NumericProperty(0)
    pressure_advance = NumericProperty(0)
    # Config
    config_pressure_advance = NumericProperty(0)
    config_acceleration = NumericProperty(0)
    continuous_printing = BooleanProperty(False)
    reposition = BooleanProperty(False)
    condition = StringProperty("")

    def __init__(self, config, **kwargs):
        logging.info("Kivy app initializing...")
        self.network_manager = NetworkManager()
        self.notify = Notifications()
        self.gcode_metadata = gcode_metadata.load_config(config) # Beware this is not the 'right' config
        self.temp = {'extruder': [0,0], 'extruder1': [0,0], 'heater_bed': [0,0]}
        self.homed = {'x': False, 'y': False, 'z': False}
        self.warned_not_homed = {'x': False, 'y': False, 'z': False}
        self.kv_file = join(p.kgui_dir, "kv/main.kv") # Tell kivy where the root kv file is

        if TESTING:
            self.pos_max = {'x': 200, 'y': 0}
            self.pos_min = {'x': 0, 'y': 0}
            self.xy_homing_controls = True
            self.extruder_count = 2
            self.reactor = None
            return super().__init__(**kwargs)

        self.reactor = config.get_reactor()
        self.reactor.register_mp_callback_handler(kivy_callback)
        self.fd = config.get_printer().get_start_args().get("gcode_fd")
        # Read config
        self.config_pressure_advance = config.getsection('extruder').getfloat("pressure_advance", 0)
        self.config_acceleration = config.getsection('printer').getfloat("max_accel", 0)
        self.invert_z_controls = config.getboolean('invert_z_controls', False)
        self.xy_homing_controls = config.getboolean('xy_homing_controls', True)
        self.led_controls = config.get('led_controls', None)
        self.led_update_time = 0
        if self.led_controls:
            self.led_brightness = config.getsection(f'output_pin {self.led_controls}').getfloat('value')
        stepper_config = {'x': config.getsection('stepper_x'),
                          'y': config.getsection('stepper_y'),
                          'z': config.getsection('stepper_z')}
        self.pos_max = {i: stepper_config[i].getfloat('position_max', 200) for i in 'xyz'}
        self.pos_min = {i: stepper_config[i].getfloat('position_min', 0) for i in 'xyz'}
        # Maintain this by keeping default the same as klipper
        self.min_extrude_temp = config.getsection("extruder").getfloat("min_extrude_temp", 170)
        # Count how many extruders exist
        for i in range(1, 10):
            if not config.has_section(f"extruder{i}"):
                self.extruder_count = i
                break
        # These are loaded a bit late
        self.reactor.cb(printer_cmd.load_object, "live_move")
        self.reactor.cb(printer_cmd.load_object, "filament_manager")
        self.reactor.cb(printer_cmd.load_object, "print_history")
        super().__init__(**kwargs)
        self.reactor.cb(printer_cmd.request_event_history)

    def clean(self):
        ndel, freed = freedir(p.sdcard_path)
        if ndel:
            self.notify.show("Disk space freed", f"Deleted {ndel} files, freeing {freed} MiB")
            self.reactor.cb(printer_cmd.trim_history, process='printer')

    def handle_connect(self):
        self.connected = True
        self.clean() # print_history should exist at this point since it is created from a callback in init

    def handle_ready(self):
        self.state = "ready"
        self.reactor.cb(printer_cmd.update)
        self.reactor.cb(printer_cmd.get_material)
        self.reactor.cb(printer_cmd.get_tbc)
        self.reactor.cb(printer_cmd.get_collision_config)
        self.bind(print_state=self.handle_material_change)
        Clock.schedule_interval(lambda dt: self.reactor.cb(printer_cmd.update), 1)
        logging.info("Kivy app running")

    def handle_shutdown(self):
        """
        Is called when system shuts down all work, either
        to halt so the user can see what he did wrong
        or to fully exit afterwards
        """
        pass

    def handle_disconnect(self):
        """
        Is called when system disconnects from mcu, this is only done at
        the very end, when exiting or restarting
        """
        logging.info("Kivy app.handle_disconnect")
        self.connected = False
        self.reactor.register_async_callback(self.reactor.end)
        self.stop()

    def handle_critical_error(self, message):
        self.state = "error"
        CriticalErrorPopup(message = message).open()

    def handle_error(self, message):
        ErrorPopup(message = message).open()

    def handle_home_end(self, homing_state, rails):
        self.toolhead_busy = False
        for rail in rails:
            self.homed[rail.steppers[0].get_name(short=True)] = True

    def handle_print_change(self, jobs):
        """
        Update the configuration of print jobs and the state of 1. print job
        If there is no print job, the 'finished' state is retained until hide_print is executed
        """
        if len(jobs):
            self.print_state = jobs[0].state
        self.jobs = jobs

    def handle_print_added(self, jobs, job):
        self.handle_print_change(jobs)
        if len(self.jobs) > 1:
            self.notify.show("Added Print Job", f"Added {job.name} to print Queue", delay=4)

    def handle_print_start(self, jobs, job):
        self.handle_print_change(jobs)
        self.notify.show("Started printing", f"Started printing {job.name}", delay=5)
        self.print_title = job.name
        self.thumbnail = self.gcode_metadata.get_metadata(job.path).get_thumbnail_path()
        # This only works if we are in a printing state
        self.reactor.cb(printer_cmd.get_print_progress)

    def handle_print_end(self, jobs, job):
        self.print_state = job.state # in case the following handle_print_change doesnt update because there is no job
        self.handle_print_change(jobs)
        if job.state in ('finished', 'aborted'):
            self.thumbnail = p.kgui_dir + '/logos/transparent.png'
            self.progress = 0
            self.print_done_time = "Confirm Build Plate is clear"
            self.print_time = ""

    def hide_print(self):
        self.print_title = ""
        self.print_done_time = ""
        self.print_time = ""
        self.progress = 0
        self.print_state = "no print job"
        if not self.jobs:
            # Tuning values are only reset once print_queue has run out
            self.reactor.cb(printer_cmd.reset_tuning)

    def handle_history_change(self, history):
        self.history = history

    def handle_material_change(self, *args):
        self.reactor.cb(printer_cmd.get_material)

    def note_live_move(self, axis):
        if axis in 'xyz' and not (self.homed[axis] or self.warned_not_homed[axis]):
            self.notify.show("Axis not homed", "Proceed with care!", level="warning", delay=3)
            self.warned_not_homed['z'] = True
        self.toolhead_busy = True

    def note_live_move_end(self, axis=None):
        self.toolhead_busy = False

    def set_led_brightness(self, val):
        self.led_brightness = val
        now = self.reactor.monotonic()
        if now > self.led_update_time:
            self.led_update_time = max(self.led_update_time + 0.025, now)
            Clock.schedule_once(self.apply_led_brightness, 0.025)

    def apply_led_brightness(self, dt):
        self.reactor.cb(printer_cmd.run_script, f"SET_PIN PIN={self.led_controls} VALUE={self.led_brightness}")

    def on_start(self, *args):
        if self.network_manager.available:
            self.network_manager.start()
        try:
            self.root_window.set_vkeyboard_class(UltraKeyboard)
        except:
            logging.warning("root_window wasnt available")

    def on_stop(self, *args):
        """Stop networking dbus event loop"""
        self.network_manager.stop()

    def poweroff(self):
        Popen(['sudo','systemctl', 'poweroff'])

    def reboot(self):
        Popen(['sudo','systemctl', 'reboot'])


def run_callback(reactor, callback, waketime, waiting_process, *args, **kwargs):
    res = callback(reactor.monotonic(), reactor.root, *args, **kwargs)
    if waiting_process:
        reactor.cb(reactor.mp_complete, (callback.__name__, waketime, "kgui"), res, process=waiting_process)

def kivy_callback(*args, **kwargs):
    Clock.schedule_del_safe(lambda: run_callback(*args, **kwargs))

# Catch KGUI exceptions and display popups
class PopupExceptionHandler(ExceptionHandler):
    def handle_exception(self, exception):
        if not TESTING:
            tr = ''.join(traceback.format_tb(exception.__traceback__))
            App.get_running_app().handle_critical_error(tr + "\n\n" + repr(exception))
            logging.exception("UI-Exception, popup invoked")
            return ExceptionManager.PASS

ExceptionManager.add_handler(PopupExceptionHandler())

# Load kv-files:
# Add parent directory to sys.path so kv-files (kivy/../parser.py) can import from it
site.addsitedir(p.kgui_dir)
# load a custom style.kv with changes to popup and more
Builder.unload_file(join(kivy_data_dir, "style.kv"))
# All files to read (order is important), main.kv is read first, automatically
for fname in ("style.kv", "overwrites.kv", "elements.kv", "home.kv",
              "timeline.kv", "files.kv", "settings.kv"):
    Builder.load_file(join(p.kgui_dir, "kv", fname))
