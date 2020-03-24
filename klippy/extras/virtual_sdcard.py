# Virtual sdcard support (print files directly from a host g-code file)
#
# Copyright (C) 2018  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import os, logging, re


class VirtualSD(object):
    def __init__(self, config):
        self.printer = config.get_printer()
        self.printer.register_event_handler("klippy:ready", self.handle_ready)
        self.printer.register_event_handler("klippy:shutdown", self.handle_shutdown)
        self.printer.register_event_handler("gcode:read_metadata", self.handle_gcode_metadata)
        # sdcard state
        sd = config.get('path')
        self.sdcard_dirname = os.path.normpath(os.path.expanduser(sd))
        # Work timer
        self.reactor = self.printer.get_reactor()
        self.must_pause_work = False
        self.cmd_from_sd = False
        self.work_timer = None
        self.saved_pause_state = False
        self.gcode = self.printer.lookup_object('gcode')
        self.current_file = None # python file object
        self.queued_files = [] # as str, first element is current filepath
        self.state = 'no_printjob' # no_printjob -> printing -> paused -> printing -> done -> printing
        self.toolhead = None #                                                  |-> stopped
        self.file_position = 0
        self.slicer_elapsed_times = [] # [[time actually printed, elapsed time put by slicer], ...]
        self.slicer_estimated_time = None

    def add_printjob(self, filepath, pause=True):
        # if it can be printed right away don't pause it
        if len(self.queued_files) < 1:
            pause = False
        self.queued_files.append((filepath, pause))
        self.check_queue()

    def clear_queue(self):
        # remove everything but the first element wich is currently being printed
        self.queued_files = self.queued_files[:1]

    def check_queue(self):
        if  len(self.queued_files) > 0 and self.state != 'printing' and self.state != 'paused':
            # start a printjob
            self.pause_work()
            try:
                f = open(self.queued_files[0][0], 'rb')
                f.seek(0, os.SEEK_END)
                self.file_size = f.tell()
                f.seek(0)
                self.current_file = f
            except:
                logging.warning("virtual_sdcard: couldnt open file{}".format(self.queued_files[0]))
                return False
            logging.warning("virtual_sdcard: has opened file from queue")

            self.file_position = 0
            self.start_stop_times = [[self.toolhead.get_last_move_time(), None]] # [[start, pause], [resume, pause] ...]
            self.slicer_elapsed_times = [] # [[time actually printed, elapsed time put by slicer], ...]
            self.slicer_estimated_time = None
            if self.queued_files[0][1]: # start in paused state
                self.state = 'paused'
                self.must_pause_work = True
            else:
                self.state = 'printing'
                self.must_pause_work = False
                self.work_timer = self.reactor.register_timer(self.work_handler, self.reactor.NOW)
            return True

    def resume_printjob(self):
        if self.state == 'paused':
            self.state = 'printing'
            self.must_pause_work = False
            # work handler has finished while paused, and saved a gcode state
            if self.work_timer is None:
                self.work_timer = self.reactor.register_timer(self.work_handler, self.reactor.NOW)
            if self.saved_pause_state:
                self.gcode.cmd_RESTORE_GCODE_STATE({'NAME':"PAUSE_STATE", 'MOVE':1})
                self.saved_pause_state = False

    def pause_printjob(self):
        if self.state == 'printing':
            self.state = 'paused'
            self.pause_work()
            self.start_stop_times[-1][1] = self.toolhead.get_last_move_time()
 
    def stop_printjob(self):
        self.state = 'stopped'
        self.pause_work()
        self.start_stop_times[-1][1] = self.toolhead.get_last_move_time()
        self.queued_files.pop(0)
        self.check_queue()

    def pause_work(self):
        if self.work_timer is not None:
            self.must_pause_work = True
            while self.work_timer is not None and not self.cmd_from_sd:
                self.reactor.pause(self.reactor.monotonic() + .001)
            logging.warning("stopped pausing work &&&&&&&&&: cmd_from is {}, work timer is {}".format(self.cmd_from_sd, self.work_timer))

    def work_handler(self, eventtime):
        # Background work timer
        logging.warning("Starting SD card print (position %d)", self.file_position)
        logging.warning("work_timer is: {}".format(self.work_timer))
        self.reactor.unregister_timer(self.work_timer)
        try:
            self.current_file.seek(self.file_position)
        except:
            logging.exception("virtual_sdcard seek")
            self.gcode.respond_error("Unable to seek file")
            self.work_timer = None
            return self.reactor.NEVER
        gcode_mutex = self.gcode.get_mutex()
        partial_input = ""
        lines = []
        logging.warning("entering while loop now, work timer is {}".format(self.work_timer))
        while not self.must_pause_work:
            if not lines:
                # Read more data
                try:
                    data = self.current_file.read(8192)
                except:
                    logging.exception("virtual_sdcard read")
                    self.gcode.respond_error("Error on virtual sdcard read")
                    break
                if not data:
                    # End of file
                    self.state = 'done'
                    self.current_file.close()
                    self.queued_files.pop(0)
                    self.start_stop_times[-1][1] = self.toolhead.get_last_move_time()
                    logging.warning("Finished SD card print")
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
                logging.warning("didnt get mutex")
                self.reactor.pause(self.reactor.monotonic() + 0.100)
                continue
            # Dispatch command
            self.cmd_from_sd = True
            try:
                self.gcode.run_script(lines[-1])
            except self.gcode.error:
                break
            except:
                logging.exception("virtual_sdcard dispatch")
                break
            self.cmd_from_sd = False
            self.file_position += len(lines.pop()) + 1
        logging.warning("Exiting SD card print (position %d)", self.file_position)
        self.work_timer = None
        # in some cases we are paused without having a saved pause state, e.g. when starting
        # a printjob from queue as paused or when work handler didnt terminate in time
        if self.state == 'paused':
            self.gcode.cmd_SAVE_GCODE_STATE({'NAME': "PAUSE_STATE"})
            self.saved_pause_state = True
        else:
            # switch off all heaters, especially necessary after print was stopped
            heater_manager = self.printer.lookup_object('heater')
            for heater in heater_manager.heaters.values():
                heater.set_temp(0)
            # print next file in queue
            self.check_queue()
        return self.reactor.NEVER

    def get_printed_time(self, eventtime=None):
        now = self.toolhead.mcu.estimated_print_time(self.reactor.monotonic())#self.reactor.monotonic() #dont run get_last_move_time since this can be ran in UI thread
        # also dont use print time since it doesnt advance continuously
        printed_time = 0
        for time in self.start_stop_times:
            printed_time += - time[0] + (time[1] if time[1] else now)
        return printed_time

    def handle_gcode_metadata(self, eventtime, params):
        line = params['#original']
        # recieves all gcode-comment-lines as they are printed, and searches for print-time estimations
        # needs to be aware of printed file so 
        slicer_estimated_time = [
            r'\s\s\d*\.\d*\sminutes' , 						#	Kisslicer
            r'; estimated printing time' ,					#	Slic3r
            r';\s+Build time:.*' ,							#	S3d
            r'\d+h?\s?\d+m\s\d+s' ,							#	Slic3r PE
            r';TIME:\d+' ,									#	Cura
            r';Print Time:\s\d+\.?\d+',						#	ideamaker
            r'\d+h?\s?\d+m\s\d+s'							#	PrusaSlicer
            ]
        slicer_elapsed_time = [
            #r'\s\s\d*\.\d*\sminutes' , 					#	Kisslicer
            #                               				#	Slic3r
            #r';\s+Build time:.*' ,							#	S3d
            #r'\d+h?\s?\d+m\s\d+s' ,						#	Slic3r PE
            r';TIME_ELAPSED:\d+' ,							#	Cura
            #r';Print Time:\s\d+\.?\d+',					#	ideamaker
            #                                    			#	PrusaSlicer
            ]
        def get_seconds(in_):
            if in_ == -1: return in_
            h_str = re.search(re.compile('(\d+(\s)?hours|\d+(\s)?h)'),in_)
            m_str = re.search(re.compile('(([0-9]*\.[0-9]+)\sminutes|\d+(\s)?m)'),in_)
            s_str = re.search(re.compile('(\d+(\s)?seconds|\d+(\s)?s)'),in_)
            dursecs = 0
            if h_str:
                dursecs += float(max(re.findall('([0-9]*\.?[0-9]+)', ''.join(h_str.group())))) * 3600 
            if m_str:
                dursecs += float(max(re.findall('([0-9]*\.?[0-9]+)', ''.join(m_str.group())))) * 60 
            if s_str:
                dursecs += float(max(re.findall('([0-9]*\.?[0-9]+)', ''.join(s_str.group()))))
            if dursecs == 0:
                dursecs = float(max(re.findall('([0-9]*\.?[0-9]+)', in_)))
            return dursecs
        for regex in slicer_estimated_time:
            match = re.search(regex, line)
            if match:
                self.slicer_estimated_time = get_seconds(match.group())
                return
        for regex in slicer_elapsed_time:
            match = re.search(regex, line)
            if match:
                self.slicer_elapsed_times.append((self.get_printed_time(), get_seconds(match.group())))
                return

    def get_status(self, eventtime=None):
        # time estimations in gcode: |....|....|....|........................|
        # actual print time      |......|.....|.....|.............................|
        #                        ^ start of print   ^ current point in time       ^ prediction
        est_remaining = None
        progress = None
        if self.state == 'done':
            est_remaining = 0
            progress = 1
        elif self.slicer_estimated_time:
            printed_time = self.get_printed_time()
            if len(self.slicer_elapsed_times):
                time_since_slicer_est = printed_time\
                                      - self.slicer_elapsed_times[-1][0]
                est_remaining  = max(0, self.slicer_estimated_time\
                                      - self.slicer_elapsed_times[-1][1]\
                                      - time_since_slicer_est)
                # now apply factor based on how wrong previous estimations were
                # we ignore the first estimation block since it contains heatup
                # where high variance is expected
                if len(self.slicer_elapsed_times) > 1:
                    est_remaining *= \
                        (self.slicer_elapsed_times[-1][1] - self.slicer_elapsed_times[0][1])\
                       /(self.slicer_elapsed_times[-1][0] - self.slicer_elapsed_times[0][0])
            else: #we dont have elapsed times
                est_remaining = max(self.slicer_estimated_time - printed_time, 0)
            # time estimation done, calculate progress, avoid zero division
            if printed_time <= 0: progress = 0
            else: progress = printed_time/float(printed_time + est_remaining)
        return {'state': self.state,
                'progress': progress,
                'estimated_remaining_time': est_remaining,
                'queued_files': [f[0] for f in self.queued_files]}

    def handle_ready(self):
        self.toolhead = self.printer.lookup_object('toolhead')

    def handle_shutdown(self):
        if self.work_timer:
            self.must_pause_work = True
            try:
                readpos = max(self.file_position - 1024, 0)
                readcount = self.file_position - readpos
                self.current_file.seek(readpos)
                data = self.current_file.read(readcount + 128)
            except:
                logging.exception("virtual_sdcard shutdown read")
                return
            logging.info("Virtual sdcard (%d): %s\nUpcoming (%d): %s",
                         readpos, repr(data[:readcount]),
                         self.file_position, repr(data[readcount:]))

    def stats(self, eventtime):
        if self.work_timer:
            return True, "sd_pos=%d" % (self.file_position,)
        return False, ""

class GcodeVirtualSD(VirtualSD):
    def __init__(self, config):
        super(GcodeVirtualSD, self).__init__(config)
        self.selected_file = None # str
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
        return self.work_timer is not None
    def cmd_error(self, params):
        raise self.gcode.error("SD write not supported")
    def cmd_M20(self, params):
        # List SD card
        files = self.get_file_list()
        self.gcode.respond("Begin file list")
        for fname, fsize in files:
            self.gcode.respond("%s %d" % (fname, fsize))
        self.gcode.respond("End file list")
    def cmd_M21(self, params):
        # Initialize SD card
        self.gcode.respond("SD card ok")
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
        if self.work_timer is not None:
            raise self.gcode.error("SD busy")
        pos = self.gcode.get_int('S', params, minval=0)
        self.file_position = pos
    def cmd_M27(self, params):
        # Report SD print status
        if self.state == 'printing':
            self.gcode.respond("SD printing byte %d/%d" % (
            self.file_position, self.file_size))
        else:
            self.gcode.respond("SD print {}".format(self.state))

def load_config(config):
    return GcodeVirtualSD(config)

