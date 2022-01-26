# Print job manager providing API for local print jobs
# with pause-resume, cura-style compressed gcode, and queue functionality
#
# Copyright (C) 2020  Konstantin Vogel <konstantin.vogel@gmx.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import os
from uuid import uuid4


class PrintJob:
    def __init__(self, path, manager):
        self.manager = manager
        self.reactor = manager.reactor
        self.toolhead = manager.toolhead
        self.gcode = manager.gcode
        self.heaters = manager.printer.lookup_object('heaters')
        self.gcode_metadata = manager.gcode_metadata

        self.path = path
        self.state = None
        self.set_state('queued') # queued -> printing -> pausing -> paused -> printing -> finished
        self.file_position = 0 #                      -> aborting -> aborted
        self.additional_printed_time = 0 # elapsed print time before the last pause
        self.last_start_time = 0
        self.name, ext = os.path.splitext(os.path.basename(path))
        self.uuid = str(uuid4())

        try:
            self.md = self.gcode_metadata.get_metadata(self.path)
            self.file_obj = self.md.get_gcode_stream()
            self.file_size = self.md.get_file_size()
        except (ValueError, FileNotFoundError) as e:
            self.reactor.send_event("klippy:error", f"Failed opening file {self.path}")
            logging.exception(f"Failed opening {ext} file: {e}")
            self.set_state('aborted')

    def __getstate__(self):
        return {'path': self.path, 'name': self.name, 'state': self.state, 'uuid': self.uuid}

    def set_state(self, state):
        if self.state != state:
            self.state = state
            self.reactor.send_event("virtual_sdcard:print_change", self.manager.jobs)

    def start(self):
        if self.state == 'queued':
            self.last_start_time = self.toolhead.mcu.estimated_print_time(self.reactor.monotonic())
            # set_state only after last_start_time is set but before entering work handler
            self.set_state('printing')
            self.work_timer = self.reactor.register_timer(self.work_handler, self.reactor.NOW)
            self.reactor.send_event("virtual_sdcard:print_start", self.manager.jobs, self)

    def resume(self, gcmd):
        if self.state == 'pausing':
            self.set_state('printing')
            return True
        elif self.state == 'paused':
            if gcmd == None:
                self.gcode.run_script("RESTORE_GCODE_STATE NAME=PAUSE_STATE MOVE=1")
            else:
                self.gcode.run_script_from_command("RESTORE_GCODE_STATE NAME=PAUSE_STATE MOVE=1")
            self.last_start_time = self.toolhead.mcu.estimated_print_time(self.reactor.monotonic())
            self.set_state('printing')
            self.work_timer = self.reactor.register_timer(self.work_handler, self.reactor.NOW)
            return True

    def pause(self):
        if self.state == 'printing':
            self.set_state('pausing')
            return True

    def stop(self):
        if self.state in ('printing', 'pausing'):
            self.set_state('aborting')
            # Turn off heaters so aborting doesn't wait for temperature requests
            self.heaters.cmd_TURN_OFF_HEATERS(None)
            self.reactor.pause(self.reactor.monotonic() + 0.05)
            self.heaters.cmd_TURN_OFF_HEATERS(None)
            return True
        elif self.state == 'paused': # In case it is paused we need to do all aborting actions here
            self.set_state('aborted')
            self.file_obj.close()
            self.heaters.cmd_TURN_OFF_HEATERS(None)
            self.manager.check_queue()
            return True

    def work_handler(self, eventtime):
        logging.info(f"Print job entering work handler (position {self.file_position})")
        self.reactor.unregister_timer(self.work_timer)
        try:
            self.file_obj.seek(self.file_position)
        except:
            logging.exception("virtual_sdcard seek")
            self.gcode.respond_error("Unable to seek file")
            self.set_state('aborting')
        gcode_mutex = self.gcode.get_mutex()
        partial_input = ""
        lines = []

        while self.state == 'printing':
            # Read more lines if necessary
            if not lines:
                try:
                    data = self.file_obj.read(8192).decode()
                except:
                    self.set_state('aborting')
                    logging.exception("virtual_sdcard read")
                    self.reactor.send_event("klippy:error", "Error reading File")
                    self.gcode.respond_error("Error on virtual sdcard read")
                    break
                if not data:
                    # End of file
                    self.set_state('finished')
                    self.gcode.respond_raw("Done printing file")
                    break
                lines = data.split('\n')
                lines[0] = partial_input + lines[0]
                partial_input = lines.pop()
                lines.reverse()
                self.reactor.pause(self.reactor.NOW)
                continue
            # Pause if any other request is pending in the gcode class
            if gcode_mutex.test():
                self.reactor.pause(self.reactor.monotonic() + 0.050)
                continue
            # Dispatch command
            try:
                self.gcode.run_script(lines[-1])
            except Exception as e:
                self.reactor.send_event("klippy:error", repr(e))
                self.set_state('aborting')
                logging.exception("Virtual sdcard error dispaching command: " + repr(e))
                break
            self.file_position += len(lines.pop()) + 1

        logging.info(f"Exiting SD card print in state {self.state} position {self.file_position}")
        self.additional_printed_time += self.toolhead.get_last_move_time() - self.last_start_time
        # Finish aborting or pausing actions
        if self.state == 'pausing':
            self.gcode.run_script("SAVE_GCODE_STATE NAME=PAUSE_STATE")
            self.gcode.run_script("SET_GCODE_OFFSET X=0 Y=0")
            self.set_state('paused')
        else:
            if self.state == 'aborting':
                self.set_state('aborted')
            self.file_obj.close()
            self.manager.check_queue()
        return self.reactor.NEVER

    def get_printed_time(self, print_time=None):
        if not print_time:
            print_time = self.toolhead.mcu.estimated_print_time(self.reactor.monotonic())
        if self.state in ("printing", "pausing", "aborting"):
            return self.additional_printed_time + print_time - self.last_start_time
        return self.additional_printed_time


class PrintJobManager:
    def __init__(self, config):
        self.toolhead = None
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode_metadata = self.printer.load_object(config, 'gcode_metadata')
        self.printer.load_object(config, 'print_stats')
        self.printer.register_event_handler("klippy:ready", self.handle_ready)
        self.printer.register_event_handler("klippy:shutdown", self.handle_shutdown)
        self.jobs = [] # Print jobs, first is current

    def add_print(self, path):
        """ Add new print job to queue """
        job = PrintJob(path, self)
        self.jobs.append(job)
        self.check_queue()
        self.printer.send_event("virtual_sdcard:print_added", self.jobs, job)

    def pause_print(self, gcmd=None):
        if self.jobs:
            return self.jobs[0].pause()

    def stop_print(self, gcmd=None):
        if self.jobs:
            return self.jobs[0].stop()

    def resume_print(self, gcmd=None):
        if self.jobs:
            return self.jobs[0].resume(gcmd)

    def remove_print(self, idx, uuid):
        if 0 < idx < len(self.jobs) and self.jobs[idx].uuid == uuid:
            self.jobs.pop(idx)
            self.printer.send_event("virtual_sdcard:print_change", self.jobs)
            return True

    def move_print(self, idx, uuid, move):
        if 0 < idx + move < len(self.jobs) and 0 < idx < len(self.jobs) and self.jobs[idx].uuid == uuid:
            to_move = self.jobs.pop(idx)
            self.jobs.insert(idx + move, to_move)
            self.printer.send_event("virtual_sdcard:print_change", self.jobs)
            return True

    def clear_queue(self):
        """ Remove everything but the first element which is currently being printed """
        self.jobs = self.jobs[:1]
        self.printer.send_event("virtual_sdcard:print_change", self.jobs)

    def check_queue(self):
        """ Remove 'aborted' or 'finished' print jobs from queue, start next if necessary """
        if len(self.jobs) and self.jobs[0].state in ('finished', 'aborted'):
            last_job = self.jobs.pop(0)
            self.printer.send_event("virtual_sdcard:print_end", self.jobs, last_job)
        if len(self.jobs) and self.jobs[0].state in ('queued'):
            collision = self.printer.lookup_object('collision')
            available, offset = collision.check_available(self.jobs[0])
            logging.info(f"offset is {offset}")
            self.gcode.run_script(f"SET_GCODE_OFFSET X={offset[0]} Y={offset[1]}")
            if available:
                self.jobs[0].start()

    def get_status(self, eventtime=None):
        return {'jobs': self.jobs}

    def handle_ready(self):
        self.toolhead = self.printer.lookup_object('toolhead')

    def handle_shutdown(self):
        if len(self.jobs) and self.jobs[0].state == 'printing':
            self.stop_print()
            try:
                readpos = max(self.jobs[0].file_position - 1024, 0)
                readcount = self.jobs[0].file_position - readpos
                self.jobs[0].file_obj.seek(readpos)
                data = self.jobs[0].file_obj.read(readcount + 128)
            except:
                logging.exception("virtual_sdcard shutdown read")
                return
            logging.info(f"Virtual sdcard ({readpos}): {repr(data[:readcount])}\n\
                           Upcoming ({self.jobs[0].file_position}): {repr(data[readcount:])}")

    def stats(self, eventtime):
        if len(self.jobs) and self.jobs[0].state in ('printing', 'pausing', 'aborting'):
            return True, f"sd_pos={self.jobs[0].file_position}"
        return False, ""

def load_config(config):
    return PrintJobManager(config)
