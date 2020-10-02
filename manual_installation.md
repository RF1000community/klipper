## Manual Installation and Debugging Notes (incomplete)


opengl driver used to only work with autologin enabled and a reinstall of the lcd driver  

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


### Kivy Guide

https://blog.kivy.org/2019/06/widget-interactions-between-python-and-kv/
Screens (of screenmanager) are relative Layouts (new root for coordinate system)
setting properties of parent class in kv rules doesnt work if they are assigned to a value in parent rule
Defining Properties in kv is often bad since it happens too late, and prohibits setting them in __init__
##### LABELS #####
try setting hints to None if it does shit e.g. setting size doesnt work
size: outer dimensions of the label widget, available space, can be set to texture_size to show everything
text_size: can be set to limit texture size e.g. cut off text, can be set to size to show all that fits bounding box for text
texture_size: size of the actual text not cut off(outer dimensions), can set font_size
always size_hint: None, None when setting size: needed
halign or valign set position of text within text_size
in canvas: e.g. self.*** acceses the 'parent' widget of the canvas, unlike in other child Instances like Label:
pos: coordinates are always relative to the innermost Layout, not Widget you are in
Widgets: always define size first then pos at least when using top or right.. x:
Never Put comments after canvas: Instruction
f-strings in kv are not reevaluated if properties change, format() is
##### How to access Instances or their methods #####
in kv to on_propertychange: id.method() id can be bound within root widget
in py someinstance.bind(someinstances on_propertychange = self.method_to_bind) passes instance and every property
by instantiating in python, storing instance
in python self.ids.some_id.method() instances of child widges can be accessed by id (ids is dict with instance as value)
##### THREAD SAFETY #####
Clock methods (e.g. Clock.schedule_once()) are thread safe, can be used do execute methods in Kivy thread from somewhere else
reactor.register_async_callback should also be thread safe, since it uses a Queue
Simple Assignments are thread safe because of GIL
#### How to install kivy from Source #####
- download [latest kivy build](https://kivy.org/downloads/ci/raspberrypi/kivy/) (cpython37 for armv7) to your raspberry pi
- install downloaded kivy build
```bash
source ./klipperui/klippy-environment/bin/activate
pip install ./filename_of_kivy_build.whl
```
