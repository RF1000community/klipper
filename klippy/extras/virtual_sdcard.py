# Printjob manager (based on VirtualSDCard) providing API for local printjobs
# with pause-resume, print time prediction, compressed gcode, queue and history 
# functionality
#
# Copyright (C) 2020  Konstantin Vogel <konstantin.vogel@gmx.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import os, logging, re, time
from zipfile import ZipFile


class Printjob:
    def __init__(self, path, production_line_mode, manager):
        self.manager = manager
        self.history = manager.history
        self.reactor = manager.reactor
        self.toolhead = manager.toolhead
        self.gcode = manager.gcode
        self.path = path
        self.name = os.path.splitext(os.path.basename(path))[0]
        self.production_line_mode = production_line_mode # if True dont pause when starting the next job from q
        self.state = 'queued'  # queued -> printing -> pausing -> paused -> printing -> done
        self.file_position = 0 #                -> stopping -> stopped
        self.saved_pause_state = False
        self.start_stop_times = []
        self.slicer_idx = None
        self.slicer_elapsed_times = [] # [[time actually printed, elapsed time put by slicer], ...]
        self.slicer_estimated_time = None
        if os.path.splitext(self.path)[-1] in ('.gco', '.gcode'):
            self.thumbnail_path = None
            try:
                self.file_obj = open(self.path, 'rb')
                self.file_obj.seek(0, os.SEEK_END)
                self.file_size = self.file_obj.tell()
                self.file_obj.seek(0)
            except:
                logging.warning("printjob_manager: couldn't open file {}".format(self.path))
                self.state = 'stopped'
        elif os.path.splitext(self.path)[-1] == '.ufp':
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
                logging.warning("printjob_manager: couldn't open compressed file {}, exception {}".format(self.path, e))
                self.state = 'stopped'

    def start(self):
        logging.info("start from job")
        if self.state == 'queued':
            if self.production_line_mode:
                self.manager.printer.register_event_handler("gcode:read_metadata", self.handle_gcode_metadata)
                self.state = 'printing'
                self.start_stop_times.append([self.toolhead.get_last_move_time(), None])
                self.work_timer = self.reactor.register_timer(self.work_handler, self.reactor.NOW)
            else:
                self.state = 'paused'

    def resume(self):
        if self.state == 'paused':
            self.state = 'printing'
            self.start_stop_times.append([self.toolhead.get_last_move_time(), None])
            if self.saved_pause_state:
                self.gcode.cmd_RESTORE_GCODE_STATE({'NAME':"PAUSE_STATE", 'MOVE':1})
                self.saved_pause_state = False

    def pause(self):
        if self.state == 'printing':
            self.state = 'pausing'

    def stop(self):
        if self.state in ('printing', 'pausing'):
            self.state = 'stopping'
        else:
            self.state = 'stopped'

    def work_handler(self, eventtime):
        logging.warning("entering work handler (position %d)", self.file_position)
        self.reactor.unregister_timer(self.work_timer) # TODO is this really necessary?
        try:
            self.file_obj.seek(self.file_position)
        except:
            logging.exception("virtual_sdcard seek")
            self.gcode.respond_error("Unable to seek file")
            self.state = 'stopping'
        gcode_mutex = self.gcode.get_mutex()
        partial_input = ""
        lines = []
        logging.warning("entering while loop now, state {}".format(self.state))

        while self.state == 'printing':
            # Read more lines if necessary
            if not lines:
                try:
                    data = self.file_obj.read(8192)
                except:
                    self.state = 'stopping'
                    logging.exception("virtual_sdcard read")
                    self.gcode.respond_error("Error on virtual sdcard read")
                    break
                if not data:
                    # End of file
                    self.state = 'done'
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
            try:
                self.gcode.run_script(lines[-1])
            except self.gcode.error:
                break
            except:
                logging.exception("virtual_sdcard dispatch")
                break
            self.file_position += len(lines.pop()) + 1

        # Post print
        logging.warning("Exiting SD card print (position %d)", self.file_position)
        self.start_stop_times[-1][1] = self.toolhead.get_last_move_time()
        if self.state == 'pausing':
            self.state = 'paused'
            self.gcode.cmd_SAVE_GCODE_STATE({'NAME': "PAUSE_STATE"})
            self.saved_pause_state = True
        else:
            if self.state == 'stopping':
                self.state = 'stopped'
            self.file_obj.close()
            self.turn_off_heaters()
            self.history.add(self.path, self.state)
            self.manager.check_queue()
        return self.reactor.NEVER

    def turn_off_heaters(self):
        heater_manager = self.manager.printer.lookup_object('heater')
        for heater in heater_manager.heaters.values():
            heater.set_temp(0)

    def get_printed_time(self, eventtime=None):
        # doesnt use get_last_move_time since this can be ran in UI thread
        # also doesnt use print time since it doesnt advance continuously
        now = self.toolhead.mcu.estimated_print_time(self.reactor.monotonic())
        printed_time = 0
        for time in self.start_stop_times:
            printed_time += - time[0] + (time[1] if time[1] else now)
        return printed_time

    def handle_gcode_metadata(self, eventtime, params):
        line = params['#original']
        # recieves all gcode-comment-lines as they are printed, and searches for print-time estimations
        # needs to be aware of printed file so being a separate plugin makes less sense
        slicers = [ 
            r'KISSlicer' ,
            r'^Slic3r$' ,
            r'Simplify3D\(R\).*' ,
            r'Slic3r Prusa Edition\s.*\so',
            r'Cura_SteamEngine.*' ,
            r'ideaMaker\s([0-9]*\..*,)',
            r'PrusaSlicer'
            ]
        slicer_estimated_time = [
            r'\s\s\d*\.\d*\sminutes' ,                        #    Kisslicer
            r'; estimated printing time' ,                    #    Slic3r
            r';\s+Build time:.*' ,                            #    S3d
            r'\d+h?\s?\d+m\s\d+s' ,                           #    Slic3r PE
            r';TIME:\d+' ,                                    #    Cura
            r';Print Time:\s\d+\.?\d+',                       #    ideamaker
            r'\d+h?\s?\d+m\s\d+s'                             #    PrusaSlicer
            ]
        slicer_elapsed_time = [
            #r'\s\s\d*\.\d*\sminutes' ,                       #    Kisslicer
            #                                                 #    Slic3r
            #r';\s+Build time:.*' ,                           #    S3d
            #r'\d+h?\s?\d+m\s\d+s' ,                          #    Slic3r PE
            r';TIME_ELAPSED:\d+' ,                            #    Cura
            #r';Print Time:\s\d+\.?\d+',                      #    ideamaker
            #                                                 #    PrusaSlicer
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

        if self.slicer_idx is None: # if slicer isn't determined yet we dont make predictions
            for i, slicer in enumerate(slicers):
                if re.search(slicer, line):
                    self.slicer_idx = i
        else:
            estimated = re.search(slicer_estimated_time[self.slicer_idx], line)
            if estimated:
                self.slicer_estimated_time = get_seconds(estimated.group())
                return
            elapsed = re.search(slicer_elapsed_time[self.slicer_idx], line)
            if elapsed:
                self.slicer_elapsed_times.append((self.get_printed_time(), get_seconds(elapsed.group())))

    def get_print_time_prediction(self):
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
            if printed_time <= 0:
                progress = 0
            else: 
                progress = printed_time/float(printed_time + est_remaining)
        return est_remaining, progress

class PrintjobManager(object):
    def __init__(self, config):
        self.toolhead = None
        self.history = PrintjobHistory()
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
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
        self.check_queue()

    def resume_printjob(self):
        self.jobs[0].resume()

    def clear_queue(self):
        """ remove everything but the first element wich is currently being printed """
        self.jobs = self.jobs[:1]

    def check_queue(self):
        if len(self.jobs) and self.jobs[0].state in ('done', 'stopped'):
            self.jobs.pop(0)
        if len(self.jobs) and self.jobs[0].state in ('queued'):
            self.jobs[0].start()

    def get_status(self, eventtime=None):
        if self.jobs != []:
            est_remaining, progress = self.jobs[0].get_print_time_prediction()
        else:
            est_remaining, progress = None, None
        return {'printjobs': self.jobs,
                'progress': progress,
                'estimated_remaining_time': est_remaining}

    def handle_ready(self):
        self.toolhead = self.printer.lookup_object('toolhead')

    def handle_shutdown(self): # TODO
        if self.state == 'printing':
            self.stop()
            try:
                readpos = max(self.file_position - 1024, 0)
                readcount = self.file_position - readpos
                self.file_obj.seek(readpos)
                data = self.file_obj.read(readcount + 128)
            except:
                logging.exception("virtual_sdcard shutdown read")
                return
            logging.info("Virtual sdcard (%d): %s\nUpcoming (%d): %s",
                         readpos, repr(data[:readcount]),
                         self.file_position, repr(data[readcount:]))

    def stats(self, eventtime):
        if len(self.jobs) and self.jobs[0].state in ('printing', 'pausing', 'stopping'):
            return True, "sd_pos=%d" % (self.file_position,)
        return False, ""

class PrintjobHistory:
    """
    Manage print history file

    The history file is json-formatted as a list of lists each containing
    the elements
        [path, state, timestamp],
    whith path being the path of the gcode file,
    status being a string defining the outcome of the print, one of
        "done", "stopped",
    timestamp being the time of completion in seconds since epoch.
    """
    def __init__(self):
        self.history_path = os.path.expanduser("~/")
        self.history = self.read()
        self.trim_history()

    def trim_history(self):
        """Remove all entries of deleted files, return number of removed entries"""
        history = self.history
        to_remove = []
        for e in history:
            if not exists(e[0]):
                to_remove.append(e)
        if to_remove != []:
            for e in to_remove:
                history.remove(e)
            self.write(history)
            self.history = history
            return len(to_remove)
        return 0

    def read(self):
        """Read the history file and return it as a list object"""
        try:
            with open(self.history_path, "r") as fp:
                history = json.load(fp)
        except (IOError, ValueError): # No file or incorrect JSON
            logging.info("History: Couldn't read file at {}".format(self.history_path))
            history = []
        if not self.verify_history(history):
            logging.warning("History: Malformed history file")
            history = []
        return history

    def verify_history(self, history):
        """Only return True when the entire history has a correct structure"""
        try:
            for e in history:
                if not (isinstance(e[0], (unicode, str))        # path
                and (e[1] == "done" or e[1] == "stopped")       # state
                and isinstance(e[2], (float, int))):            # timestamp
                    return False
        except:
            return False
        return True

    def write(self, history):
        """Write the object to the history file"""
        try:
            with open(self.history_path, "w") as fp:
                json.dump(history, fp, indent=True)
        except IOError:
            return

    def add(self, path, state):
        """Add a new entry to the history with the path and state string specified"""
        self.history.append([path, state, time.time()])
        self.write(self.history)

class VirtualSD(PrintjobManager):
    def __init__(self, config):
        super(VirtualSD, self).__init__(config)
        self.selected_file = None # str
        self.file_position = 0
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
        if len(self.jobs) and self.jobs[0].state == 'printing':
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
    return VirtualSD(config)
