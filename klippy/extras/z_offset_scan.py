# Allow to re-level the bed mesh by measuring a single point
#
# Copyright (C) 2020  Martin Hierholzer <martin@hierholzer.info>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging, time

class ZOffsetScan:
    def __init__(self, config):
        self.printer = config.get_printer()

        self.horizontal_move_z = config.getfloat('horizontal_move_z', 5.)
        self.speed = config.getfloat('speed', 5., above=0.)

        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command('Z_OFFSET_SCAN',
            self.cmd_BED_MESH_RELEVEL,
            desc=self.cmd_BED_MESH_RELEVEL_help)

        self.z_offset = 0.0

        # Register transform
        gcode_move = self.printer.load_object(config, 'gcode_move')
        self.normal_transform = gcode_move.set_move_transform(self, force=True)

    cmd_BED_MESH_RELEVEL_help = "Re-level bed mesh by re-measuring a single point"

    def cmd_BED_MESH_RELEVEL(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        probe = self.printer.lookup_object('probe')
        bed_mesh = self.printer.lookup_object('bed_mesh')

        # perform probe measurement
        result = probe.run_probe(gcmd)
        self.z_offset = result[2]

        # obtain current position
        x, y, z, e = toolhead.get_position()

        # subtract bed mesh value at the measurement position (otherwise we get the bed mesh correction twice)
        corr = bed_mesh.get_mesh().calc_z(x,y) + bed_mesh.get_mesh().mesh_offset
        gcmd.respond_info("corr = %f, z_offset = %f" % (corr, self.z_offset))
        self.z_offset -= corr

        # lift toolhead
        toolhead.move([x, y, z+5, e], self.speed)

    def get_position(self):
        x, y, z, e = self.normal_transform.get_position()
        return [x, y, z-self.z_offset, e]

    def move(self, newpos, speed):
        x, y, z, e = newpos
        self.normal_transform.move([x, y, z+self.z_offset, e], speed)


def load_config(config):
    probe = ZOffsetScan(config)
    return probe
