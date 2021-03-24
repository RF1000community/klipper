
# This is where functions turn themselves into a pickle
# They wander off to processes far away
# They do what needs to be done

import logging

def set_attribute(e, root, property_name, val):
    logging.info(f"set attribute {property_name} to {val}")
    setattr(root, property_name, val)

######################################################################
# Tuning
######################################################################

def reset_tuning(e, printer):
    send_flow(e, printer, 100)
    send_speed(e, printer, 100)
    send_z_offset(e, printer, 0)
    send_fan(e, printer, 0)
    send_acceleration(e, printer, printer.config.getsection('printer').getfloat('max_accel', above=0.))
    reset_pressure_advance(e, printer)
    update(e, printer)

def get_z_offset(e, printer):
    z_offset = printer.objects['gcode_move'].homing_position[2]
    printer.reactor.cb(set_attribute, 'z_offset', z_offset, process='kgui')
def send_z_offset(e, printer, z_offset):
    printer.objects['gcode'].run_script_from_command(f"SET_GCODE_OFFSET Z={z_offset} MOVE=1 MOVE_SPEED=5")
    get_z_offset(e, printer)

def get_speed(e, printer):
    speed = printer.objects['gcode_move'].speed_factor*60*100 #speed factor also converts from mm/sec to mm/min
    printer.reactor.cb(set_attribute, 'speed', speed, process='kgui')
def send_speed(e, printer, val):
    val = val/(60.*100.)
    printer.objects['gcode_move'].speed = rinter.objects['gcode_move']._get_gcode_speed() * val
    printer.objects['gcode_move'].speed_factor = val
    get_speed(e, printer)

def get_flow(e, printer):
    flow = printer.objects['gcode_move'].extrude_factor*100
    printer.reactor.cb(set_attribute, 'flow', flow, process='kgui')
def send_flow(e, printer, val):
    new_extrude_factor = val/100.
    gcode_move = printer.objects['gcode_move']
    last_e_pos = gcode_move.last_position[3]
    e_value = (last_e_pos - gcode_move.base_position[3]) / gcode_move.extrude_factor
    gcode_move.base_position[3] = last_e_pos - e_value * new_extrude_factor
    gcode_move.extrude_factor = new_extrude_factor
    get_flow(e, printer)

def get_fan(e, printer):
    fan_speed = printer.objects['fan'].fan.last_fan_value * 100 / printer.objects['fan'].fan.max_power
    printer.reactor.cb(set_attribute, 'fan_speed', fan_speed, process='kgui')
def send_fan(e, printer, speed):
    printer.objects['fan'].fan.set_speed_from_command(speed/100)
    get_fan(e, printer)

def get_pressure_advance(e, printer): # gives pressure_advance value of 1. extruder
    pressure_advance = printer.objects['extruder'].get_status(e)['pressure_advance']
    printer.reactor.cb(set_attribute, 'pressure_advance', pressure_advance, process='kgui')
def send_pressure_advance(e, printer, val):
    for i in range(10):
        extruder_id = f"extruder{'' if i==0 else i}"
        if extruder_id in printer.objects:
            printer.objects[extruder_id]._set_pressure_advance(
                val, printer.objects[extruder_id].pressure_advance_smooth_time)
        else:
            break
    get_pressure_advance(e, printer)
def reset_pressure_advance(e, printer):
    for i in range(10):
        extruder_id = f"extruder{'' if i==0 else i}"
        if extruder_id in printer.objects:
            extruder = printer.objects[extruder_id]
            pa = printer.config.getsection(extruder.name).getfloat('pressure_advance', 0., minval=0.)
            extruder._set_pressure_advance(pa, extruder.pressure_advance_smooth_time)

def get_acceleration(e, printer):
    acceleration = printer.objects['toolhead'].max_accel
    printer.reactor.cb(set_attribute, 'acceleration', acceleration, process='kgui')
# with dynamic acceleration control (M204) this becomes useless (sets limit)
def send_acceleration(e, printer, val):
    printer.objects['toolhead'].max_accel = val
    printer.objects['toolhead']._calc_junction_deviation()
    get_acceleration(e, printer)

######################################################################
# Other Commands
######################################################################

def update(e, printer):
    get_toolhead_busy(e, printer)
    get_homing_state(e, printer)
    get_pos(e, printer)
    get_pressure_advance(e, printer)
    get_acceleration(e, printer)
    get_z_offset(e, printer)
    get_speed(e, printer)
    get_flow(e, printer)
    get_temp(e, printer)
    get_fan(e, printer)

def write_config(e, printer, section, option, value):
    logging.info(f"trying to write config section: {section} option: {option}, value: {value}")
    printer.objects['configfile'].set(section, option, value)
    printer.objects['configfile'].cmd_SAVE_CONFIG(None)

def write_pressure_advance(e, printer, value, extruder_count):
    for i in range(extruder_count):
        printer.objects['configfile'].set(f"extruder{'' if i==0 else i}", "pressure_advance", value)
    printer.objects['configfile'].cmd_SAVE_CONFIG(None)

def get_temp(e, printer):
    if 'heaters' in printer.objects:
        temp = {}
        for name, heater in printer.objects['heaters'].heaters.items():
            current, target = heater.get_temp(e)
            temp[name] = [target, current]
        printer.reactor.cb(set_attribute, 'temp', temp, process='kgui')
def send_temp(e, printer, temp, extruder_id):
    printer.objects['heaters'].heaters[extruder_id].set_temp(temp)
    get_temp(e, printer)

def get_homing_state(e, printer):
    kin_status = printer.objects['toolhead'].kin.get_status(e)
    homed = {axis: bool(axis in kin_status['homed_axes']) for axis in "xyz"}
    printer.reactor.cb(set_attribute, 'homed', homed, process='kgui')
def send_home(e, printer, axis):
    printer.objects['gcode'].run_script_from_command("G28" + axis.upper())

def send_motors_off(e, printer):
    printer.objects['gcode'].run_script_from_command("M18")

def get_toolhead_busy(e, printer):
    print_time, est_print_time, lookahead_empty = printer.objects['toolhead'].check_busy(e)
    idle_time = est_print_time - print_time
    busy = bool(not lookahead_empty or idle_time <= 0)
    printer.reactor.cb(set_attribute, 'toolhead_busy', busy, process='kgui')
    return busy

def get_pos(e, printer):
    pos = printer.objects['toolhead'].get_position()
    printer.reactor.cb(set_attribute, 'pos', pos, process='kgui')
def send_pos(e, printer, x=None, y=None, z=None, speed=15):
    new_pos = [x,y,z,e]
    homed_axes = printer.objects['toolhead'].get_status(e)['homed_axes']
    # check whether axes are still homed
    new_pos = [new if name in homed_axes else None for new, name in zip(new_pos, 'xyze')]
    new_pos = _fill_coord(printer, new_pos)
    printer.objects['toolhead'].move(new_pos, speed)
    get_pos(e, printer)

def _fill_coord(printer, new_pos):
    """ Fill in any None entries in 'new_pos' with current toolhead position """
    pos = list(printer.objects['toolhead'].get_position())
    for i, new in enumerate(new_pos):
        if new is not None:
            pos[i] = new
    return pos




def send_calibrate(e, printer):
    printer.objects['bed_mesh'].calibrate.cmd_BED_MESH_CALIBRATE(None)

def send_print(e, printer, filepath):
    printer.objects['virtual_sdcard'].add_printjob(filepath)

def send_stop(e, printer):
    printer.objects['virtual_sdcard'].stop_printjob()

def send_pause(e, printer):
    printer.objects['virtual_sdcard'].pause_printjob()

def send_resume(e, printer):
    printer.sdcard.resume_printjob()

def restart(e, printer):
    printer.request_exit('restart')

def firmware_restart(e, printer):
    printer.request_exit('firmware_restart')

def quit(e, printer):
    """Stop klipper and GUI, returns to tty"""
    printer.request_exit('exit')
