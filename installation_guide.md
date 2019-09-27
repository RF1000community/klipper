Raspian buster lite without desktop env.

add new 'ssh' file with no extension to boot folder to enable ssh

#git is for Klipper and LCD driver, pip and the rest is for Kivy maybe mtdev-tools is not needed

evtl expand filesystem



sudo apt install --yes \
   git python3-pip python3-pygame libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
   pkg-config libgl1-mesa-dev libgles2-mesa-dev \
   python3-setuptools libgstreamer1.0-dev git-core \
   gstreamer1.0-plugins-{bad,base,good,ugly} \
   gstreamer1.0-{omx,alsa} python3-dev libmtdev-dev \
   xclip xsel libjpeg-dev mtdev-tools xorg python3-pillow xserver-xorg-video-fbturbo
#maybe install lcd driver first and not fbturbo
python3 -m pip install --upgrade --user pip
python3 -m pip install --upgrade --user Cython==0.29.10
python3 -m pip install --user kivy==1.11.0
#uses pypi as source



sudo apt-get update
sudo apt-get upgrade
sudo raspi-config: memory split = 256, GL Driver, autologin

sudo apt install --yes \
   git python-pip python-pygame libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
   pkg-config libgl1-mesa-dev libgles2-mesa-dev \
   python-setuptools libgstreamer1.0-dev git-core \
   gstreamer1.0-plugins-{bad,base,good,ugly} \
   gstreamer1.0-{omx,alsa} python-dev libmtdev-dev \
   xclip xsel libjpeg-dev mtdev-tools xorg python-pillow xserver-xorg-video-fbturbo network-manager && \
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




#backend gl oder sdl2
#window egl rpi
#python3
#evtl rpi-update

opengl driver only works with autologin enabled and a reinstall of the lcd driver
backend gl oder sdl2
window egl rpi
python3


### NetworkManager

sudo apt install network-manager

sudo apt purge dhcpcd5

_maybe edit /etc/interfaces_
