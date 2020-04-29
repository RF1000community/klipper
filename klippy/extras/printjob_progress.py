# Printjob progress estimatior for virtual_sdcard prinjobs
# utilizing estimations and elapsed times in gcode put by slicer to
# give instant and accurate estimations
#
# Copyright (C) 2020  Konstantin Vogel <konstantin.vogel@gmx.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import re, logging

class PrintjobProgress:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.initialize_printjob()
        self.printer.register_event_handler("gcode:read_metadata", self.handle_gcode_metadata)
        self.printer.register_event_handler("virtual_sdcard:printjob_ended", self.initialize_printjob)
        self.printer.register_event_handler("klippy:connect", self.handle_connect)

    def handle_connect(self):
        self.printjob_manager = self.printer.lookup_object('virtual_sdcard')

    def initialize_printjob(self, *args):
        self.slicer_elapsed_times = [] # [[time actually printed, elapsed time put by slicer], ...]
        self.slicer_estimated_time = None

    def handle_gcode_metadata(self, eventtime, params):
        line = params['#original']
        # recieves all gcode-comment-lines as they are printed, and searches for print-time estimations
        slicer_estimated_time = [
            r'\s\s\d*\.\d*\sminutes' ,                        # Kisslicer
            r'; estimated printing time' ,                    # Slic3r
            r';\s+Build time:.*' ,                            # S3d
            r'\d+h?\s?\d+m\s\d+s' ,                           # Slic3r PE
            r';TIME:\d+' ,                                    # Cura
            r';Print Time:\s\d+\.?\d+',                       # ideamaker
            r'\d+h?\s?\d+m\s\d+s'                             # PrusaSlicer
            ]
        slicer_elapsed_time = [
            # r'',                                               # Kisslicer
            # r'',                                               # Slic3r
            # r'',                                               # S3d
            # r'',                                               # Slic3r PE
            r';TIME_ELAPSED:\d+',                              # Cura
            # r'',                                               # ideamaker
            # r'',                                               # PrusaSlicer
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
                self.slicer_elapsed_times.append((self.printjob_manager.jobs[0].get_printed_time(), get_seconds(match.group())))
                return

    def get_print_time_prediction(self):
        # time estimations in gcode: |....|....|....|........................|
        # actual print time      |......|.....|.....|.............................|
        #                        ^ start of print   ^ current point in time       ^ prediction
        est_remaining = None
        progress = None

        if self.slicer_estimated_time and len(self.printjob_manager.jobs):
            printed_time = self.printjob_manager.jobs[0].get_printed_time()
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

def load_config(config):
    return PrintjobProgress(config)
