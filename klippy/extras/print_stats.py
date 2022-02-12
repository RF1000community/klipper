# Print job progress estimatior for virtual_sdcard
# utilizing estimations and elapsed times in gcode put by slicer to
# give instant and accurate estimations
#
# Copyright (C) 2020  Konstantin Vogel <konstantin.vogel@gmx.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

class PrintStats:

    def __init__(self, config):
        self.printer = config.get_printer()
        self.initialize_print()
        self.printer.register_event_handler("gcode:read_metadata", self.handle_gcode_metadata)
        self.printer.register_event_handler("virtual_sdcard:print_end", self.initialize_print)
        # this relies on no gcode being processed before the start event which is given.
        self.printer.register_event_handler("virtual_sdcard:print_start", self.initialize_print)
        self.printer.register_event_handler("klippy:ready", self.handle_ready)

        # List of time estimations by the slicer inside the gcode
        # [[time actually printed, elapsed time put by slicer], ...]
        self.slicer_elapsed_times = []

    def handle_ready(self):
        self.virtual_sdcard = self.printer.lookup_object('virtual_sdcard')

    def initialize_print(self, *args):
        self.slicer_elapsed_times = []

    def handle_gcode_metadata(self, print_time, line):
        """
        Recieves all gcode-comment-lines as they are printed,
        and searches for print-time estimations
        """
        if self.virtual_sdcard.jobs:
            job = self.virtual_sdcard.jobs[0]
            slicer_elapsed_time = job.md.parse_elapsed_time(line)
            if slicer_elapsed_time is not None:
                self.slicer_elapsed_times.append(
                        (job.get_printed_time(), slicer_elapsed_time))

    def get_print_time_prediction(self):
        """ we try to consider everything 'printed' that ran through gcode processing,
            time is measured using print_time
            time estimations in gcode: |....|....|....|........................|
            actual print time      |......|.....|.....|.............................|
                                   ^ start of print   ^ current point in time       ^ prediction
            after the print job is done the output is undefined, normally None """
        if self.virtual_sdcard.jobs:
            job = self.virtual_sdcard.jobs[0]
            slicer_estimated_time = job.md.get_time()
        else: # No print job in queue
            return None, None
        if slicer_estimated_time is None:  # No time prediction
            return None, None

        est_remaining = None
        progress = None

        printed_time = job.get_printed_time()
        if self.slicer_elapsed_times:
            time_since_slicer_est = (printed_time
                                     - self.slicer_elapsed_times[-1][0])
            est_remaining = max(0, slicer_estimated_time
                                 - self.slicer_elapsed_times[-1][1]
                                 - time_since_slicer_est)
            # now apply factor based on how wrong previous estimations were
            # we ignore the first estimation block since it contains heatup
            # where high variance is expected
            if len(self.slicer_elapsed_times) > 1:
                est_remaining *= \
                    (self.slicer_elapsed_times[-1][0] - self.slicer_elapsed_times[0][0]) \
                   /(self.slicer_elapsed_times[-1][1] - self.slicer_elapsed_times[0][1])
        else: # We dont have elapsed times
            est_remaining = max(slicer_estimated_time - printed_time, 0)

        # Time estimation done, calculate progress, avoid zero division
        if printed_time <= 0:
            progress = 0
        else:
            progress = printed_time/(printed_time + est_remaining)

        return est_remaining, progress

def load_config(config):
    return PrintStats(config)
