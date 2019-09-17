Raspian buster lite without desktop env.


add new 'ssh' file with no extension to boot folder to enable ssh
sudo apt-get install python-pip

python -m pip install --upgrade --user pip setuptools
python -m pip install --upgrade --user pip virtualenv



sudo apt-get install git
Der wesentliche Schritt ist, den Xorg Display Server zu installieren 
    sudo apt-get install --no-install-recommends xserver-xorg
Der nächste (empfohlene) Schritt besteht darin, xinit zu installieren, mit dem Sie den Xorg Display Server von der Kommandozeile aus starten können (mit startx)
    sudo apt-get install --no-install-recommends xinit


sudo rm -rf LCD-show
git clone https://github.com/goodtft/LCD-show.git
chmod -R 755 LCD-show
cd LCD-show/
sudo ./LCD7C-show 90


python -m pip install kivy


## Additional dependencies

#### Xorg

* xserver-xorg
* xinit

#### Wifi

* network-manager


`sudo apt-get install --no-install-recommends xserver-xorg xinit`

`sudo apt-get install network-manager`
