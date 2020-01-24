Installation Guide
==================


### Raspberry Pi 4

[Raspian buster lite](https://www.raspberrypi.org/downloads/raspbian) without desktop env.  
add new 'ssh' file with no extension to boot folder to enable ssh  

```bash
sudo apt update
sudo raspi-config #memory split = 256, GL Driver, autologin  
sudo apt install git python-pip virtualenv  
```

### Octoprint from source

```bash
cd
git clone https://github.com/foosel/OctoPrint.git
cd OctoPrint/
virtualenv venv  
./venv/bin/python setup.py install

sudo cp ./scripts/octoprint.service /etc/systemd/system/octoprint.service
sudo systemctl daemon-reload
sudo systemctl enable octoprint
#sudo journalctl -u octoprint
```

### Klipperui with KGUI

```bash
cd ~

git clone --recurse-submodules https://github.com/D4SK/klipperui
./klipperui/scripts/install-kgui-systemd.sh
```

put printer.cfg file in home folder  
connect OctoPrint to /tmp/printer using web interface  


---
  
  
  
  
### KGUI deps

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
