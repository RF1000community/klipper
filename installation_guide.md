Raspian buster lite without desktop env.

add new 'ssh' file with no extension to boot folder to enable ssh

sudo apt-get update
sudo apt-get upgrade # to get new mesa gl driver, maybe not needed later

sudo raspi-config: memory split = 256, GL Driver, autologin

sudo apt-get install git python-pip virtualenv

### Octoprint
cd ~
git clone https://github.com/foosel/OctoPrint.git
cd OctoPrint/
virtualenv venv
./venv/bin/python setup.py install

### Klipperui with KGUI

git clone https://github.com/KevinOConnor/klipper
./klipper/scripts/install-kgui.sh

















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

sudo apt purge dhcpcd5 --yes && \

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


opengl driver only works with autologin enabled and a reinstall of the lcd driver


### NetworkManager

sudo apt install network-manager

sudo apt purge dhcpcd5

_maybe edit /etc/interfaces_
