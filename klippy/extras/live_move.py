# Simple module allowing for live-movement of axes, e.g. by pressing and holding a button
#
# Copyright (C) 2020  Konstantin Vogel <konstantin.vogel@gmx.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

class LiveMove:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = config.get_reactor()
        self.toolhead = self.printer.objects['toolhead']
        self.move_completion = {}

    def _fill_coord(self, new_pos):
        """ Fill in any None entries in 'new_pos' with current toolhead position """
        pos = list(self.toolhead.get_position())
        for i, new in enumerate(new_pos):
            if new is not None:
                pos[i] = new
        return pos

    def toolhead_busy(self):
        print_time, est_print_time, lookahead_empty = self.toolhead.check_busy(self.reactor.monotonic())
        idle_time = est_print_time - print_time
        return bool(not lookahead_empty or idle_time <= 0)

    def start_move(self, axis, direction):
        if not toolhead_busy(self.reactor.monotonic()):
            if axis in "xyz":
                kin_status = self.toolhead.kin.get_status(self.reactor.monotonic())
                self.move_completion[axis] = ReactorCompletion(self.reactor)
                pos = self.toolhead.get_position()
                if axis in kin_status['homed_axes']:
                    pos[2] = (self.pos_max['z'] if up else self.pos_min['z'])
                else:
                    pos[2] += (self.pos_max['z'] - self.pos_min['z']) * direction

                self.toolhead.flush_step_generation()
                kin = self.toolhead.get_kinematics()
                steppers = kin.get_steppers()

                for s in steppers:
                    s.set_tag_position(s.get_commanded_position())

                self.start_mcu_pos[axis] = [(s, s.get_mcu_position()) for s in steppers]
                self.toolhead.dwell(0.050)
                self.toolhead.drip_move(pos, self.z_speed, self.z_move_completion, force=True)

    def stop_move(self, axis):
        if axis in self.move_completion.keys() and self.move_completion[axis] != None:
            # this works similar to homing.py
            self.move_completion['axis'].complete(self.reactor, True)
            self.reactor.pause(self.reactor.monotonic() + 0.200)
            #self.reactor.pause(self.reactor.NOW)
            self.toolhead.flush_step_generation()
            #                   v--start_pos     v--end_pos
            end_mcu_pos = [(s, spos, s.get_mcu_position()) for s, spos in self.start_mcu_pos[axis]]
            for s, spos, epos in end_mcu_pos:
                md = (epos - spos) * s.get_step_dist()
                s.set_tag_position(s.get_tag_position() + md)
            self.toolhead.set_position(self._fill_coord(self.toolhead.get_kinematics().calc_tag_position()))

def load_config(config):
    return LiveMove(config)