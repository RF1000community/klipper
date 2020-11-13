# Support for bed level probes featuring a load cell at which the hotend is suspended.
#
# Copyright (C) 2020  Martin Hierholzer <martin@hierholzer.info>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging, time

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
        self.threshold = config.getint('threshold', 12, minval=1)
        self.step_size = config.getfloat('step_size', 0.05, above=0.)
        self.incr_step_after_n_same_dir = config.getint('incr_step_after_n_same_dir', 2, minval=1)
        self.precision_goal = config.getfloat('precision_goal', 0.002, above=0.)
        self.max_variance = config.getint('max_variance', 15, minval=0)
        self.delay_exceeding_max_variance = config.getfloat('delay_exceeding_max_variance', 0.1, above=0.)
        self.max_retry = config.getint('max_retry', 100, minval=0)
        self.compensation_z_lift = config.getfloat('compensation_z_lift', 0.2, minval=self.step_size)
        self.delay_compensation_lift = config.getfloat('delay_compensation_lift', 0.1, above=0.)
        self.max_abs_force = config.getint('max_abs_force', 5000, minval=self.threshold+1)
        self.force_offset = 0

        # Infer Z position to move to during a probe
        if config.has_section('stepper_z'):
            zconfig = config.getsection('stepper_z')
            self.z_position = zconfig.getfloat('position_min', 0.)
        else:
            pconfig = config.getsection('printer')
            self.z_position = pconfig.getfloat('minimum_z_position', 0.)

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

    def _move_z_relative(self, length):
        pos = self.tool.get_position()
        self.tool.manual_move([pos[0],pos[1],pos[2]+length], self.speed)
        
    def _average_force(self, gcmd):
        # discard one values, because the ADC sampling is asynchronous to the movement. The readout is asynchronous to
        # the ADC sampling, but it is synchronised to the movement, hence we do not need to discard another value.
        self.mcu_adc.read_current_value()
        attempt = 0
        while True:
          force = 0.
          min_force = +1e6
          max_force = -1e6
          for i in range(0, self.adc_n_average) :
            val = self.mcu_adc.read_current_value()
            force = force + val
            min_force = min(val,min_force)
            max_force = max(val,max_force)
            
          if max_force - min_force < self.max_variance:
            force = force / self.adc_n_average
            if abs(force) > self.max_abs_force :
              # lift tool head to prevent permament strong force applied to head and bed
              self._move_z_relative(self.compensation_z_lift)
              raise gcmd.error("Maximum absolute force exceeded.")
            return force

          time.sleep(self.delay_exceeding_max_variance)
          
          attempt = attempt+1
          if attempt > self.max_retry :
            raise gcmd.error("Unstable force reading, maximum retries exceeded.")
    
    def _lower_to_threshold(self, gcmd):
        # Lower the tool head until the force threshold is exceeded
        while True:
          # Check threshold before first movement, to prevent doing an unchecked step after a retry
          force = self._average_force(gcmd) - self.force_offset
          gcmd.respond_info("z = %f, force = %d" % (self.tool.get_position()[2], force))
          if(abs(force) > self.threshold):
            break
          self._move_z_relative(-self.step_size)

    def _fast_approach(self, gcmd):
        # Strategy for fast approach: lower tool head until exceeding threshold, then lift head a bit and compare force
        # with original force_offset. If it matches, the contact is assumed. If not, the force_offset has drifed and
        # the search is continued with the new offset.
        gcmd.respond_info("Commencing fast approach.")
        self.force_offset = self._average_force(gcmd)
        attempt = 0
        attempt_start_pos = self.tool.get_position()[2]
        while True:
        
          # lower tool head until force threshold is exceeded
          self._lower_to_threshold(gcmd)
          
          # confirm contact with new offset measured after compensation lift
          self._move_z_relative(self.compensation_z_lift)
          time.sleep(self.delay_compensation_lift)
          self.force_offset = self._average_force(gcmd)
          self._move_z_relative(-self.compensation_z_lift)
          time.sleep(self.delay_compensation_lift)
          force = self._average_force(gcmd) - self.force_offset
          
          # if contact is confirmed with new measurement, terminate fast approach
          if(abs(force) > self.threshold):
            # stay at slightly z-lifted position without contact when returning
            gcmd.respond_info("Fast approach found contact.")
            return
          
          # check for failure condition
          if attempt_start_pos - self.tool.get_position()[2] < 2*self.step_size :
            attempt = attempt + 1
            if attempt > self.max_retry :
              raise gcmd.error("Force reading drifting too much, maximum retries exceeded.")
          else :
            attempt = 0
            attempt_start_pos = self.tool.get_position()[2]

    def _iterative_search(self, gcmd):
        # Strategy for iterative search: take series of measurements. If a measurement shows a force above the threshold
        # move tool head away from bed; if force is below threshold move head towards bed. Whenever the direction is
        # changed, reduce the stepsize by a factor of two. When two consecutive measurements go into same direction,
        # increase stepsize by factor of two (up to the start value of the step size used for the fast approach).
        # Each measurement point is compensated for the force offset. This is done by taking another measurement for
        # each point with the tool head moved further away from the bed.
        # This search is continued until the step size is below our precision goal.
        gcmd.respond_info("Commencing iterative search.")
        current_step_size = +self.step_size   # sign determines direction
        same_direction_counter = 0
        attempt = 0
        attempt_start_step_size = current_step_size
        
        # lift tool head a bit to make sure the search starts without contact to the bed
        self._move_z_relative(self.compensation_z_lift)

        while True:
          # take compensated measurement
          time.sleep(self.delay_compensation_lift)
          force_in = self._average_force(gcmd)
          self._move_z_relative(self.compensation_z_lift)
          time.sleep(self.delay_compensation_lift)
          force_out = self._average_force(gcmd)
          force = force_in - force_out
          
          # log result
          gcmd.respond_info("z = %f, step size %f, force = %d" % (self.tool.get_position()[2]-self.step_size, current_step_size, force))
          
          # decide next action
          # no hysteresis is used for the force threshold here, because it will fail to converge if the force is
          # changing only slightly when the step size is very small
          if current_step_size < 0:
            # currently moving to negative Z
            if(abs(force) > self.threshold):
              # found contact: decrease step size and change direction
              same_direction_counter = 0
              current_step_size = -current_step_size/2
            else :
              # still no contact: increase step size, if same_direction_counter > 2
              same_direction_counter = same_direction_counter+1
              if same_direction_counter > self.incr_step_after_n_same_dir :
                current_step_size = -min(self.step_size, abs(2*current_step_size))
          else :
            # currently moving to positive Z
            if(abs(force) < self.threshold):
              # lost contact: decrease step size and change direction
              same_direction_counter = 0
              current_step_size = -current_step_size/2
            else :
              # we still have contact: increase step size, if same_direction_counter > 2
              same_direction_counter = same_direction_counter+1
              if same_direction_counter > self.incr_step_after_n_same_dir :
                current_step_size = +min(self.step_size, abs(2*current_step_size))
          
          # check abort condition
          if abs(current_step_size) < self.precision_goal :
            gcmd.respond_info("Search completed.")
            # return Z position before compensation step
            return self.tool.get_position()[2] - self.step_size
          
          # check failure condition
          if abs(current_step_size) >= abs(attempt_start_step_size) :
            attempt = attempt + 1
            if attempt > self.max_retry :
              raise gcmd.error("Iterative search does not converge.")
          else :
            attempt = 0
            attempt_start_step_size = current_step_size

          # move to new position (incl. reverse compensation step)
          self._move_z_relative(-self.compensation_z_lift + current_step_size)

    def run_probe(self, gcmd):
        v = self.mcu_adc.read_current_value()
        gcmd.respond_info("ADC value %d" % v)

        self.tool = self.printer.lookup_object('toolhead')
        
        # wait until toolhead is in position
        self.tool.wait_moves()
        
        # fast, coarse approach
        self._fast_approach(gcmd)
        
        # precise interative search
        result = self._iterative_search(gcmd)

        pos = self.tool.get_position()
        gcmd.respond_info("FINISHED z = %f" % result)
        return pos[0], pos[1], result

def load_config(config):
    probe = LoadCellProbe(config)
    config.printer.add_object('probe', probe)
    return probe
