## Manual Installation and Debugging Notes (incomplete)


opengl driver uset to only work with autologin enabled and a reinstall of the lcd driver  

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

/home/pi/klippy-env/bin/python      klippy executable  
/usr/bin/startx                     xorg
