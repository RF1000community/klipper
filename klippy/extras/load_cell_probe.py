# Support for bed level probes featuring a load cell at which the hotend is
# suspended.
#
# Copyright (C) 2022 Martin Hierholzer <martin@hierholzer.info>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

from mathutil import linear_regression
import sys
import logging

syspath = sys.path
sys.path = syspath[1:]
import statistics
sys.path = syspath

###########################
# Configuration constants #
###########################

# Speed used for all movements; "as fast as possible"
SPEED=500.0

# Lift distance for compensation measurement (relative to fit step size)
COMPENSATION_Z_LIFT_FACTOR=40

# Aim for forces lower than max_abs_force by this factor ("target force").
# Note that the target force can be exceeded regularly by a factor of 1.5 by
# design (since threshold is half the target force).
FORCE_SAFETY_MARGIN=5.

# Divider to compute threshold from target force
THRESHOLD_DIVIDER=4.

# Number of points for the fit (theoretical minimum is 3)
FIT_POINTS=5

# Minimum fit quality factor to accept result
FIT_MIN_QUALITY=0.85

# Factor above noise level to use data points for fit
FIT_THRESHOLD_FACTOR=6

# Maximum number of fit steps per full motor step. Typically, micro steps are
# not perfectly linear. Using a smaller step size for the fit raster scan than
# 1/4 or maybe 1/8 full step might reduce precision.
FIT_SUB_STEPPING=4

# Number of retries if fit fails (due to FIT_MIN_QUALITY)
MAX_RETRY=5

###########################


class LoadCellProbe:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name()
        self.reactor = self.printer.get_reactor()
        self.configfile = self.printer.lookup_object('configfile')
        
        pin_name = config.get('adc')
        ppins = self.printer.lookup_object('pins')
        self.mcu_adc = ppins.setup_pin('adc', pin_name)
        
        # Parameters from configuration, e.g. determined by calibration commands
        # ----------------------------------------------------------------------

        # Conversion factor to convert ADC readings into physical units.
        self.force_calibration = config.getfloat('force_calibration')

        # Maximum acceptable force
        self.max_abs_force = config.getfloat('max_abs_force', above=0.)

        # Stiffness/"spring constant", i.e. force per distance
        self.stiffness = config.getfloat('stiffness', above=0.)

        # Noise level of force measurements (standard deviation, in physical
        # units)
        self.noise_level = config.getfloat('noise_level', above=0.)
        
        # From stepper_z section: Distance for one full step
        cfg_stepper_z = config.getsection("stepper_z")
        rotation_distance = cfg_stepper_z.getfloat("rotation_distance")
        full_steps = config.getint('full_steps_per_rotation', 200)
        full_step_distance = rotation_distance/full_steps
        

        # Compute derived parameters
        # --------------------------
        target_force = self.max_abs_force / FORCE_SAFETY_MARGIN
        
        # Threshold is half-way to "target" force
        self.threshold = target_force / THRESHOLD_DIVIDER
        
        # Step size is the distance to  of the target_force 
        self.step_size = target_force / self.stiffness

        # Threshold for data points used in fit
        self.fit_threshold = self.noise_level * FIT_THRESHOLD_FACTOR

        # Step size of the fit data points: chosen as small as possibe, such
        # that each data point is significantly different from previous data
        # point and the step size is not below a quater step on the z axis
        self.fit_step_size = max( self.fit_threshold / self.stiffness,
                                  full_step_distance/FIT_SUB_STEPPING)

        # Distance of Z compensation lift
        self.compensation_z_lift = self.fit_step_size *                        \
                                   COMPENSATION_Z_LIFT_FACTOR

        # initialise data members
        self.last_z_result = 0
        self.force_offset = None
        self._last_uncompensated_force = None
        self.last_force = 0
        self._last_time = None
        self.report_time = 0.0001
        self.force_subscribers = []
        self._last_move_time = 0

        # subscribe to ADC callbackin ready event, since ADC module might not
        # yet be available.
        self.printer.register_event_handler("klippy:ready", self._handle_ready)

        # register gcode commands
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command('PROBE', self.cmd_PROBE,
                                    desc=self.cmd_PROBE_help)

        self.gcode.register_command('PROBE_ACCURACY', self.cmd_PROBE_ACCURACY,
                                    desc=self.cmd_PROBE_ACCURACY_help)

        self.gcode.register_command('READ_LOAD_CELL', self.cmd_READ_LOAD_CELL,
                                    desc=self.cmd_READ_LOAD_CELL_help)

        self.gcode.register_command('COMPENSATE_LOAD_CELL',
                                    self.cmd_COMPENSATE_LOAD_CELL,
                                    desc=self.cmd_COMPENSATE_LOAD_CELL_help)

        self.gcode.register_command('LOAD_CELL_CALIB_NOISE',
                                    self.cmd_LOAD_CELL_CALIB_NOISE,
                                    desc=self.cmd_LOAD_CELL_CALIB_NOISE_help)

        self.gcode.register_command('LC_INFO', self.LC_INFO)


    cmd_PROBE_ACCURACY_help = "Determine probe accuracy at current position."
    cmd_PROBE_help = "Run probe and stop at the contact position."
    cmd_READ_LOAD_CELL_help = "Print current load cell measurement to the "    \
            + "console using the same averaging setting as for the probe."
    cmd_COMPENSATE_LOAD_CELL_help = "Set load cell compensation offset to "    \
            + "current measured value. Only affects output of READ_LOAD_CELL." \
            + " Any PROBE command will also perform the compensation."
    cmd_LOAD_CELL_CALIB_NOISE_help = "Determine typical noise level of load "  \
            + "cell measurements."



    def LC_INFO(self, gcmd):
        gcmd.respond_info(str(syspath[1:]))
        gcmd.respond_info("self.threshold = %f" % self.threshold)
        gcmd.respond_info("self.step_size = %f" % self.step_size)
        gcmd.respond_info("self.fit_threshold = %f" % self.fit_threshold)
        gcmd.respond_info("self.fit_step_size = %f" % self.fit_step_size)
        gcmd.respond_info("self.compensation_z_lift = %f" % self.compensation_z_lift)


    def _handle_ready(self):
        self.mcu_adc.setup_adc_callback(None, self._adc_callback)


    # Allow another module to subscribe to the load-cell measurement. This is
    # used e.g. for the z_sense_offset module.
    def subscribe_force(self, callback):
        self.force_subscribers.append(callback)


    def get_lift_speed(self, gcmd=None):
        if gcmd is not None:
            return gcmd.get_float("LIFT_SPEED", SPEED, above=0.)
        return SPEED


    def get_offsets(self):
        return 0, 0, 0


    def multi_probe_begin(self):
        pass


    def multi_probe_end(self):
        pass


    def _adc_callback(self, time, value):
        # convert to physical unit
        self._last_uncompensated_force = value * self.force_calibration
        # First value after start: use as zero offset
        if self.force_offset == None :
          self.force_offset = self._last_uncompensated_force
        # Compute time difference between samples
        if self._last_time != None :
          self.report_time = time - self._last_time
          logging.info("report_time = "+str(self.report_time))
        self._last_time = time
        # Store zero offset compensated value for display
        self.last_force = self._last_uncompensated_force - self.force_offset
        # Forward uncompensated value to subscribers
        for sub in self.force_subscribers :
            sub(value)


    def _adc_wait_conversion_ready(self):
        # wait shortly after the timer has called _sample_timer
        #self._last_time = self.reactor.pause(self._last_time + self.report_time
        #    + 0.0001)
        self.reactor.pause(self._last_move_time + self.report_time)


    def _move_z_relative(self, length, wait=True):
        pos = self.tool.get_position()
        self.tool.manual_move([pos[0],pos[1],pos[2]+length], SPEED)
        self._last_move_time = self.tool.print_time
        logging.info("_last_move_time = "+str(self._last_move_time))
        if wait:
          self.tool.wait_moves()


    def _move_axis_relative(self, length, wait=True):
        # move along selected probing axis
        pos = self.tool.get_position()
        pos[2] += length
        self.tool.manual_move([pos[0],pos[1],pos[2]], SPEED)
        self._last_move_time = self.tool.print_time
        logging.info("_last_move_time = "+str(self._last_move_time))
        if wait:
          self.tool.wait_moves()


    def _move_axis_absolute(self, position, wait=True):
        pos = self.tool.get_position()
        pos[2] = position
        self.tool.manual_move([pos[0],pos[1],pos[2]], SPEED)
        self._last_move_time = self.tool.print_time
        logging.info("_last_move_time = "+str(self._last_move_time))
        if wait:
          self.tool.wait_moves()


    def _read_uncompensated_force(self, gcmd, precise):
        # discard one values, because the ADC sampling is asynchronous to the
        # movement. The readout is asynchronous to the ADC sampling, but it is
        # synchronised to the movement, hence we do not need to discard another
        # value.
        self._adc_wait_conversion_ready()

        # read ADC sample
        self._adc_wait_conversion_ready()
        
        # check if maximum force exceeded
        if abs(self._last_uncompensated_force) > self.max_abs_force :
          # lift tool head to prevent permament strong force applied to head
          # and bed
          self._move_z_relative(self.compensation_z_lift)
          raise gcmd.error("Maximum absolute force exceeded.")

        return self._last_uncompensated_force


    def _lower_to_threshold(self, gcmd):
        # Lower the tool head until the force threshold is exceeded
        while True:
          # Check threshold before first movement, to prevent doing an unchecked
          # step after a retry
          force = self._read_uncompensated_force(gcmd,False) - self.force_offset
          gcmd.respond_info("pos = %f, force = %.1f"
              % (self.tool.get_position()[2], force))
          if(abs(force) > self.threshold):
            break
          self._move_axis_relative(                                            \
              -1*self.step_size)


    def _fast_approach(self, gcmd):
        # Strategy for fast approach: lower tool head until exceeding threshold,
        # then lift head a bit and compare force with original force_offset. If
        # it matches, the contact is assumed. If not, the force_offset has
        # drifed and the search is continued with the new offset.
        gcmd.respond_info("Commencing fast approach.")
        self.force_offset = self._read_uncompensated_force(gcmd,False)
        attempt = 0
        attempt_start_pos = self.tool.get_position()[2]
        while True:

          # lower tool head until force threshold is exceeded
          self._lower_to_threshold(gcmd)

          # confirm contact with compensated measuerment (also updating the
          # force_offset)
          force = self._compensated_measurement(gcmd)

          # if contact is confirmed with new measurement, terminate fast
          # approach
          if(abs(force) > self.threshold):
            # stay at slightly z-lifted position without contact when returning
            gcmd.respond_info("Fast approach found contact.")
            return force

          # check for failure condition
          attempt_dist = attempt_start_pos + \
            -1*self.tool.get_position()[2]
          if attempt_dist < 2*self.step_size :
            attempt = attempt + 1
            if attempt > MAX_RETRY :
              raise gcmd.error("Force reading drifting too much, maximum "
                  "retries exceeded.")
          else :
            attempt = 0
            attempt_start_pos = self.tool.get_position()[2]


    def _compensated_measurement(self, gcmd):
        # take compensated measurement, update force_offset
        self._move_z_relative(self.compensation_z_lift)
        self.force_offset = self._read_uncompensated_force(gcmd,True)
        self._move_z_relative(-self.compensation_z_lift)
        force_in = self._read_uncompensated_force(gcmd,True)
        force = force_in - self.force_offset

        gcmd.respond_info("pos = %f, force(cmp) = %.1f" %
            (self.tool.get_position()[2], force))

        return force


    def _find_fit_start(self, gcmd, force0):
        force1 = force0
        self._move_axis_relative(self.step_size/2,False)
        while abs(force1) > self.fit_threshold*2:
          force2 = self._compensated_measurement(gcmd)
          if abs(force2) < self.fit_threshold*2:
            break
          slope = (self.step_size/2)/max(force2-force1,1)
          dist = min(abs((force2-self.fit_threshold)*slope),                   \
              self.step_size/2)
          self._move_axis_relative(dist,False)
          force1 = force2


    def _perform_fit(self, gcmd):
        gcmd.respond_info("PERFORM FIT")

        # initialise array with measurement data
        data = []

        # take raster scan measurements to collect data for fit
        while True:
          force = self._compensated_measurement(gcmd)

          # check abort condition
          if len(data) >= FIT_POINTS:
            break

          # store measurement data for linear fit
          if abs(force) > self.fit_threshold :
            height = self.tool.get_position()[2]
            data.append([height, force])

          # move to next position
          self._move_axis_relative(-1*self.fit_step_size,
              False)

        # perform fit to find zero force contact position
        heights = [ d[0] for d in data ]
        forces = [ d[1] for d in data ]
        m,b,r,sm,sb = linear_regression(forces, heights)

        gcmd.respond_info(
          "Fit result: m = %f, b = %f, r = %f, sm = %f, sb = %f"
          % (m,b,r,sm,sb))

        # safety check: r must be big enough
        if abs(r) < FIT_MIN_QUALITY :
          gcmd.respond_info(
            "Fit failed, fit quality factor r too small: %f < %f" %
            (abs(r), FIT_MIN_QUALITY))
          return None

        # return 0-force offset
        return b


    def run_probe(self, gcmd):

        # obtain toolhead object
        self.tool = self.printer.lookup_object('toolhead')

        # wait until toolhead is in position
        self.tool.wait_moves()

        repeat_count=0
        while True:
          # fast, coarse approach
          force = self._fast_approach(gcmd)

          # find start position for fit (no contact but as close to surface)
          self._find_fit_start(gcmd, force)

          # perform raster scan and fit
          result = self._perform_fit(gcmd)
          if result is not None:
            break

          # check abort condition
          repeat_count += 1
          if repeat_count > MAX_RETRY:
            raise gcmd.error("Maximum retries reached, giving up.")
          gcmd.respond_info("Retrying...")
          self._move_axis_relative(5*self.step_size, False)

        pos = self.tool.get_position()
        gcmd.respond_info("FINISHED toolhead Z = %f" % result)
        pos[2] = result
        self.last_z_result = result
        return pos[0], pos[1], pos[2]


    def cmd_PROBE_ACCURACY(self, gcmd):
        lift_speed = self.get_lift_speed(gcmd)
        sample_count = gcmd.get_int("SAMPLES", 10, minval=1)
        sample_retract_dist = gcmd.get_float("SAMPLE_RETRACT_DIST",
                                             2., above=0.)

        toolhead = self.printer.lookup_object('toolhead')
        pos = toolhead.get_position()
        gcmd.respond_info("PROBE_ACCURACY at X:%.3f Y:%.3f Z:%.3f"
                          " (samples=%d retract=%.3f"
                          " lift_speed=%.1f)\n"
                          % (pos[0], pos[1], pos[2],
                             sample_count, sample_retract_dist,
                             lift_speed))
        # Probe bed sample_count times
        self.multi_probe_begin()
        positions = []
        while len(positions) < sample_count:
            # Probe position
            pos = self.run_probe(gcmd)
            positions.append(pos)
            # Retract
            self._move_axis_relative(sample_retract_dist)
        self.multi_probe_end()
        # Calculate maximum, minimum and average values
        max_value = max([p[2] for p in positions])
        min_value = min([p[2] for p in positions])
        range_value = max_value - min_value
        avg_value = self._calc_mean(positions)[2]
        median = self._calc_median(positions)[2]
        # calculate the standard deviation
        deviation_sum = 0
        for i in range(len(positions)):
            deviation_sum += pow(positions[i][2] - avg_value, 2.)
        sigma = (deviation_sum / len(positions)) ** 0.5
        # Show information
        gcmd.respond_info(
            "probe accuracy results: maximum %.6f, minimum %.6f, range %.6f, "
            "average %.6f, median %.6f, standard deviation %.6f" % (
            max_value, min_value, range_value, avg_value, median, sigma))


    def cmd_PROBE(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        pos = toolhead.get_position()

        gcmd.respond_info("PROBE at X:%.3f Y:%.3f Z:%.3f\n"
                          % (pos[0], pos[1], pos[2]))

        pos = self.run_probe(gcmd)
        self.tool.manual_move([pos[0],pos[1],pos[2]], SPEED)
        self.tool.wait_moves()


    def _calc_mean(self, positions):
        count = float(len(positions))
        return [sum([pos[i] for pos in positions]) / count
                for i in range(3)]


    def _calc_median(self, positions):
        z_sorted = sorted(positions, key=(lambda p: p[2]))
        middle = len(positions) // 2
        if (len(positions) & 1) == 1:
            # odd number of samples
            return z_sorted[middle]
        # even number of samples
        return self._calc_mean(z_sorted[middle-1:middle+1])


    def cmd_READ_LOAD_CELL(self, gcmd):
        force = self._read_uncompensated_force(gcmd,True)
        gcmd.respond_info("Uncompensated: %.6f  compensated: %.6f" %           \
                          (force, force - self.force_offset))


    def cmd_COMPENSATE_LOAD_CELL(self, gcmd):
        self.force_offset = self._read_uncompensated_force(gcmd,True)


    def cmd_LOAD_CELL_CALIB_NOISE(self, gcmd):
        sample_count = gcmd.get_int("SAMPLES", 10, minval=2)
        gcmd.respond_info("Determine noise level from %d samples:" %           \
                          sample_count)

        samples = []
        for s in range(0, sample_count):
          samples.append(self._read_uncompensated_force(gcmd,True))
        
        self.noise_level = statistics.stdev(samples)

        gcmd.respond_info("noise_level = %6.2f" % self.noise_level)
        self.configfile.set(self.name, 'noise_level', self.noise_level)
        gcmd.respond_info("The SAVE_CONFIG command will update the printer\n"
                  "config file and restart the printer.")


    def get_status(self, eventtime):
        return {
          'last_force': self.last_force,
          'last_z_result': self.last_z_result,
        }


def load_config(config):
    probe = LoadCellProbe(config)
    config.printer.add_object('probe', probe)
    # Add second "load_cell" object to make load cell measurement available to
    # other modules (e.g. z_sense_offset)
    config.printer.add_object('load_cell', probe)
    return probe
