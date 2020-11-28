# Support for bed level probes featuring a load cell at which the hotend is
# suspended.
#
# Copyright (C) 2020 Martin Hierholzer <martin@hierholzer.info>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging, time, math


def fit(X, Y):

    def mean(Xs):
        return sum(Xs) / len(Xs)
    m_X = mean(X)
    m_Y = mean(Y)

    def std(Xs, m):
        normalizer = len(Xs) - 1
        return math.sqrt(sum((pow(x - m, 2) for x in Xs)) / normalizer)

    def pearson_r(Xs, Ys):

        sum_xy = 0
        sum_sq_v_x = 0
        sum_sq_v_y = 0

        for (x, y) in zip(Xs, Ys):
            var_x = x - m_X
            var_y = y - m_Y
            sum_xy += var_x * var_y
            sum_sq_v_x += pow(var_x, 2)
            sum_sq_v_y += pow(var_y, 2)
        return sum_xy / math.sqrt(sum_sq_v_x * sum_sq_v_y)

    r = pearson_r(X, Y)

    m = r * (std(Y, m_Y) / std(X, m_X))
    b = m_Y - m * m_X

    return [m,b,r]



class LoadCellProbe:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name()

        pin_name = config.get('adc')
        ppins = self.printer.lookup_object('pins')
        self.mcu_adc = ppins.setup_pin('adc', pin_name)

        self.speed = config.getfloat('speed', 50.0, above=0.)
        self.lift_speed = config.getfloat('lift_speed', self.speed, above=0.)

        self.adc_n_average = config.getint('adc_n_average', 2, minval=1)
        self.adc_n_average_precise = config.getint('adc_n_average_precise',
          3, minval=self.adc_n_average)

        self.threshold = config.getint('threshold', 12, minval=1)
        self.step_size = config.getfloat('step_size', 0.05, above=0.)
        self.incr_step_after_n_same_dir = \
            config.getint('incr_step_after_n_same_dir', 2, minval=1)
        self.precision_goal = config.getfloat('precision_goal', 0.01, above=0.)
        self.max_variance = config.getint('max_variance', 15, minval=0)
        self.delay_exceeding_max_variance = \
            config.getfloat('delay_exceeding_max_variance', 0.1, above=0.)
        self.max_retry = config.getint('max_retry', 100, minval=0)
        self.compensation_z_lift = \
            config.getfloat('compensation_z_lift', 0.2, minval=self.step_size)
        self.delay_compensation_lift = \
            config.getfloat('delay_compensation_lift', 0.5, above=0.)
        self.max_abs_force = \
            config.getint('max_abs_force', 5000, minval=self.threshold+1)

        self.fit_z_start_offset = \
            config.getint('fit_z_start_offset', 0.015)
        self.additional_fit_points = config.getint('additional_fit_points', 10,
            minval=2)
        self.fit_step_size = config.getfloat('fit_step_size', 0.002, above=0.)
        self.fit_min_quality = \
            config.getfloat('fit_min_quality', 0.98, above=0.)

        self.sample_retract_dist = config.getfloat('sample_retract_dist', 2.,
                                                   above=0.)

        self.force_offset = 0
        self.force_subscribers = []

        self.printer.register_event_handler("klippy:ready", self._handle_ready)

        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command('PROBE_ACCURACY', self.cmd_PROBE_ACCURACY,
                                    desc=self.cmd_PROBE_ACCURACY_help)

        # Infer Z position to move to during a probe
        if config.has_section('stepper_z'):
            zconfig = config.getsection('stepper_z')
            self.z_position = zconfig.getfloat('position_min', 0.)
        else:
            pconfig = config.getsection('printer')
            self.z_position = pconfig.getfloat('minimum_z_position', 0.)


    cmd_PROBE_ACCURACY_help = "Probe Z-height accuracy at current XY position"


    def _handle_ready(self):
        self.mcu_adc.setup_adc_callback(None, self._adc_callback)


    def subscribe_force(self, callback):
        self.force_subscribers.append(callback)


    def get_lift_speed(self, gcmd=None):
        if gcmd is not None:
            return gcmd.get_float("LIFT_SPEED", self.lift_speed, above=0.)
        return self.lift_speed


    def get_offsets(self):
        return 0, 0, 0


    def multi_probe_begin(self):
        pass


    def multi_probe_end(self):
        pass


    def _adc_callback(self, time, value):
        for sub in self.force_subscribers :
            sub(value)


    def _move_z_relative(self, length):
        pos = self.tool.get_position()
        self.tool.manual_move([pos[0],pos[1],pos[2]+length], self.speed)


    def _move_z_absolute(self, position):
        pos = self.tool.get_position()
        self.tool.manual_move([pos[0],pos[1],position], self.speed)


    def _average_force(self, gcmd, precise):
        # discard one values, because the ADC sampling is asynchronous to the
        # movement. The readout is asynchronous to the ADC sampling, but it is
        # synchronised to the movement, hence we do not need to discard another
        # value.
        self.mcu_adc.read_single_value()
        # number of averaging values depends on precise mode
        n_average = ( self.adc_n_average_precise if precise else
            self.adc_n_average )
        # start averaging
        attempt = 0
        while True:
          force = 0.
          min_force = +1e6
          max_force = -1e6
          for i in range(0, self.adc_n_average) :
            val = self.mcu_adc.read_single_value()
            force = force + val
            min_force = min(val,min_force)
            max_force = max(val,max_force)

          if max_force - min_force < self.max_variance:
            force = force / self.adc_n_average
            if abs(force) > self.max_abs_force :
              # lift tool head to prevent permament strong force applied to head
              # and bed
              self._move_z_relative(self.compensation_z_lift)
              raise gcmd.error("Maximum absolute force exceeded.")
            return force

          time.sleep(self.delay_exceeding_max_variance)

          attempt = attempt+1
          if attempt > self.max_retry :
            raise gcmd.error("Unstable force reading, maximum retries "
                "exceeded.")


    def _lower_to_threshold(self, gcmd):
        # Lower the tool head until the force threshold is exceeded
        while True:
          # Check threshold before first movement, to prevent doing an unchecked
          # step after a retry
          force = self._average_force(gcmd,False) - self.force_offset
          gcmd.respond_info("z = %f, force = %d"
              % (self.tool.get_position()[2], force))
          if(abs(force) > self.threshold):
            break
          self._move_z_relative(-self.step_size)


    def _fast_approach(self, gcmd):
        # Strategy for fast approach: lower tool head until exceeding threshold,
        # then lift head a bit and compare force with original force_offset. If
        # it matches, the contact is assumed. If not, the force_offset has
        # drifed and the search is continued with the new offset.
        gcmd.respond_info("Commencing fast approach.")
        time.sleep(self.delay_compensation_lift)
        self.force_offset = self._average_force(gcmd,True)
        attempt = 0
        attempt_start_pos = self.tool.get_position()[2]
        while True:

          # lower tool head until force threshold is exceeded
          self._lower_to_threshold(gcmd)

          # confirm contact with new offset measured after compensation lift
          self._move_z_relative(self.compensation_z_lift)
          time.sleep(self.delay_compensation_lift)
          self.force_offset = self._average_force(gcmd,True)
          self._move_z_relative(-self.compensation_z_lift)
          time.sleep(self.delay_compensation_lift)
          force = self._average_force(gcmd,True) - self.force_offset

          # if contact is confirmed with new measurement, terminate fast
          # approach
          if(abs(force) > self.threshold):
            # stay at slightly z-lifted position without contact when returning
            gcmd.respond_info("Fast approach found contact.")
            return

          # check for failure condition
          attempt_dist = attempt_start_pos - self.tool.get_position()[2]
          if attempt_dist < 2*self.step_size :
            attempt = attempt + 1
            if attempt > self.max_retry :
              raise gcmd.error("Force reading drifting too much, maximum "
                  "retries exceeded.")
          else :
            attempt = 0
            attempt_start_pos = self.tool.get_position()[2]


    def _compensated_measurement(self, gcmd):
        # take compensated measurement, will increase z position by
        # self.compensation_z_lift
        time.sleep(self.delay_compensation_lift)
        force_in = self._average_force(gcmd,True)
        self._move_z_relative(self.compensation_z_lift)
        time.sleep(self.delay_compensation_lift)
        force_out = self._average_force(gcmd,True)
        force = force_in - force_out

        # store and log result
        self._data.append(
          (self.tool.get_position()[2]-self.compensation_z_lift, force))
        gcmd.respond_info("z = %f, step size %f, force = %d" %
            (self.tool.get_position()[2]-self.compensation_z_lift,
             self.current_step_size, force))

        return force


    def _iterative_search(self, gcmd):
        # Strategy for iterative search: take series of measurements. If a
        # measurement shows a force above the threshold move tool head away from
        # bed; if force is below threshold move head towards bed. Whenever the
        # direction is changed, reduce the stepsize by a factor of two. When two
        # consecutive measurements go into same direction, increase stepsize by
        # factor of two (up to the start value of the step size used for the
        # fast approach).
        # Each measurement point is compensated for the force offset. This is
        # done by taking another measurement for each point with the tool head
        # moved further away from the bed. This search is continued until the
        # step size is below our precision goal.
        gcmd.respond_info("Commencing iterative search.")
        self.current_step_size = +self.step_size   # sign determines direction
        same_direction_counter = 0
        attempt = 0
        attempt_start_step_size = self.current_step_size

        # lift tool head a bit to make sure the search starts without contact to
        # the bed
        self._move_z_relative(self.compensation_z_lift)

        # initialise array with measurement data
        self._data = []

        while True:
          force = self._compensated_measurement(gcmd)

          # decide next action
          # no hysteresis is used for the force threshold here, because it will
          # fail to converge if the force is changing only slightly when the
          # step size is very small
          if self.current_step_size < 0:
            # currently moving to negative Z
            if(abs(force) > self.threshold):
              # found contact: decrease step size and change direction
              same_direction_counter = 0
              self.current_step_size = -self.current_step_size/2
            else :
              # still no contact:
              # increase step size, if same_direction_counter > 2
              same_direction_counter = same_direction_counter+1
              if same_direction_counter > self.incr_step_after_n_same_dir :
                self.current_step_size = \
                    -min(self.step_size, abs(2*self.current_step_size))
          else :
            # currently moving to positive Z
            if(abs(force) < self.threshold):
              # lost contact: decrease step size and change direction
              same_direction_counter = 0
              self.current_step_size = -self.current_step_size/2
            else :
              # we still have contact:
              # increase step size, if same_direction_counter > 2
              same_direction_counter = same_direction_counter+1
              if same_direction_counter > self.incr_step_after_n_same_dir :
                self.current_step_size = \
                    +min(self.step_size, abs(2*self.current_step_size))

          # check abort condition
          if abs(self.current_step_size) < self.precision_goal :
            gcmd.respond_info("Search completed.")
            # return Z position before compensation step
            return self.tool.get_position()[2] - self.compensation_z_lift - \
                self.current_step_size/2

          # check failure condition
          if abs(self.current_step_size) >= abs(attempt_start_step_size) :
            attempt = attempt + 1
            if attempt > self.max_retry :
              raise gcmd.error("Iterative search does not converge.")
          else :
            attempt = 0
            attempt_start_step_size = self.current_step_size

          # move to new position (incl. reverse compensation step)
          self._move_z_relative(-self.compensation_z_lift +
              self.current_step_size)


    def _perform_fit(self, gcmd, split_point):
        gcmd.respond_info("PERFORM FIT split_point = %f" % split_point)

        # initialise array with measurement data
        self._data = []

        # take additional measurements
        self._move_z_absolute(split_point + self.fit_z_start_offset)
        n = self.additional_fit_points
        while n > 0:
          force = self._compensated_measurement(gcmd)
          if abs(force) > self.threshold :
            n -= 1
          self._move_z_relative(-self.fit_step_size-self.compensation_z_lift)

        # prepare data for linear regression with measuerments below split point
        forces = []
        heights = []
        for point in self._data:
          if abs(point[1]) > self.threshold :
            forces.append(point[1])
            heights.append(point[0])

        # perform linear fit
        m,b,r = fit(forces,heights)
        gcmd.respond_info("Fit result: m = %f, b = %f, r = %f" % (m,b,r))

        # safety check: r must be big enough
        if abs(r) < self.fit_min_quality :
          raise gcmd.error("Fit failed, r too small: %f < %f" %
              (abs(r), self.fit_min_quality))

        # return 0-force offset
        return b


    def run_probe(self, gcmd):
        self.tool = self.printer.lookup_object('toolhead')

        # wait until toolhead is in position
        self.tool.wait_moves()

        # fast, coarse approach
        self._fast_approach(gcmd)

        # precise interative search
        split_point = self._iterative_search(gcmd)

        # perform fit
        result = self._perform_fit(gcmd, split_point)

        pos = self.tool.get_position()
        gcmd.respond_info("FINISHED z = %f" % result)
        return pos[0], pos[1], result


    def cmd_PROBE_ACCURACY(self, gcmd):
        lift_speed = self.get_lift_speed(gcmd)
        sample_count = gcmd.get_int("SAMPLES", 10, minval=1)
        sample_retract_dist = gcmd.get_float("SAMPLE_RETRACT_DIST",
                                             self.sample_retract_dist, above=0.)
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
            self._move_z_relative(sample_retract_dist)
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


def load_config(config):
    probe = LoadCellProbe(config)
    config.printer.add_object('probe', probe)
    config.printer.add_object('load_cell', probe)
    return probe
