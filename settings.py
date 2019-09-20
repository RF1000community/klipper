from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.properties import ListProperty, StringProperty, ObjectProperty, NumericProperty
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.logger import Logger
from subprocess import Popen, PIPE, STDOUT
from functools import partial
from elements import *
import parameters as p

#Only for test, will be removed later
import time


class Wifi(EventDispatcher):

    #How often to rescan. 0 means never (disabled)
    update_freq = NumericProperty(0)
    #networks = ListProperty()

    def __init__(self, **kwargs):
        super(Wifi, self).__init__(**kwargs)
        self.state = self.check_nmcli()
        self.register_event_type('on_networks')
        #This shouldn't be needed, but it is
        #self.bind(update_freq=self.on_update_freq)
        self.update_clock = None
        self.networks = []

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
                Logger.error("Wifi: NetworkManager not available. Wifimenu will be disabled. ")
                Logger.error("Wifi: Use 'sudo apt-get install network-manager' to install")
                return e.errno
            else:
                # crash in case of unknown error
                Logger.critical('Wifi: NetworkManager failed with Error:')
                raise
        output = proc.communicate()
        if output[0].rstrip('\n') == 'running':
            return 0
        else:
            Logger.error('Wifi: NetworkManager not running:')
            Logger.error('NetworkManager: ' + output[1])
            return 3

    def on_update_freq(self, instance, value):
        if self.state:
            return
        if self.update_clock:
            self.update_clock.cancel()
        if value > 0:
            self.get_wifi_list()
            self.update_clock = Clock.schedule_interval(self.get_wifi_list, value)

    def get_wifi_list(self, dt=0, no_rescan=False):
        # no_rescan: when True set --rescan to no to immediately (still ~100ms delay) return a list, even if
        # it is too old. Otherwise rescan if necessary (handled by using 'auto'), possibly taking a few
        # seconds, unless the latest rescan was very recent.
        # bind to networks property to receive the final list
        if self.state:
            return
        rescan = 'no' if no_rescan else 'auto'
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
            Logger.error('NetworkManager: ' + stderr)
        if returncode == 8:
            Logger.error('Wifi: NetworkManager not running:')
            Logger.error('NetworkManager: ' + output[1])
            self.state = 3
            return
        # catch all other returncodes
        elif returncode != 0:
            self.state = 10
            Logger.error('NetworkManager: ' + returncode)
            return

        wifi_list = []
        for wifi in stdout.splitlines():
            f = wifi.split(':')
            in_use = True if '*' in f[3] else False
            # create a dictionary for each network containing the fields
            entry = {'ssid': f[0], 'signal': int(f[1]), 'bars': f[2], 'in-use': in_use}
            # Put in-use network to beginning of list
            if entry['in-use']:
                wifi_list.insert(0, entry)
            else:
                wifi_list.append(entry)
        self.networks = wifi_list
        self.dispatch('on_networks', self.networks)

    def on_networks(self, *args):
        pass

    def connect(self, ssid, password):

        if state:
            return
        #TODO Error handling

        cmd = ['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password]
        #TODO everything
        Popen(cmd)


wifi = Wifi()


class SetItem(FloatLayout):
    pass


class SI_Wifi(SetItem):
    
    # The string that is displayed by the label. 
    # Holds the current wifi connection and possibly the signal strength as well. 
    # [0]: ssid or message, [1]: formatted as ssid if true, as message otherwise
    display = ListProperty(['', False])

    def __init__(self, **kwargs):
        super(SI_Wifi, self).__init__(**kwargs)
        self.freq = 10
        if wifi.state:
            self.default = 'not available'
        else:
            self.default = '...'
        # Assuming very much that the Setting Screen will NEVER be the default on load
        self.do_update = False
        wifi.bind(on_networks=self.update)
        # Bind to main tab switches after everything is set up and running
        Clock.schedule_once(self.bind_tab, 0)

    def on_touch_down(self, touch):
        # don't open wifiscreen when wifi doesn't work
        if self.collide_point(*touch.pos) and not wifi.state:
            mgr = self.parent.parent.parent.manager
            mgr.transition.direction = 'left'
            mgr.current = 'WifiScreen'
            return True
        return super(SI_Wifi, self).on_touch_down(touch)

    def on_pre_enter(self):
        wifi.update_freq = self.freq

    def bind_tab(self, dt):
        tab = App.get_running_app().root
        tab.bind(current_tab=self.control_update)

    def control_update(self, instance, value):
        if value == instance.ids.set_tab:
            self.do_update = True
            wifi.get_wifi_list(no_rescan=True)
            wifi.update_freq = self.freq
        elif self.do_update and value != instance.ids.set_tab:
            self.do_update = False
            #Disable scanning updates
            wifi.update_freq = 0

    def update(self, instance, value):
        if value[0]['in-use']:
            self.display = [value[0]['ssid'], True]
        else:
            self.display = ['not connected', False]

    def on_display(self, instance, value):
        # Applys the new text to display in the Label whenever the text got updated
        label = self.ids.current_wifi
        label.text = value[0]
        if value[1]:
            label.color = p.light_gray
            label.italic = False
        else:
            label.color = p.medium_light_gray
            label.italic = True


class SI_WifiNetwork(SetItem):

    def __init__(self, wifi, **kwargs):
        self.wifi = wifi
        super(SI_WifiNetwork, self).__init__(**kwargs)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.popup = PasswordPopup(ssid=self.wifi['ssid'])
            self.popup.open()
            return True
        return super(SI_WifiNetwork, self).on_touch_down(touch)


class WifiScreen(Screen):

    def __init__(self, **kwargs):
        super(WifiScreen, self).__init__(**kwargs)
        if wifi.state:
            self.message = "Wifi doesn't work. How did you even get here? You should never have come this far."
        else:
            self.message = 'scanning...'
        Clock.schedule_once(self.set_message, 0)
        # Amount of seconds between wifi rescans in seconds
        self.freq = 10
        wifi.bind(on_networks=self.update)

    def on_pre_enter(self):
        # pre_enter: This function is executed when the animation starts
        wifi.get_wifi_list(no_rescan=True)
        wifi.update_freq = self.freq

    def set_message(self, dt, msg=None):
        message = msg or self.message
        box = self.ids.wifi_box
        box.clear_widgets()
        label = Label(text=message)
        label.markup = True
        label.italic = True
        label.color = p.medium_light_gray
        label.size_hint = (1, None)
        label.text_size = (p.screen_width, None)
        label.height = 110
        label.font_size = p.normal_font
        label.padding = (p.padding,p.padding)
        label.halign = 'center'
        box.add_widget(label)

    def update(self, instance, value):
        # Repopulate the list of networks when wifi.networks changes
        box = self.ids.wifi_box
        box.clear_widgets()
        if value:
            for i in value:
                entry = SI_WifiNetwork(i)
                box.add_widget(entry)
        # In case no networks were found
        else:
            self.set_message(msg='no wifi networks detected')


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
        wifi.connect(self.ssid, self.password)

    def confirm(self):
        self.connect()
        super(PasswordPopup,self).confirm()


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

    def quit(self):
        app = App.get_running_app()
        app.stop()

class SI_ValueSlider(SetItem):
    pass
