Additional Installation Steps for Klippo
==================


### Requirements ###
* Raspberry pi 4 (raspberry pi 3 is not tested, and may require different GL driver settings in kgui/\_\_init\_\_.py)
* One of the supported touchscreens:
   - Official Raspberry pi 7" touchscreen 800x480
   - Chinese 7" 1024x600 touchscreens. These screens can be purchased for around 35$ on Aliexpress, Ebay, or Banggood. Make sure to get one with an IPS panel (much better image quality)

### Prepare OS ###
- Flash [Raspberry Pi OS lite](https://www.raspberrypi.org/software/operating-systems/) 2021-01-11 to SD-Card
- Add new file named "ssh" (with no file extension) to the boot folder to enable ssh
- Boot your pi and run the following commands via SSH
- An ethernet connection is currently necessary during the installation (installing wifi dependencies disconnects any wifi connection, terminating the ssh session)

```bash
sudo apt update
sudo apt install git
sudo raspi-config
```
- Set following raspi-config options:
   - Advanced Options -> GL Driver to `GL (Fake KMS)` (confirm installation of additional drivers with Y)
   - System Options -> Boot / Auto Login to `Console Autologin`
   - Interface Options -> Camera to `enabled` (If you plan to use a raspi-cam)
   - Localisation Options -> Locale: Add your local Locale (UTF8 version) as well as `en_GB.UTF8 UTF-8` by selecting with the spacebar, confirm and set `en_GB.UTF8 UTF-8` as default.
- (If the Pi fails to boot, try briefly disconnecting the printer mainboards USB cable)

### Install Klippo ###
```bash
cd ~

git clone https://github.com/D4SK/klippo
./klippo/scripts/install-klippo-x11.sh
```

- If you haven't flashed your printer-mainboards firmware yet follow [klipper/Installation.md](https://github.com/D4SK/klippo/blob/master/docs/Installation.md) (Building and flashing the micro-controller)
- Move your printer configuration (printer.cfg) to /home/pi and add the necessary sections to activate the KGUI UI
- Change the resolution in the kivy config according to the screen you are using. (default is 1024x600) E.g. "height = 800" and "width = 480" ```nano ~/klippo/klippy/parallel_extras/kgui/config.ini```
- If the UI appears upside down, rotate your screen. Alternatively you can change the rotation parameter of the kivy config from "rotation = 90" to "rotation = 270" ```nano ~/klippo/klippy/parallel_extras/kgui/config.ini```

### Install cura_connection (recommended) ###
- Add the necessary config section ```[cura_connection]```
- Run the install script
```bash
~/klippo/klippy/parallel_extras/cura_connection/install.sh
```


- Reboot ``` sudo reboot  ```


### Additional Config Sections ###
```bash

# (needed)
[virtual_sdcard]

# (optional) allow continuous printing
[collision]
printhead_x_min: 80
printhead_x_max: 80
printhead_y_min: 80
printhead_y_max: 80
gantry_xy_min: 90
gantry_xy_max: 90
gantry_z_min: 40
gantry_orientation: y
padding: 2
continuous_printing: True
reposition: False
condition: any # exact | type | any

# The Filament Manager provides automatic material loading and unloading, and tracking of material usage and type.
# This module works together with the cura_connection plugin
[filament_manager]

# (recommended) This module allows controlling your printer from cura within the local network
[cura_connection]

# Main UI module 
# set [stepper_z] to allow for at least 0.5mm of additional movement
[kgui]
# Set this to True if the Z-Axis is moving the printbed and not the printhead (e.g. for Ultimaker style printers)
invert_z_controls: False


# Provide these Gcode macros when using filament_manager.
# The FORCE parameter is needed for all G1 moves to 
# avoid "Extrude below minimum temp" and "Extrude only move too long" errors.
# This is an example for a bowden printer with 600mm tube length.
[gcode_macro UNLOAD_FILAMENT]
gcode:
    SAVE_GCODE_STATE NAME=UNLOAD_STATE ; Store previoius gcode state
    M83 ; use relative extrusion mode
    M109 S{params.TEMPERATURE} ; set temperature and wait
    G1 E-60 F5 FORCE ; slowly retract from nozzle
    M400 ; wait until move is done
    M104 S0 ; switch off heater
    G1 E-700 F50 FORCE ; pull filament out of bowden tube
    RESTORE_GCODE_STATE NAME=UNLOAD_STATE
    M400 ; wait till everything is done

[gcode_macro LOAD_FILAMENT]
gcode:
    SAVE_GCODE_STATE NAME=LOAD_STATE
    M83
    M104 S{params.TEMPERATURE} ; set temperature and don't wait
    G1 E30 F5 FORCE  ; slowly grab the filament
    G1 E600 F50 FORCE ; quickly move filament through bowden tube (needs to be at least this length!)
    M109 S{params.TEMPERATURE} ; set temperature and wait
    G1 E100 F5 FORCE ; prime nozzle
    RESTORE_GCODE_STATE NAME=LOAD_STATE
    M400
    M104 S0
```
