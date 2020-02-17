Installation Guide
==================


### Prepare OS on Raspberry Pi 4
(raspberry pi 3 is not fast enough to run the UI properly and likely requires different GL driver settings  in kgui/\_\_init\_\_.py)
- flash [Raspian buster lite](https://www.raspberrypi.org/downloads/raspbian) image to SD-Card
- add new file named "ssh" (with no file extension) to the boot folder to enable ssh
- Boot your pi and run the following commands via SSH

```bash
sudo apt update
sudo raspi-config 
"""set memory split to 256,
   GL Driver to OpenGL FKMS, 
   Desktop/CLI to Console Autologin """ 
sudo apt install git python-pip virtualenv  
```

### Install Octoprint from source
- This is optional, Klipper can be used just with KGUI

```bash
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

- move your printer configuration (printer.cfg) to /home/pi  
- reboot
- connect OctoPrint to /tmp/printer using web interface  


---
  
  
  
## Manual Installation 
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
cd /usr/local/src/ && \
sudo git clone https://github.com/goodtft/LCD-show.git && \
sudo chmod -R 755 LCD-show && \
cd LCD-show/ && \
sudo ./LCD7C-show 90  
#reboots when finished  
#git clone https://github.com/D4SK/Klipper-GUI
```

opengl driver only works with autologin enabled and a reinstall of the lcd driver  

### Automount usb

[Link](https://raspberrypi.stackexchange.com/questions/66169/auto-mount-usb-stick-on-plug-in-without-uuid)  

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
