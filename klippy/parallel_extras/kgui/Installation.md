Installation Guide
==================

##### This is still in development and may have bugs.

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

### Install Klipper with KGUI ###
```bash
cd ~

git clone --recurse-submodules https://github.com/D4SK/klipperui
./klipperui/scripts/install-kgui-x11.sh
```

- If you haven't flashed your printer-mainboards firmware yet follow [klipper/Installation.md](https://github.com/KevinOConnor/klipper/blob/master/docs/Installation.md) (Building and flashing the micro-controller)
- Move your printer configuration (printer.cfg) to /home/pi and add the necessary sections to activate the KGUI UI as seen here [klipper/config/sample-kgui.cfg](https://github.com/D4SK/klipperui/blob/master/config/sample-kgui.cfg)
- Change the resolution in the kivy config according to the screen you are using. (default is 1024x600) E.g. "height = 800" and "width = 480" ```nano ~/klipperui/klippy/parallel_extras/kgui/config.ini```
- If the UI appears upside down, rotate your screen. Alternatively you can change the rotation parameter of the kivy config from "rotation = 90" to "rotation = 270" ```nano ~/klipperui/klippy/parallel_extras/kgui/config.ini```

### Install cura_connection (recommended) ###
- Add the necessary config section ```[cura_connection]```
- Run the install script
```bash
~/klipperui/klippy/parallel_extras/cura_connection/install.sh
```


- Reboot ``` sudo reboot  ```
