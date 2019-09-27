#!/bin/bash

sudo apt-get update
sudo apt-get upgrade

sudo apt install --yes \
   git python-pip python-pygame libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
   pkg-config libgl1-mesa-dev libgles2-mesa-dev \
   python-setuptools libgstreamer1.0-dev git-core \
   gstreamer1.0-plugins-{bad,base,good,ugly} \
   gstreamer1.0-{omx,alsa} python-dev libmtdev-dev \
   xclip xsel libjpeg-dev mtdev-tools xorg python-pillow xserver-xorg-video-fbturbo network-manager
sudo apt purge dhcpcd5 --yes
python -m pip install --upgrade --user pip
python -m pip install --upgrade --user Cython==0.29.10
python -m pip install --user kivy==1.11.0
cd /usr/local/src/
sudo git clone https://github.com/goodtft/LCD-show.git
sudo chmod -R 755 LCD-show
cd LCD-show/
sudo ./LCD7C-show 90 
