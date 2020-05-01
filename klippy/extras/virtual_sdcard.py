# Printjob manager (based on VirtualSDCard) providing API for local printjobs
# with pause-resume, cura-style compressed gcode, and queue functionality 
#
# Copyright (C) 2020  Konstantin Vogel <konstantin.vogel@gmx.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import os, logging
from zipfile import ZipFile


class Printjob:
    def __init__(self, path, production_line_mode, manager):
        self.manager = manager
        self.reactor = manager.reactor
        self.toolhead = manager.toolhead
        self.gcode = manager.gcode
        self.printer = manager.printer
        self.heater_manager = manager.heater_manager
        self.path = path
        self.state = None
        self.production_line_mode = production_line_mode # if True dont pause when starting the next job from q
        self.set_state('queued') # queued -> printing -> pausing -> paused -> printing -> done
        self.file_position = 0 #                    -> stopping -> stopped
        self.saved_pause_state = False
        self.start_stop_times = []
        self.name, ext = os.path.splitext(os.path.basename(path))
        if ext in ('.gco', '.gcode'):
            self.thumbnail_path = None
            try:
                self.file_obj = open(self.path, 'rb')
                self.file_obj.seek(0, os.SEEK_END)
                self.file_size = self.file_obj.tell()
                self.file_obj.seek(0)
            except:
                logging.info("printjob_manager: couldn't open file {}".format(self.path))
                self.set_state('stopped')
                self.manager.check_queue()
        elif ext == '.ufp':
            try:
                zip_obj = ZipFile(path)
                self.thumbnail_path = path.replace('.ufp', '.png')
                with open(self.thumbnail_path, 'wb') as thumbnail:
                    thumbnail.write(zip_obj.read("/Metadata/thumbnail.png"))
                    self.file_obj = zip_obj.open("/3D/model.gcode", 'r')
                    self.file_obj.seek(0, os.SEEK_END)
                    self.file_size = self.file_obj.tell()
                    self.file_obj.seek(0)
            except Exception as e:
                logging.debug("printjob_manager: couldn't open compressed file {}, exception {}".format(self.path, e))
                self.set_state('stopped')

    def set_state(self, state):
        if self.state != state:
            self.state = state
            self.printer.send_event("virtual_sdcard:printjob_change")

    def start(self):
        if self.state == 'queued':
            if self.production_line_mode:
                self.set_state('printing')
                self.start_stop_times.append([self.toolhead.mcu.estimated_print_time(self.reactor.monotonic()), None])
                self.work_timer = self.reactor.register_timer(self.work_handler, self.reactor.NOW)
            else:
                self.set_state('paused')
            self.printer.send_event("virtual_sdcard:printjob_started", self.path, self.state)

    def resume(self):
        if self.state == 'pausing':
            self.set_state('printing')
        elif self.state == 'paused':
            if self.saved_pause_state:
                self.gcode.cmd_RESTORE_GCODE_STATE({'NAME':"PAUSE_STATE", 'MOVE':1})
                self.saved_pause_state = False
            self.set_state('printing')
            self.start_stop_times.append([self.toolhead.mcu.estimated_print_time(self.reactor.monotonic()), None])
            self.work_timer = self.reactor.register_timer(self.work_handler, self.reactor.NOW)

    def pause(self):
        if self.state == 'printing':
            self.set_state('pausing')

    def stop(self):
        if self.state in ('printing', 'pausing'):
            self.set_state('stopping')
            # turn off heaters so stopping doesn't wait for temperature requests
            self.reactor.pause(self.reactor.monotonic() + 0.100)
            self.heater_manager.cmd_TURN_OFF_HEATERS({})
        else: # in case it is paused we need to do all stopping actions here
            self.set_state('stopped')
            self.file_obj.close()
            self.heater_manager.cmd_TURN_OFF_HEATERS({})
            self.manager.check_queue()

    def work_handler(self, eventtime):
        logging.info("Printjob entering work handler (position %d)", self.file_position)
        self.reactor.unregister_timer(self.work_timer)
        try:
            self.file_obj.seek(self.file_position)
        except:
            logging.exception("virtual_sdcard seek")
            self.gcode.respond_error("Unable to seek file")
            self.set_state('stopping')
        gcode_mutex = self.gcode.get_mutex()
        partial_input = ""
        lines = []

        while self.state == 'printing':
            # Read more lines if necessary
            if not lines:
                try:
                    data = self.file_obj.read(8192).decode()
                except:
                    self.set_state('stopping')
                    logging.exception("virtual_sdcard read")
                    self.gcode.respond_error("Error on virtual sdcard read")
                    break
                if not data:
                    # End of file
                    self.set_state('done')
                    self.gcode.respond("Done printing file")
                    break
                lines = data.split('\n')
                lines[0] = partial_input + lines[0]
                partial_input = lines.pop()
                lines.reverse()
                self.reactor.pause(self.reactor.NOW)
                continue
            # Pause if any other request is pending in the gcode class
            if gcode_mutex.test():
                self.reactor.pause(self.reactor.monotonic() + 0.100)
                continue
            # Dispatch command
            try:
                self.gcode.run_script(lines[-1])
            except Exception as e:
                self.printer.send_event("klippy:error", repr(e))
                self.set_state('stopping')
                logging.exception("Virtual sdcard error dispaching command: " + repr(e))
                break
            self.file_position += len(lines.pop()) + 1

        logging.info(f"Exiting SD card print in state {self.state} position {self.file_position}")
        self.start_stop_times[-1][1] = self.toolhead.get_last_move_time()
        # Finish stopping or pausing actions
        if self.state == 'pausing':
            self.set_state('paused')
            self.gcode.cmd_SAVE_GCODE_STATE({'NAME': "PAUSE_STATE"})
            self.saved_pause_state = True
        else:
            if self.state == 'stopping':
                self.set_state('stopped')
            self.file_obj.close()
            self.heater_manager.cmd_TURN_OFF_HEATERS({})
            self.manager.check_queue()
        return self.reactor.NEVER

    def get_printed_time(self, print_time=None):
        # doesnt use get_last_move_time since this can be ran in UI thread
        # also doesnt use print time since it doesnt advance continuously
        if not print_time:
            print_time = self.toolhead.mcu.estimated_print_time(self.reactor.monotonic())
        printed_time = 0
        for time in self.start_stop_times:
            printed_time += - time[0] + (time[1] if time[1] else print_time)
        return printed_time


class PrintjobManager(object):
    def __init__(self, config):
        self.toolhead = None
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.heater_manager = self.printer.lookup_object('heaters')
        self.printer.register_event_handler("klippy:ready", self.handle_ready)
        self.printer.register_event_handler("klippy:shutdown", self.handle_shutdown)
        self.jobs = [] # Printjobs, first is current

    def add_printjob(self, path, paused=True):
        """ add new printjob to queue """
        self.jobs.append(Printjob(path, paused, self))
        self.check_queue()

    def pause_printjob(self):
        self.jobs[0].pause()

    def stop_printjob(self):
        self.jobs[0].stop()

    def resume_printjob(self):
        self.jobs[0].resume()

    def clear_queue(self):
        """ remove everything but the first element wich is currently being printed """
        self.jobs = self.jobs[:1]

    def check_queue(self):
        """ remove 'stopped' or 'done' printjobs from queue, start next if necessary """ 
        if len(self.jobs) and self.jobs[0].state in ('done', 'stopped'):
            last = self.jobs.pop(0)
            self.printer.send_event("virtual_sdcard:printjob_ended", last.path, last.state)
            self.printer.send_event("virtual_sdcard:printjob_change")
        if len(self.jobs) and self.jobs[0].state in ('queued'):
            self.jobs[0].start()

    def get_status(self, eventtime=None):
        return {'printjobs': self.jobs}

    def handle_ready(self):
        self.toolhead = self.printer.lookup_object('toolhead')

    def handle_shutdown(self):
        if len(self.jobs) and self.jobs[0].state == 'printing':
            self.stop_printjob()
            try:
                readpos = max(self.jobs[0].file_position - 1024, 0)
                readcount = self.jobs[0].file_position - readpos
                self.jobs[0].file_obj.seek(readpos)
                data = self.jobs[0].file_obj.read(readcount + 128)
            except:
                logging.exception("virtual_sdcard shutdown read")
                return
            logging.info("Virtual sdcard (%d): %s\nUpcoming (%d): %s",
                         readpos, repr(data[:readcount]),
                         self.jobs[0].file_position, repr(data[readcount:]))

    def stats(self, eventtime):
        if len(self.jobs) and self.jobs[0].state in ('printing', 'pausing', 'stopping'):
            return True, "sd_pos=%d" % (self.jobs[0].file_position,)
        return False, ""


class VirtualSD(PrintjobManager):
    def __init__(self, config):
        super(VirtualSD, self).__init__(config)
        self.selected_file = None # str
        sd_path = config.get('path')
        self.sdcard_dirname = os.path.normpath(os.path.expanduser(sd_path))
        self.gcode.register_command('M21', None)

        for cmd in ['M20', 'M21', 'M23', 'M24', 'M25', 'M26', 'M27']:
            self.gcode.register_command(cmd, getattr(self, 'cmd_' + cmd))
        for cmd in ['M28', 'M29', 'M30']:
            self.gcode.register_command(cmd, self.cmd_error)
    def get_file_list(self):
        dname = self.sdcard_dirname
        try:
            filenames = os.listdir(self.sdcard_dirname)
            return [(fname, os.path.getsize(os.path.join(dname, fname)))
                    for fname in sorted(filenames, key=str.lower)
                    if not fname.startswith('.')
                    and os.path.isfile((os.path.join(dname, fname)))]
        except:
            logging.exception("virtual_sdcard get_file_list")
            raise self.gcode.error("Unable to get file list")
    def is_active(self):
        return len(self.jobs) and self.jobs[0] == 'printing'
    def cmd_error(self, params):
        raise self.gcode.error("SD write not supported")
    def cmd_M20(self, params):
        # List SD card
        files = self.get_file_list()
        self.gcode.respond_raw("Begin file list")
        for fname, fsize in files:
            self.gcode.respond_raw("%s %d" % (fname, fsize))
        self.gcode.respond_raw("End file list")
    def cmd_M21(self, params):
        # Initialize SD card
        self.gcode.respond_raw("SD card ok")
    def cmd_M23(self, params):
        # Select SD file
        # parses filename
        try:
            orig = params['#original']
            filename = orig[orig.find("M23")+4 : max(orig.find(".gco")+4, orig.find(".gcode")+6)].strip()
            if '*' in filename:
                filename = filename[:filename.find('*')].strip()
        except:
            raise self.gcode.error("Unable to extract filename")
        if filename.startswith('/'):
            filename = filename[1:]
        files = self.get_file_list()
        files_by_lower = { fname.lower(): fname for fname, fsize in files }
        filename = files_by_lower[filename.lower()]
        self.selected_file = os.path.join(self.sdcard_dirname, filename)
        self.gcode.respond("File {} selected".format(filename))
    def cmd_M24(self, params):
        # Start/resume SD print
        if self.state == 'paused':
            self.resume_printjob()
        elif self.state != 'printing':
            self.clear_queue()
            self.add_printjob(self.selected_file)
    def cmd_M25(self, params):
        # Pause SD print
        self.pause_printjob()
    def cmd_M26(self, params):
        # Set SD position
        if len(self.jobs):
            if self.jobs[0].state == 'printing':
                raise self.gcode.error("SD busy")
            else:
                pos = self.gcode.get_int('S', params, minval=0)
                self.jobs[0].file_position = pos
    def cmd_M27(self, params):
        # Report SD print status
        if self.state == 'printing':
            self.gcode.respond("SD printing byte %d/%d" % (
            self.jobs[0].file_position, self.file_size))
        else:
            self.gcode.respond("SD print {}".format(self.state))

def load_config(config):
    return VirtualSD(config)
