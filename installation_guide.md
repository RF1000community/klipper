Installation Guide
==================

##### this is still in development, works except connecting to a printer or homing moves fail sometimes with a "Timer too close" error additionally the kivy master branch has to be installed manually e.g. from precompiled wheel because it includes necessary fixes for the raspberry pi #####

### Requirements
* Raspberry pi 4 (raspberry pi 3 is not fast enough to run the UI properly and likely requires different GL driver settings  in kgui/\_\_init\_\_.py)
* 7 inch LCD Touch screen with 1024\*600 resolution (lower resolutions are not supported at the moment)
These screens can be purchased for around 35$ on [Aliexpress](https://de.aliexpress.com/item/4000375954941.html?spm=a2g0x.12010612.8148356.46.7c802eb8VaLawi), Ebay, or [Banggood](https://www.banggood.com/de/7-Inch-Full-View-LCD-IPS-Touch-Screen-1024+600-800+480-HD-HDMI-Display-Monitor-for-Raspberry-Pi-p-1633584.html?rmmds=search&ID=514816&cur_warehouse=CN). Make sure to get one with an IPS panel, and 1024\*600 resolution.

### Prepare OS

- flash [Raspian buster lite 2020-02-13](https://www.raspberrypi.org/downloads/raspbian) to SD-Card
- add new file named "ssh" (with no file extension) to the boot folder to enable ssh
- Boot your pi and run the following commands via SSH

```bash
sudo apt update
sudo apt install git
sudo raspi-config
"""set memory split to 256,
   GL Driver to Legacy, 
   Desktop/CLI to Console Autologin """ 
```

### Install Octoprint if required <br> (it is recommended to just use the klipper-cura plugin instead of any webinterface)
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

- move your printer configuration (printer.cfg) to /home/pi (make sure it includes sections from /config/sample-kgui.cfg)
- reboot ``` sudo reboot  ```
- done !

---
  
  
  
## Manual Installation and Debugging Notes (incomplete)
#### KGUI deps

Execute klipperui/scripts/install-kgui.sh or:

```bash
sudo apt install --yes \ 
   git python-pip python-pygame libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
   pkg-config libgl1-mesa-dev libgles2-mesa-dev \
   python-setuptools libgstreamer1.0-dev git-core \
   gstreamer1.0-plugins-{bad,base,good,ugly} \
   gstreamer1.0-{omx,alsa} python-dev libmtdev-dev \
   xclip xsel libjpeg-dev mtdev-tools xorg python-pillow xserver-xorg-video-fbturbo \
   network-manager && \

#git is for Klipper and LCD driver, pip and the rest is for Kivy 
#maybe mtdev-tools is not needed  

sudo apt purge dhcpcd5 && \

python -m pip install --upgrade --user pip  && \
python -m pip install --upgrade --user Cython==0.29.10  && \
python -m pip install --user kivy==1.11.0 && \

sudo ./LCDC7-better.sh -r 90 && \
sudo cp 10-dpms.conf /etc/X11/xorg.conf.d/

#git clone https://github.com/D4SK/Klipper-GUI
```

opengl driver only works with autologin enabled and a reinstall of the lcd driver  

### Automount usb

[Link](https://raspberrypi.stackexchange.com/questions/66169/auto-mount-usb-stick-on-plug-in-without-uuid)  

```bash
sudo apt install usbmount
sudo cp usbmount.conf /etc/usbmount/
sudo sed -i 's/PrivateMounts=yes/PrivateMounts=no/' /lib/systemd/system/systemd-udevd.service
```

### NetworkManager

```bash
sudo apt install network-manager  
sudo apt purge dhcpcd5  
```

### Boot optimizations

add `quiet disable_splash=1` to /boot/cmdline.txt  

### Logs

Klipper: /tmp/klippy.log  
Kivy:  ~/.kivy/logs  
Xorg: /var/log/  


### Shutdown without needing to provide password

```bash
sudo echo "%sudo ALL=(ALL) NOPASSWD: /bin/systemctl" >> /etc/sudoers
```

### Klipper microcontroller flashing

For use of the gtk configuration GUI a basic gtk installation must be available:

`sudo apt install libgtk2.0-dev libglade2-dev libglib2.0-dev`

Then from the klipperui directory execute
`make gconfig`
with a running X session.

/home/pi/klippy-env/bin/python      klippy executable  
/usr/bin/startx                     xorg
