from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.properties import ListProperty, StringProperty, ObjectProperty
from kivy.clock import Clock
from subprocess import Popen, PIPE, STDOUT
from functools import partial
from elements import *

#Only for test, will be removed later
import time


class SetItem(FloatLayout):
    pass

class SI_Wifi(SetItem):
    
    # The string that is displayed by the label. 
    # Holds the current wifi connection and possibly the signal strength as well. 
    display = StringProperty()

    def __init__(self, **kwargs):
        super(SI_Wifi, self).__init__(**kwargs)
        self.freq = 30
        # Assuming very much that the Setting Screen will NEVER be the default on load
        self.do_update = False
        # Bind to main tab switches after everything is set up and running
        Clock.schedule_once(self.bind_tab, 0)

    def bind_tab(self, dt):
        tab = App.get_running_app().root
        tab.bind(current_tab=self.control_update)

    def control_update(self, instance, value):
        if value == instance.ids.set_tab:
            self.do_update = True
            Clock.schedule_once(self.update, -1)
            self.update_clock = Clock.schedule_interval(self.update, self.freq)
        elif self.do_update and value != instance.ids.set_tab:
            self.do_update = False
            self.update_clock.cancel()

    def update(self, dt):
        # Placeholder
        hms = time.strftime("%H:%M:%S")
        print(hms)
        self.display = hms

    def on_display(self, instance, value):
        # Applys the new text to display in the Label whenever the text got updated
        self.ids.current_wifi.text = value


class SI_WifiNetwork(SetItem):
    ssid = StringProperty()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.popup = PasswordPopup(ssid=self.ssid)
            self.popup.open()
            return True
        return super(SI_WifiNetwork, self).on_touch_down(touch)

class WifiScreen(Screen):

    ssid_list = ListProperty()
    
    def __init__(self, **kwargs):
        super(WifiScreen, self).__init__(**kwargs)
        # Amount of seconds between wifi rescans in seconds
        self.freq = 30

    def on_pre_enter(self):
        # pre_enter: This function is executed when the animation starts
        Clock.schedule_once(self.get_ssid_list, -1)
        self.update_clock = Clock.schedule_interval(self.get_ssid_list, self.freq)

    def on_leave(self):
        self.update_clock.cancel()

    def on_ssid_list(self, instance, val):
        # Repopulate the list of networks when self.ssid_list changes
        box = self.ids.wifi_box
        box.clear_widgets()
        for i in val:
            entry = SI_WifiNetwork()
            entry.ssid = i
            box.add_widget(entry)

    def get_ssid_list(self, dt):
        # on_ssid_list() is only called when this list is different to the previous list
        hms = time.strftime("%H:%M:%S")
        s = int(time.time())%7 + 2
        names = []
        for i in range(s):
            names.append(hms+'.'+str(i))
        print(names)
        self.ssid_list = names

class PasswordPopup(BasePopup):
    
    password = StringProperty()
    txt_input = ObjectProperty(None)
    
    def __init__(self, ssid, **kwargs):
        self.ssid = ssid
        self.title = ssid
        super(PasswordPopup, self).__init__(**kwargs)
        self.txt_input.bind(on_text_validate=self.connect)
        # If focus is set immediately, keyboard will be covered by popup
        Clock.schedule_once(self.set_focus_on, 0.1)

    def set_focus_on(self, dt):
        self.txt_input.focus = True

    def connect(self, instance=None):
        self.dismiss()
        self.password = self.txt_input.text
        print(self.password)
    def confirm(self):
        self.connect()
        super(PasswordPopup,self).confirm()

class Wifi(object):

    networks = ListProperty()

    def __init__(self):
        self.state = self.check_nmcli()

    def check_nmcli(self):
        # state codes:
        #
        # 0     No problems
        # 2     network-manager not installed
        # 3     network-manager not running
        # 10    Any Error while running nmcli
        #
        #TODO integrate kivy logger warnings
        try:
            proc = Popen(['nmcli', '-g', 'RUNNING', 'general'], stdout=PIPE, stderr=STDOUT, universal_newlines=True)
        except OSError as e:
            # 2 is "No such file or directory" error
            if e.errno == 2:
                print('NetworkManager not available. Wifimenu will be disabled')
                print("Use 'sudo apt-get install network-manager' to install")
                return e.errno
            else:
                # crash in case of unknown error
                print('NetworkManager failed with Error:')
                raise
        output = proc.communicate()
        if output[0] == 'running':
            return 0
        else:
            print(output[1])
            return 3

    def get_wifi_list(self, instant=False):
        # instant: when True set --rescan to no to immediately (~100ms delay) return a list, even if
        # it is too old. Otherwise rescan if necessary (handled by using 'auto'), possibly taking a few
        # seconds, unless the latest rescan was very recent.
        # bind to networks property to receive the final list
        if self.state != 0:
            return
        rescan = 'no' if instant else 'auto'
        cmd = ['nmcli', '--get-values', 'SSID,SIGNAL,BARS,IN-USE', 'device', 'wifi', 'list', '--rescan', rescan]
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        self.poll(proc, self.parse_wifi_list)

    def poll(self, proc, callback, *args):
        # This function keeps checking whether the given process is done and only forwards it
        # to the given callback once it is complete, which is checked by Popen.poll(), which
        # returns the returncode when the process is complete.
        # accept *args to catch dt from Clock if provided

        # if process is still running
        if proc.poll() == None:
            # partial returns a new callable with the given default args
            # because Clock itself can't add args to the callback
            Clock.schedule_once(partial(self.poll, proc, callback), 0)
        # if process is done forward to callback
        else:
            callback(proc)

    def parse_wifi_list(self, proc):
        stdout, stderr = proc.communicate()
        returncode = proc.returncode
        if stderr:
            print(stderr)
        if returncode == 8:
            self.state = 3
            return
        # catch all other returncodes
        elif returncode != 0:
            self.state = 10
            print('NetworkManager returned {}'.format(returncode))
            return

        wifi_list = []
        for wifi in stdout.splitlines():
            f = wifi.split(':')
            # create a dictionary for each network containing the fields
            entry = {'ssid': f[0], 'signal': int(f[1]), 'bars': f[2], 'in-use': bool(f[3])}
            # Put in-use network to beginning of list
            if entry['in-use']:
                wifi_list.insert(0, entry)
            else:
                wifi_list.append(entry)

        self.networks = wifi_list


wifi = Wifi()

class SI_PowerMenu(SetItem):

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.popup = PowerPopup()
            self.popup.open()
            return True
        return super(SI_PowerMenu, self).on_touch_down(touch)

class PowerPopup(BasePopup):

    def poweroff(self):
        Popen(['systemctl', 'poweroff'])

    def reboot(self):
        Popen(['systemctl', 'reboot'])

class SI_ValueSlider(SetItem):
    pass
