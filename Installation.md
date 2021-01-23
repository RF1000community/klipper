Installation Guide
==================

##### This is still in development and may have bugs. (see bugs in TODO.txt) #####

### Requirements
* Raspberry pi 4 (raspberry pi 3 is not fast enough to meet real time requirements of Klipper with the added load, and likely requires different GL driver settings  in kgui/\_\_init\_\_.py)
* 7" LCD Touch screen with 1024\*600 resolution (lower resolutions are not supported at the moment)
These screens can be purchased for around 35$ on [Aliexpress](https://s.click.aliexpress.com/e/_d78tnDk), Ebay, or Banggood. 
Make sure to get one with an IPS panel (much better image quality)

### Prepare OS

- flash [Raspian buster lite](https://www.raspberrypi.org/downloads/raspbian) 2021-01-11 to SD-Card
- add new file named "ssh" (with no file extension) to the boot folder to enable ssh
- Boot your pi and run the following commands via SSH

```bash
sudo apt update
sudo apt install git
sudo raspi-config
```
- Set following settings:
   - Performance Options -> GPU Memory to `256`
   - Advanced Options -> GL Driver to `GL (Fake KMS)`
   - System Options -> Boot / Auto Login to `Console Autologin`
   - Interface Options -> Camera to `enabled` (If you plan to use a raspi-cam)
   - Localisation Options -> Locale to `en_GB.UTF8 UTF-8`
- (If the Pi fails to boot, try briefly disconnecting the printer mainboards' USB cable)

### Install Klipper with KGUI

```bash
cd ~

git clone --recurse-submodules https://github.com/D4SK/klipperui
./klipperui/scripts/install-kgui.sh
```

- if you haven't flashed your printer-mainboards' firmware yet follow [klipper/Installation.md](https://github.com/KevinOConnor/klipper/blob/master/docs/Installation.md) (Building and flashing the micro-controller)
- move your printer configuration (printer.cfg) to /home/pi and add the necessary sections to activate the KGUI UI as seen here [klipper/config/sample-kgui.cfg](https://github.com/D4SK/klipperui/blob/master/config/sample-kgui.cfg)
- reboot ``` sudo reboot  ```
- done !
