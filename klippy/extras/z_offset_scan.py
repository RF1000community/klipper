# Allow to re-level the bed mesh by measuring a single point
#
# Copyright (C) 2020  Martin Hierholzer <martin@hierholzer.info>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging, time

class ZOffsetScan:
    def __init__(self, config):
        self.name = config.get_name()
        self.printer = config.get_printer()

        self.speed = config.getfloat('speed', 5., above=0.)

        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command('Z_OFFSET_SCAN',
            self.cmd_Z_OFFSET_SCAN,
            desc=self.cmd_Z_OFFSET_SCAN_help)

        self.z_offset = config.getfloat('z_offset', 0.)

        # Register transform
        gcode_move = self.printer.load_object(config, 'gcode_move')
        self.normal_transform = gcode_move.set_move_transform(self, force=True)

    cmd_Z_OFFSET_SCAN_help = "Re-level bed mesh by re-measuring a " \
                                "single point"

    def cmd_Z_OFFSET_SCAN(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        probe = self.printer.lookup_object('probe')
        bed_mesh = self.printer.lookup_object('bed_mesh')
        configfile = self.printer.lookup_object('configfile')

        # perform probe measurement
        result = probe.run_probe(gcmd)
        self.z_offset = result[2]

        # obtain current position
        x, y, z, e = toolhead.get_position()

        # subtract bed mesh value at the measurement position (otherwise we get
        # the bed mesh correction twice)
        corr = bed_mesh.get_mesh().calc_z(x,y) + bed_mesh.get_mesh().mesh_offset
        self.z_offset -= corr

        # update config file
        configfile.set(self.name, 'z_offset', self.z_offset)
        gcmd.respond_info("New z_offset: %f\n"
                  "The SAVE_CONFIG command will update the printer config\n"
                  "file and restart the printer" % (self.z_offset))

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
