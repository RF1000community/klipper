Raspian buster lite without desktop env.

add new 'ssh' file with no extension to boot folder to enable ssh

sudo apt update

#git is for Klipper and LCD driver, pip and the rest is for Kivy
sudo apt install --yes \
   git python-pip python-pygame libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
   pkg-config libgl1-mesa-dev libgles2-mesa-dev \
   python-setuptools libgstreamer1.0-dev git-core \
   gstreamer1.0-plugins-{bad,base,good,ugly} \
   gstreamer1.0-{omx,alsa} python-dev libmtdev-dev \
   xclip xsel libjpeg-dev
mtdev-tools??
python -m pip install --upgrade --user pip
python -m pip install --upgrade --user setuptools
python -m pip install --upgrade --user Cython==0.29.10
python -m pip install --upgrade --user pillow
#uses pypi as source
python -m pip install --user kivy==1.11.0

(sudo apt install xorg)

#sudo rm -rf LCD-show
cd /
sudo git clone https://github.com/goodtft/LCD-show.git
sudo chmod -R 755 LCD-show
cd LCD-show/
#reboots when finished
sudo ./LCD7C-show 90 

git clone https://github.com/D4SK/Klipper-GUI #needs password for github right now


backend gl oder sdl2
window egl rpi
python3


### NetworkManager

sudo apt install network-manager
sudo apt purge openresolv dhcpcd5
sudo mv /etc/resolv.conf /etc/resolv.conf.backup
sudo ln -s /lib/systemd/resolv.conf /etc/resolv.conf
sudo systemctl start systemd-resolved.service
sudo systemctl enable systemd-resolved.service
