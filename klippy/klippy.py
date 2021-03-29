#!/usr/bin/env python3
# Main code for host side printer firmware
#
# Copyright (C) 2016-2020  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import sys, os, gc, optparse, logging, time, collections, importlib
import util, reactor, queuelogger, msgproto
import gcode, configfile, pins, mcu, toolhead, webhooks
import signal, traceback, site
import multiprocessing
from os.path import join, exists, dirname

message_ready = "Printer is ready"

message_startup = """
Printer is not ready
The klippy host software is attempting to connect.  Please
retry in a few moments.
"""

message_restart = """
Once the underlying issue is corrected, use the "RESTART"
command to reload the config and restart the host software.
Printer is halted
"""

message_protocol_error = """
This type of error is frequently caused by running an older
version of the firmware on the micro-controller (fix by
recompiling and flashing the firmware).
Once the underlying issue is corrected, use the "RESTART"
command to reload the config and restart the host software.
Protocol error connecting to printer
"""

message_mcu_connect_error = """
Once the underlying issue is corrected, use the
"FIRMWARE_RESTART" command to reset the firmware, reload the
config, and restart the host software.
Error configuring printer
"""

message_shutdown = """
Once the underlying issue is corrected, use the
"FIRMWARE_RESTART" command to reset the firmware, reload the
config, and restart the host software.
Printer is shutdown
"""

class Printer:
    config_error = configfile.error
    command_error = gcode.CommandError
    def __init__(self, main_reactor, bglogger, start_args):
        signal.signal(signal.SIGTERM, self._terminate)
        self.bglogger = bglogger
        self.start_args = start_args
        self.reactor = main_reactor
        self.reactor.register_callback(self._connect)
        self.state_message = message_startup
        self.in_shutdown_state = False
        self.run_result = None
        self.objects = collections.OrderedDict()
        self.parallel_objects = {}
        self._pending_event_handlers = {}
        # Init printer components that must be setup prior to config
        for m in [gcode, webhooks]:
            m.add_early_printer_objects(self)
    def get_start_args(self):
        return self.start_args
    def get_reactor(self):
        return self.reactor
    def get_state_message(self):
        if self.state_message == message_ready:
            category = "ready"
        elif self.state_message == message_startup:
            category = "startup"
        elif self.in_shutdown_state:
            category = "shutdown"
        else:
            category = "error"
        return self.state_message, category
    def is_shutdown(self):
        return self.in_shutdown_state
    def _set_state(self, msg):
        if self.state_message in (message_ready, message_startup):
            self.state_message = msg
        if (msg != message_ready
            and self.start_args.get('debuginput') is not None):
            self.request_exit('error_exit')
    def add_object(self, name, obj):
        if obj in self.objects:
            raise self.config_error(
                "Printer object '%s' already created" % (name,))
        self.objects[name] = obj
    def lookup_object(self, name, default=configfile.sentinel):
        if name in self.objects:
            return self.objects[name]
        if default is configfile.sentinel:
            raise self.config_error("Unknown config object '%s'" % (name,))
        return default
    def lookup_objects(self, module=None):
        if module is None:
            return list(self.objects.items())
        prefix = module + ' '
        objs = [(n, self.objects[n])
                for n in self.objects if n.startswith(prefix)]
        if module in self.objects:
            return [(module, self.objects[module])] + objs
        return objs
    def load_object(self, config, section, default=configfile.sentinel):
        if section in self.objects:
            return self.objects[section]
        module_parts = section.split()
        module_name = module_parts[0]
        init_func = 'load_config_prefix' if len(module_parts) > 1 else 'load_config' 
        module           = join(dirname(__file__), 'extras', module_name + '.py')
        package          = join(dirname(__file__), 'extras', module_name, '__init__.py')
        parallel_module  = join(dirname(__file__), 'parallel_extras', module_name + '.py')
        parallel_package = join(dirname(__file__), 'parallel_extras', module_name, '__init__.py')
        if exists(module) or exists(package):
            mod = importlib.import_module('extras.' + module_name)
            init_func = getattr(mod, init_func, None)
            if init_func is None:
                if default is not configfile.sentinel:
                    return default
                raise self.config_error("Unable to load module '%s'" % (section,))
            self.objects[section] = init_func(config.getsection(section))
            return self.objects[section]
        elif exists(parallel_module) or exists(parallel_package):
            def start_process(module_name, init_func, object_config, default):
                # avoid active imports changing environment - import in target process
                mod = importlib.import_module('parallel_extras.' + module_name)
                init_func = getattr(mod, init_func, None)
                if init_func is None:
                    if default is not configfile.sentinel:
                        return default
                    return -1
                object_config.reactor.root = init_func(object_config)
                object_config.reactor.run()
            # add module directory to path, so objects can be imported when unpickled
            # USE GLOBALLY UNIQUE MODULE NAMES RESPECTIVELY
            if exists(parallel_module):
                site.addsitedir(dirname(parallel_module))
            else:
                site.addsitedir(dirname(parallel_package))
            object_config = config.getsection(section)
            object_config.reactor = reactor.Reactor(False, process=section)
            object_config.reactor._setup_async_callbacks()
            object_config.reactor.register_mp_queues(
                {'printer': self.reactor._mp_queue}, 
                {'printer': self.reactor._pipe_fds[1]})
            self.reactor.register_mp_queues(
                {section: object_config.reactor._mp_queue}, 
                {section: object_config.reactor._pipe_fds[1]})
            self.parallel_objects[section] = multiprocessing.Process(
                target=start_process, 
                args=(module_name, init_func, object_config, default))
            self.parallel_objects[section].start()
            return self.parallel_objects[section]
        else:
            if default is not configfile.sentinel:
                return default
            raise self.config_error("Unable to load module '%s'" % (section,))

    def _read_config(self):
        self.objects['configfile'] = pconfig = configfile.PrinterConfig(self)
        config = pconfig.read_main_config()
        if self.bglogger is not None:
            pconfig.log_config(config)
        # Create printer components
        for m in [pins, mcu]:
            m.add_printer_objects(config)
        for section_config in config.get_prefix_sections(''):
            self.load_object(config, section_config.get_name(), None)
        for m in [toolhead]:
            m.add_printer_objects(config)
        #self.reactor.broadcast_mp_queues()
        # Validate that there are no undefined parameters in the config file
        # pconfig.check_unused_options(config)
    def _connect(self, eventtime):
        try:
            self._read_config()
            self.send_event("klippy:mcu_identify")
            self._pending_event_handlers = {}
            for cb in self.reactor.event_handlers.get("klippy:connect", []):
                if self.state_message is not message_startup:
                    return
                cb()
            # run event handlers in all processes, wait for completion
            for process in self.reactor._mp_queues.keys():
                self._pending_event_handlers[process] = True
                self.reactor.cb(send_event_and_wait, "klippy:connect", process=process)
            while 1:
                pending = False
                for pending_process in self._pending_event_handlers.values():
                    pending = pending or pending_process
                if not pending:
                    break
                self.reactor.pause(0.01)
        except (self.config_error, pins.error) as e:
            logging.exception("Config error")
            self.send_event("klippy:critical_error", "Config error")
            self._set_state("%s%s" % (str(e), message_restart))
            return
        except msgproto.error as e:
            logging.exception("Protocol error")
            self.send_event("klippy:critical_error", "Protocol error")
            self._set_state("%s%s" % (str(e), message_protocol_error))
            util.dump_mcu_build()
            return
        except mcu.error as e:
            logging.exception("MCU error during connect")
            self.send_event("klippy:critical_error", "MCU error during connect")
            self._set_state("%s%s" % (str(e), message_mcu_connect_error))
            util.dump_mcu_build()
            return
        except Exception as e:
            logging.exception("Unhandled exception during connect")
            self.send_event("klippy:critical_error", "Unhandled exception during connect")
            self._set_state("Internal error during connect: %s\n%s" % (
                str(e), message_restart,))
            return
        try:
            self._set_state(message_ready)
            for cb in self.reactor.event_handlers.get("klippy:ready", []):
                if self.state_message is not message_ready:
                    return
                cb()
            for process in self.reactor._mp_queues.keys():
                self.reactor.cb(send_event_and_wait, "klippy:ready", process=process)
        except Exception as e:
            logging.exception("Unhandled exception during ready callback")
            self.invoke_shutdown("Internal error during ready callback: %s"
                                 % (str(e),))
    def run(self):
        systime = time.time()
        monotime = self.reactor.monotonic()
        logging.info("Start printer at %s (%.1f %.1f)",
                     time.asctime(time.localtime(systime)), systime, monotime)
        # Enter main reactor loop
        try:
            self.reactor.run()
        except Exception as e:
            msg = ''.join(traceback.format_tb(e.__traceback__)) + "\n\n" + repr(e)
            logging.exception(msg)
            # Exception from a reactor callback - try to shutdown
            try:
                self.reactor.register_callback((lambda e:
                                                self.invoke_shutdown(msg)))
                self.reactor.run()
            except:
                logging.exception("Repeat unhandled exception during run")
                # Another exception - try to exit
                self.run_result = "error_exit"
        # Check restart flags
        run_result = self.run_result
        try:
            if run_result == 'firmware_restart':
                for n, m in self.lookup_objects(module='mcu'):
                    m.microcontroller_restart()
            self.send_event("klippy:disconnect")
        except:
            logging.exception("Unhandled exception during post run")
        return run_result
    def set_rollover_info(self, name, info, log=True):
        if log:
            logging.info(info)
        if self.bglogger is not None:
            self.bglogger.set_rollover_info(name, info)
    def invoke_shutdown(self, msg): # shut down all work, but dont exit
        if self.in_shutdown_state:
            return
        logging.error("Transition to shutdown state: %s", msg)
        self.in_shutdown_state = True
        self._set_state("%s%s" % (msg, message_shutdown))
        self.send_event("klippy:critical_error", msg)
        for cb in self.reactor.event_handlers.get("klippy:shutdown", []):
            try:
                cb()
            except:
                logging.exception("Exception during shutdown handler")
        logging.info("Reactor garbage collection: %s",
                     self.reactor.get_gc_stats())
    def invoke_async_shutdown(self, msg):
        self.reactor.register_async_callback(
            (lambda e: self.invoke_shutdown(msg)))

    def register_event_handler(self, event, callback):
        self.reactor.register_event_handler(event, callback)
    def send_event(self, event, *params):
        self.reactor.send_event(event, *params)
    def request_exit(self, result):
        if self.run_result is None:
            self.run_result = result
        self.reactor.end()
    def _terminate(self, signalnum, frame):
        """Called on SIGTERM"""
        logging.info("Received SIGTERM, shutting down...")
        self.request_exit("terminated")

def send_event_and_wait(e, root, event):
    for cb in root.reactor.event_handlers.get(event, []):
        cb()
    root.reactor.cb(note_event_handlers_done, root.reactor.process_name, process='printer')
def note_event_handlers_done(e, printer, done_process):
    printer._pending_event_handlers[done_process] = False

######################################################################
# Startup
######################################################################

def arg_dictionary(option, opt_str, value, parser):
    key, fname = "dictionary", value
    if '=' in value:
        mcu_name, fname = value.split('=', 1)
        key = "dictionary_" + mcu_name
    if parser.values.dictionary is None:
        parser.values.dictionary = {}
    parser.values.dictionary[key] = fname

def main():
    usage = "%prog [options] <config file>"
    opts = optparse.OptionParser(usage)
    opts.add_option("-i", "--debuginput", dest="debuginput",
                    help="read commands from file instead of from tty port")
    opts.add_option("-I", "--input-tty", dest="inputtty",
                    default='/tmp/printer',
                    help="input tty name (default is /tmp/printer)")
    opts.add_option("-a", "--api-server", dest="apiserver",
                    help="api server unix domain socket filename")
    opts.add_option("-l", "--logfile", dest="logfile",
                    help="write log to file instead of stderr")
    opts.add_option("-v", action="store_true", dest="verbose",
                    help="enable debug messages")
    opts.add_option("-o", "--debugoutput", dest="debugoutput",
                    help="write output to file instead of to serial port")
    opts.add_option("-d", "--dictionary", dest="dictionary", type="string",
                    action="callback", callback=arg_dictionary,
                    help="file to read for mcu protocol dictionary")
    options, args = opts.parse_args()
    if len(args) != 1:
        opts.error("Incorrect number of arguments")
    start_args = {'config_file': args[0], 'apiserver': options.apiserver,
                  'start_reason': 'startup'}

    debuglevel = logging.INFO
    if options.verbose:
        debuglevel = logging.DEBUG
    if options.debuginput:
        start_args['debuginput'] = options.debuginput
        debuginput = open(options.debuginput, 'rb')
        start_args['gcode_fd'] = debuginput.fileno()
    else:
        start_args['gcode_fd'] = util.create_pty(options.inputtty)
    if options.debugoutput:
        start_args['debugoutput'] = options.debugoutput
        start_args.update(options.dictionary)
    bglogger = None
    if options.logfile:
        start_args['log_file'] = options.logfile
        bglogger = queuelogger.setup_bg_logging(options.logfile, debuglevel)
    else:
        logging.basicConfig(level=debuglevel)
    logging.info("Starting Klippy...")
    start_args['software_version'] = util.get_git_version()
    start_args['cpu_info'] = util.get_cpu_info()
    if bglogger is not None:
        versions = "\n".join([
            "Args: %s" % (sys.argv,),
            "Git version: %s" % (repr(start_args['software_version']),),
            "CPU: %s" % (start_args['cpu_info'],),
            "Python: %s" % (repr(sys.version),)])
        logging.info(versions)
    elif not options.debugoutput:
        logging.warning("No log file specified!"
                        " Severe timing issues may result!")
    gc.disable()

    # Start Printer() class
    while 1:
        if bglogger is not None:
            bglogger.clear_rollover_info()
            bglogger.set_rollover_info('versions', versions)
        gc.collect()
        main_reactor = reactor.Reactor(gc_checking=True)
        printer = Printer(main_reactor, bglogger, start_args)
        main_reactor.root = printer
        res = printer.run()
        if res in ['exit', 'error_exit', 'terminated']:
            break
        time.sleep(1.)
        for process in printer.parallel_objects.values():
            process.join()
            logging.info(f"successfully joined process")
        main_reactor.finalize()
        main_reactor = printer = None
        logging.info("Restarting printer")
        start_args['start_reason'] = res
    if bglogger is not None:
        bglogger.stop()

    if res == 'error_exit':
        sys.exit(-1)


if __name__ == '__main__':
    main()
