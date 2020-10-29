Installation Guide
==================

##### This is still in development and may have bugs. (see bugs in TODO.txt) #####

### Requirements
* Raspberry pi 4 (raspberry pi 3 is not fast enough to meet real time requirements of Klipper with the added load, and likely requires different GL driver settings  in kgui/\_\_init\_\_.py)
* 7" LCD Touch screen with 1024\*600 resolution (lower resolutions are not supported at the moment)
These screens can be purchased for around 35$ on [Aliexpress](https://s.click.aliexpress.com/e/_d78tnDk), Ebay, or Banggood. 
Make sure to get one with an IPS panel (much better image quality)

### Prepare OS

- flash [Raspian buster lite 2020-05-27](https://www.raspberrypi.org/downloads/raspbian) to SD-Card
- add new file named "ssh" (with no file extension) to the boot folder to enable ssh
- Boot your pi and run the following commands via SSH

```bash
sudo apt update
sudo apt install git
sudo raspi-config
```
- Set following settings:
   - Advanced Options -> Memory Split to `256`
   - Advanced Options -> GL Driver to `GL (Fake KMS)`
   - Boot Options -> Desktop/CLI to `Console Autologin`
   - Interfacing Options -> Camera to `enabled` (If you plan to use a raspi-cam)

### Install Octoprint if required <br> (it is recommended to use the [klipper_cura_connection](https://github.com/Gobbel2000/klipper_cura_connection) plugin instead of a webinterface)
```bash
sudo apt install virtualenv  
cd
git clone https://github.com/foosel/OctoPrint.git
cd Octoprint/
virtualenv venv  
./venv/bin/python setup.py install

sudo cp ./scripts/octoprint.service /etc/systemd/system/octoprint.service
sudo systemctl daemon-reload
sudo systemctl enable octoprint
#sudo journalctl -u octoprint
```

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
