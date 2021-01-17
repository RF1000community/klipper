# Correct Z offset for first layer for thermal elongation of the hotend, based
# on the required extrusion force measured by the load cell probe. Requires
# to enable the load_cell_probe module.
#
# Copyright (C) 2020 Martin Hierholzer <martin@hierholzer.info>
#
# Based on the implementation by Nibbles/Wessix on:
# https://github.com/RF1000community/Repetier-Firmware
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging, time

class SensingZOffset:
    def __init__(self, config):
        self.name = config.get_name()
        self.printer = config.get_printer()
        self.printer.register_event_handler("klippy:ready", self._handle_ready)

        self.force_threshold = config.getint('force_threshold', minval=1.)
        self.force_threshold_default = self.force_threshold
        self.max_z_offset = config.getfloat('max_z_offset', above=0.)
        self.max_z_offset_default = self.max_z_offset
        self.max_z_height = config.getfloat('max_z_height', 0.33, above=0.)
        self.n_average_force = config.getint('n_average_force', 10, minval=1)
        self.smoothing = config.getfloat('smoothing', 0.5, minval=0.,
            maxval=0.99)
        self.step_size = config.getfloat('step_size', 0.001, above=0.)
        self.relative_tolerance = config.getfloat('relative_tolerance', 0.1,
            above=0.)
        self.acuteness = config.getfloat('acuteness', 24., above=0.)
        self.max_steps_at_once = config.getfloat('max_steps_at_once', 48.,
            above=0.)

        self.load_cell = self.printer.lookup_object('load_cell')
        self.load_cell.subscribe_force(self.force_callback)

        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command('Z_SENSE_OFFSET',
            self.Z_SENSE_OFFSET,
            desc=self.cmd_Z_SENSE_OFFSET_help)

        self.z_offset = 0.
        self.force_offset = 0
        self.force_offset_valid = False
        self.last_force = 0.
        self.averaged_force = 0.
        self.i_average = 0
        self.enable = False

        # Register transform
        gcode_move = self.printer.load_object(config, 'gcode_move')
        self.normal_transform = gcode_move.set_move_transform(self, force=True)

        # Reset z offset and force offset when homing Z axis
        self.printer.register_event_handler("homing:home_rails_end",
                                            self._handle_home_rails_end)


    cmd_Z_SENSE_OFFSET_help = "Increase Z offset depending on measured " \
            "extrusion pressure"

    def Z_SENSE_OFFSET(self, gcmd):
        self.max_z_offset = gcmd.get_float("MAX_Z_OFFSET",
            self.max_z_offset_default, minval=0.)
        self.force_threshold = gcmd.get_int("FORCE_THRESHOLD",
            self.force_threshold_default, minval=0)
        self.z_offset = 0.
        self.enable = True

    def _handle_ready(self):
        self.tool = self.printer.lookup_object('toolhead')
        self.enable = False

    def _handle_home_rails_end(self, homing_state, rails):
        self.force_offset_valid = False
        self.z_offset = 0.
        self.enable = False

    def get_position(self):
        x, y, z, e = self.normal_transform.get_position()
        return [x, y, z-self.z_offset, e]

    def move(self, newpos, speed):
        x, y, z, e = newpos
        self.normal_transform.move([x, y, z+self.z_offset, e], speed)

    def force_callback(self, force) :
        # store idle force
        if not self.force_offset_valid :
          self.force_offset = force
          self.force_offset_valid = True

        # check if enabled
        if not self.enable :
          return

        # check if still in first layer
        if self.tool.get_position()[2] > self.max_z_height:
          return

        # perform averaging with some smoothing
        self.averaged_force += force - self.force_offset
        self.i_average += 1
        if self.i_average < self.n_average_force :
          return
        smoothed_force = abs(self.averaged_force)/self.n_average_force
        logging.info("smoothed_force = %d" % smoothed_force)
        self.averaged_force *= self.smoothing
        self.i_average *= self.smoothing

        # no action required if below threshold
        if smoothed_force < self.force_threshold:
          self.last_force = smoothed_force
          return

        # check of extra tolerance is also exceeded
        exceed_tolerance = False
        if smoothed_force > self.force_threshold*(1+self.relative_tolerance) :
          exceed_tolerance = True

        # determine number of steps (of size self.step_size) to be done
        # start with default of 1
        n_steps = 1

        if exceed_tolerance and smoothed_force >= self.last_force:
          # larger and increasing deviations require faster action
          ratio = smoothed_force / self.force_threshold - 1
          n_steps += min(ratio * self.acuteness, self.max_steps_at_once)

          # the more offset we have already applied, the slower the additional
          # offset needs to be applied (to prevent overshooting)
          ratio = self.z_offset / self.max_z_offset
          n_steps -= (n_steps-1)*ratio

        if not exceed_tolerance and smoothed_force < self.last_force:
          # small and decreasing devation does not require any action
          n_steps = 0

        # apply offset
        self.z_offset = min(self.z_offset + n_steps*self.step_size,
            self.max_z_offset)

        logging.info("n_steps = %d  z_offset = %f" % (n_steps, self.z_offset) )


def load_config(config):
    return SensingZOffset(config)
