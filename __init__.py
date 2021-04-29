import logging
import site
import threading
import os, time
import traceback
import queue
from os.path import join, dirname
from subprocess import Popen
from kivy.config import Config

# Read custom Kivy config. This needs an absolute path otherwise
# config will only be loaded when working directory is the parent directory
TESTING = "KGUI_TESTING" in os.environ

if TESTING:
    Config.read(join(dirname(__file__), "config_test.ini"))
else:
    Config.read(join(dirname(__file__), "config.ini"))
    os.environ['KIVY_WINDOW'] = 'sdl2'
    os.environ['KIVY_GL_BACKEND'] = 'sdl2'
    os.environ['KIVY_METRICS_DENSITY'] = str(Config.getint('graphics', 'width')/600)

from kivy import kivy_data_dir
from kivy.app import App
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock
from kivy.config import Config
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

class mainApp(App, threading.Thread):
    # Property for controlling the state as shown in the statusbar
    state = OptionProperty("startup", options=[
        # Every string set has to be in this list
        "startup",
        "ready",
        "error",
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
    homed = DictProperty() # updated by handle_home_end/start event handler
    temp = DictProperty() # {'heater_bed': [setpoint, current], 'extruder': ...}
    connected = BooleanProperty(False) # updated with handle_connect
    jobs = ListProperty()
    history = ListProperty()
    print_title = StringProperty()
    print_time = StringProperty() # updated by get_printjob_progress
    print_done_time = StringProperty()
    progress = NumericProperty(0)
    pos = ListProperty([0, 0, 0, 0])
    toolhead_busy = BooleanProperty(False)
    ui_toolhead_busy = BooleanProperty(False)
    material = DictProperty()
    tbc_to_guid = DictProperty()
    # tuning
    speed = NumericProperty(100)
    flow = NumericProperty(100)
    fan_speed = NumericProperty(0)
    z_offset = NumericProperty(0)
    acceleration = NumericProperty(0)
    pressure_advance = NumericProperty(0)
    # config
    config_pressure_advance = NumericProperty(0)
    config_acceleration = NumericProperty(0)

    def __init__(self, config, **kwargs):
        logging.info("Kivy app initializing...")
        self.network_manager = NetworkManager()
        self.notify = Notifications()
        self.gcode_metadata = gcode_metadata.load_config(config) # beware this is not the 'right' config
        self.temp = {'extruder': [0,0], 'extruder1': [0,0], 'heater_bed': [0,0]}
        self.homed = {'x': False, 'y': False, 'z': False}
        self.warned_not_homed = {'x': False, 'y': False, 'z': False}
        self.curaconnection = None
        self.kv_file = join(p.kgui_dir, "kv/main.kv") # tell kivy where the root kv file is

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
        # read config
        self.config_pressure_advance = config.getsection('extruder').getfloat("pressure_advance", 0)
        self.config_acceleration = config.getsection('printer').getfloat("max_accel", 0)
        self.invert_z_controls = config.getboolean('invert_z_controls', False)
        self.xy_homing_controls = config.getboolean('xy_homing_controls', True)
        stepper_config = {'x': config.getsection('stepper_x'),
                          'y': config.getsection('stepper_y'),
                          'z': config.getsection('stepper_z')}
        self.pos_max = {i: stepper_config[i].getfloat('position_max', 200) for i in 'xyz'}
        self.pos_min = {i: stepper_config[i].getfloat('position_min', 0) for i in 'xyz'}
        # maintain this by keeping default the same as klipper
        self.min_extrude_temp = config.getsection("extruder").getfloat("min_extrude_temp", 170)
        # count how many extruders exist
        for i in range(1, 10):
            if not config.has_section(f"extruder{i}"):
                self.extruder_count = i
                break
        # register event handlers
        self.reactor.register_event_handler("klippy:connect", self.handle_connect) # printer_objects available
        self.reactor.register_event_handler("klippy:ready", self.handle_ready) # connect handlers have run
        self.reactor.register_event_handler("klippy:disconnect", self.handle_disconnect)
        self.reactor.register_event_handler("klippy:shutdown", self.handle_shutdown)
        self.reactor.register_event_handler("klippy:critical_error", self.handle_critical_error)
        self.reactor.register_event_handler("klippy:error", self.handle_error)
        self.reactor.register_event_handler("homing:home_rails_end", self.handle_home_end)
        self.reactor.register_event_handler("virtual_sdcard:printjob_start", self.handle_printjob_start)
        self.reactor.register_event_handler("virtual_sdcard:printjob_end", self.handle_printjob_end)
        self.reactor.register_event_handler("virtual_sdcard:printjob_change", self.handle_printjob_change)
        self.reactor.register_event_handler("virtual_sdcard:printjob_added", self.handle_printjob_added)
        self.reactor.register_event_handler("print_history:change", self.handle_history_change)
        self.reactor.register_event_handler("filament_manager:material_changed", self.handle_material_change)
        self.reactor.cb(printer_cmd.load_object, "live_move")
        self.reactor.cb(printer_cmd.load_object, "filament_manager")
        self.reactor.cb(printer_cmd.load_object, "print_history")
        self.clean()
        super().__init__(**kwargs)

    def clean(self):
        ndel, freed = freedir(p.sdcard_path)
        if ndel:
            self.notify.show("Disk space freed", f"Deleted {ndel} files, freeing {freed} MiB")
            self.reactor.cb(self.trim_history, process='printer')

    @staticmethod
    def trim_history(e, printer):
        printer.objects['print_history'].trim_history()

    def handle_connect(self):
        self.connected = True
        self.reactor.cb(printer_cmd.update)
        self.reactor.cb(printer_cmd.get_tbc)
        self.bind(print_state=self.handle_material_change)
        Clock.schedule_interval(lambda dt: self.reactor.cb(printer_cmd.update), 1)

        # Check reactor latency during development
        self.avg_count = 0
        self.avg = 0
        self.avg_2 = 0
        Clock.schedule_interval(self.init_latency, 0.94)
    def init_latency(self, dt):
        self.start = self.reactor.monotonic()
        self.reactor.cb(self.latency, process='printer')
    @staticmethod
    def latency(e, printer):
        half_time = printer.reactor.monotonic()
        printer.reactor.cb(mainApp.return_latency, half_time, process='kgui')
    @staticmethod
    def return_latency(e, kgui, half_time):
        if kgui.start is None:
            return logging.info("\n    big oof \n")
        l1 = half_time - kgui.start
        l2 = kgui.reactor.monotonic() - half_time
        kgui.avg_count +=1
        kgui.avg = kgui.avg*(kgui.avg_count -1)/kgui.avg_count + l1*1/kgui.avg_count
        kgui.avg_2 = kgui.avg_2*(kgui.avg_count -1)/kgui.avg_count + l2*1/kgui.avg_count
        logging.info(f"kivy->klipper  {l1:6.5f}, {kgui.avg}  klipper->kivy  {l2:6.5f}, {kgui.avg_2}  at {int(kgui.reactor.monotonic())}")
        kgui.start = None

    def handle_ready(self):
        self.state = "ready"
        self.reactor.cb(printer_cmd.get_material, process='printer')

    # is called when system shuts down all work, either
    # to halt so the user can see what he did wrong
    # or to fully exit afterwards
    def handle_shutdown(self):
        pass

    # is called when system disconnects from mcu, this is only done at
    # the very end, when exiting or restarting
    def handle_disconnect(self):
        logging.info("Kivy app.handle_disconnect")
        self.connected = False
        self.reactor.cb(self.reactor.close_process, process='kgui')
        self.stop()

    def handle_critical_error(self, message):
        self.state = "error"
        CriticalErrorPopup(message = message).open()

    def handle_error(self, message):
        ErrorPopup(message = message).open()

    def handle_home_end(self, homing_state, rails):
        self.ui_toolhead_busy = False
        for rail in rails:
            self.homed[rail.steppers[0].get_name(short=True)] = True
        self.reactor.cb(printer_cmd.wait_toolhead_not_busy)

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
        # this only works if we are in a printing state
        # we rely on this being called after handle_printjob_change
        self.reactor.cb(printer_cmd.get_printjob_progress, process='printer')

    def handle_printjob_end(self, job):
        if 'done' == job.state:
            self.progress = 1
            self.print_done_time = ""
            self.print_time = "done"
            # show finished job for 1h
            Clock.schedule_once(lambda dt: self.hide_printjob(job.name), 3600)
        else:
            self.hide_printjob(job.name)

    def hide_printjob(self, name):
        if not self.jobs and self.print_title == name:
            self.print_title = ""
            self.print_done_time = ""
            self.print_time = ""
            self.progress = 0
            self.print_state = "no printjob"
            # tuning values are only reset once print_queue has run out
            self.reactor.cb(printer_cmd.reset_tuning)

    def handle_history_change(self, history):
        self.history = history

    def handle_material_change(self, *args):
        self.reactor.cb(printer_cmd.get_material, process='printer')

    def note_live_move(self, axis):
        if axis in 'xyz' and not (self.homed[axis] or self.warned_not_homed[axis]):
            self.notify.show("Axis not homed", "Proceed with care!", level="warning", delay=3)
            self.warned_not_homed['z'] = True
        self.ui_toolhead_busy = True
        self.toolhead_busy = True

    def note_live_move_end(self, axis=None):
        self.ui_toolhead_busy = False
        self.reactor.cb(printer_cmd.wait_toolhead_not_busy)

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

    def poweroff(self):
        Popen(['sudo','systemctl', 'poweroff'])
    def reboot(self):
        Popen(['sudo','systemctl', 'reboot'])

def kivy_callback(reactor, callback, waketime, *args, **kwargs):
    Clock.schedule_del_safe(lambda: callback(reactor.monotonic(), *args, **kwargs))

# Catch KGUI exceptions and display popups
class PopupExceptionHandler(ExceptionHandler):
    def handle_exception(self, exception):
        if not TESTING:
            logging.info("UI-Exception, popup invoked")
            tr = ''.join(traceback.format_tb(exception.__traceback__))
            App.get_running_app().handle_critical_error(tr + "\n\n" + repr(exception))
            logging.exception(exception)
            return ExceptionManager.PASS

ExceptionManager.add_handler(PopupExceptionHandler())

# Load kv-files:
# Add parent directory to sys.path so kv-files (kivy/../parser.py) can import from it
site.addsitedir(p.kgui_dir)
# load a custom style.kv with changes to popup and more
Builder.unload_file(join(kivy_data_dir, "style.kv"))
# All files to read (order is important), main.kv is read first, automatically
for fname in ("style.kv", "overwrites.kv", "elements.kv", "home.kv", "timeline.kv", "files.kv", "settings.kv"):
    Builder.load_file(join(p.kgui_dir, "kv", fname))


# Entry point, order of execution: __init__()  run()  main.kv  on_start()  handle_connect()  handle_ready()
def load_config(config):
    kgui_object = mainApp(config)
    logging.info("Kivy app.run")
    kgui_object.start()
    return kgui_object
