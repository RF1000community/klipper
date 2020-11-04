# Support for bed level probes featuring a load cell at which the hotend is suspended.
#
# Copyright (C) 2020  Martin Hierholzer <martin@hierholzer.info>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging

class LoadCellProbe:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name()
        
        pin_name = config.get('adc')
        ppins = self.printer.lookup_object('pins')
        self.mcu_adc = ppins.setup_pin('adc', pin_name)
        logging.info("LoadCellProbe HIER1")

        self.speed = config.getfloat('speed', 5.0, above=0.)
        self.lift_speed = config.getfloat('lift_speed', self.speed, above=0.)
        self.threshold = config.getint('threshold', 10)
        self.step_size = config.getfloat('step_size', 0.02, above=0.)
        self.precision_goal = config.getfloat('precision_goal', 0.002, above=0.)
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
        
    def _average_force(self):
        while True:
          force = 0.
          min_force = +1e6
          max_force = -1e6
          for i in range(0,3) :
            val = self.mcu_adc.read_current_value()
            force = force + val
            min_force = min(val,min_force)
            max_force = max(val,max_force)
            
          if max_force - min_force < 15:
            return force / 3

          logging.info("Unstable force reading, retrying...")
    
    def _lower_to_threshold(self):
        # Lower the tool head until the force threshold is exceeded
        logging.info("_lower_to_threshold force_offset = %d" % self.force_offset)
        while True:
          self._move_z_relative(-self.step_size)
          force = self._average_force() - self.force_offset
          logging.info("z = %f, force = %d" % (self.tool.get_position()[2], force))
          if(abs(force) > self.threshold):
            break

    def _fast_approach(self):
        # Strategy for fast approach: lower tool head until exceeding threshold, then lift head a bit and compare force
        # with original force_offset. If it matches, the contact is assumed. If not, the force_offset has drifed and
        # the search is continued with the new offset.
        logging.info("Commencing fast approach.")
        self.force_offset = self._average_force()
        while True:
          self._lower_to_threshold()
          self._move_z_relative(self.step_size*2)
          new_offset = self._average_force()
          self._move_z_relative(-self.step_size*2)
          logging.info("force_offset = %d, new_offset = %d" % (self.force_offset, new_offset))
          if(abs(new_offset-self.force_offset) < self.threshold):
            logging.info("Fast approach found contact.")
            return
          self.force_offset = new_offset
          logging.info("Continue search with new_offset.")

    def _iterative_search(self):
        # Strategy for iterative search: take series of measurements. If a measurement shows a force above the threshold
        # move tool head away from bed; if force is below threshold move head towards bed. Whenever the direction is
        # changed, reduce the stepsize by a factor of two. When two consecutive measurements go into same direction,
        # increase stepsize by factor of two (up to the start value of the step size used for the fast approach).
        # Each measurement point is compensated for the force offset. This is done by taking another measurement for
        # each point with the tool head moved further away from the bed.
        # This search is continued until the step size is below our precision goal.
        logging.info("Commencing iterative search.")
        current_step_size = +self.step_size   # sign determines direction
        while True:
          # take compensated measurement
          force_in = self._average_force()
          self._move_z_relative(self.step_size)
          force_out = self._average_force()
          force = force_in - force_out
          
          # log result
          logging.info("z = %f, step size %f, force = %d" % (self.tool.get_position()[2]-self.step_size, current_step_size, force))
          
          # decide next action
          if(abs(force) > self.threshold):
            # we have contact, need to move to positive Z
            if current_step_size > 0:
              # already moving to positive Z: increase step size
              current_step_size = min(self.step_size, 2*current_step_size)
            else :
              # previously moving to negative Z: decrease step size and change direction
              current_step_size = -current_step_size/2
          else :
            # we have no contact, need to move to negative Z
            if current_step_size < 0:
              # already moving to negative Z: increase step size
              current_step_size = min(self.step_size, 2*current_step_size)
            else :
              # previously moving to positive Z: decrease step size and change direction
              current_step_size = -current_step_size/2
          
          # check abort condition
          if abs(current_step_size) < self.precision_goal :
            logging.info("Search completed.")
            # return Z position before compensation step
            return self.tool.get_position()[2] - self.step_size

          # move to new position (incl. reverse compensation step)
          self._move_z_relative(-self.step_size + current_step_size)

    def run_probe(self, gcmd):
        self.tool = self.printer.lookup_object('toolhead')
        
        # wait until toolhead is in position
        self.tool.wait_moves()
        
        # fast, coarse approach
        self._fast_approach()
        
        # precise interative search
        result = self._iterative_search()

        logging.info("FINISHED z = %f" % result)
        return result

def load_config(config):
    probe = LoadCellProbe(config)
    config.printer.add_object('probe', probe)
    return probe
