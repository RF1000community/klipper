Raspian buster lite without desktop env.

add new 'ssh' file with no extension to boot folder to enable ssh

sudo apt-get update

sudo raspi-config: memory split = 256, GL Driver, autologin

sudo apt-get install git python-pip virtualenv

### Octoprint from source
cd ~
git clone https://github.com/foosel/OctoPrint.git
cd OctoPrint/
virtualenv venv
./venv/bin/python setup.py install

#Autostart

wget https://github.com/foosel/OctoPrint/raw/master/scripts/octoprint.init && sudo mv octoprint.init /etc/init.d/octoprint
wget https://github.com/foosel/OctoPrint/raw/master/scripts/octoprint.default && sudo mv octoprint.default /etc/default/octoprint
sudo chmod +x /etc/init.d/octoprint

Adjust the paths to your octoprint binary in /etc/default/octoprint. If you set it up in a virtualenv as described above make sure your /etc/default/octoprint is modified like this:  
   DAEMON=/home/pi/OctoPrint/venv/bin/octoprint
sudo update-rc.d octoprint defaults.

https://community.octoprint.org/t/setting-up-octoprint-on-a-raspberry-pi-running-raspbian/2337

### Klipperui with KGUI
cd ~
git clone --recurse-submodules https://github.com/D4SK/klipperui
./klipperui/scripts/install-kgui.sh # this runs all the kgui and klipper installation 

#see install-kgui.sh and klippy-kgui-requirements.txt (where the pip packages are listed)

then put printer.cfg file in home folder















#git is for Klipper and LCD driver, pip and the rest is for Kivy maybe mtdev-tools is not needed

#evtl expand filesystem


### KGUI deps
sudo apt install --yes \
   git python-pip python-pygame libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
   pkg-config libgl1-mesa-dev libgles2-mesa-dev \
   python-setuptools libgstreamer1.0-dev git-core \
   gstreamer1.0-plugins-{bad,base,good,ugly} \
   gstreamer1.0-{omx,alsa} python-dev libmtdev-dev \
   xclip xsel libjpeg-dev mtdev-tools xorg python-pillow xserver-xorg-video-fbturbo \
   network-manager && \

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

### Automount usb
https://raspberrypi.stackexchange.com/questions/66169/auto-mount-usb-stick-on-plug-in-without-uuid


opengl driver only works with autologin enabled and a reinstall of the lcd driver


### NetworkManager

sudo apt install network-manager

sudo apt purge dhcpcd5

_maybe edit /etc/interfaces_



### Logs

Klipper: /tmp/klippy.log
Kivy:  ~/.kivy/logs
Xorg: /var/log/


/home/pi/klippy-env/bin/python      klippy executable
/usr/bin/startx                     xorg