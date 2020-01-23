# coding: utf-8
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.properties import ListProperty, ObjectProperty, NumericProperty, DictProperty
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.logger import Logger
from subprocess import Popen, PIPE, STDOUT
from functools import partial
from elements import *
import parameters as p
import logging


class Wifi(EventDispatcher):

    #How often to rescan. 0 means never (disabled)
    update_freq = NumericProperty(15)
    connection_types = DictProperty({'wifi': False, 'eth': False})

    def __init__(self, **kwargs):
        super(Wifi, self).__init__(**kwargs)
        self.state = self.check_nmcli()
        self.register_event_type('on_networks')
        self.register_event_type('on_wrong_pw')
        self.scan_output = self.connections_output = None
        self.update_clock = None
        self.networks = []
        Clock.schedule_once(partial(self.get_wifi_list, True), 1)
        if self.state == 0:
            self.update_clock = Clock.schedule_interval(self.get_wifi_list, self.update_freq)

    def check_nmcli(self):
        # state codes:
        #
        # 0     No problems
        # 2     network-manager not installed
        # 3     network-manager not running
        # 10    Any Error while running nmcli

        try:
            proc = Popen(['nmcli', '-g', 'RUNNING', 'general'], stdout=PIPE, stderr=STDOUT, universal_newlines=True)
        except OSError as e:
            # errno 2 is "No such file or directory" error
            if e.errno == 2:
                Logger.error("Wifi: NetworkManager not available. Wifimenu will be disabled. ")
                Logger.error("Wifi: Use 'sudo apt-get install network-manager' to install")
                return 2
            else:
                # crash in case of unknown error
                Logger.critical('Wifi: NetworkManager failed with Error:')
                raise
        stdout, stderr = proc.communicate()
        if stdout.rstrip('\n') == 'running':
            return 0
        else:
            Logger.error('Wifi: NetworkManager not running:')
            if stdout or stderr:
                Logger.error('NetworkManager: ', stdout, stderr)
            return 3

    def on_update_freq(self, instance, value):
        return
        if self.update_clock:
            self.update_clock.cancel()
        if self.state:
            return
        if value > 0:
            self.get_wifi_list()
            self.update_clock = Clock.schedule_interval(self.get_wifi_list, value)

    def get_wifi_list(self, dt=0, no_rescan=False):
        # no_rescan: when True set --rescan to no to immediately (still ~100ms delay) return a list, even if
        # it is too old. Otherwise rescan if necessary (handled by using 'auto'), possibly taking a few
        # seconds, unless the latest rescan was very recent.
        # bind to on_networks event to receive the final list
        if self.state:
            return
        self.get_connection_types()
        rescan = 'no' if no_rescan else 'auto'
        cmd = ['nmcli', '--get-values', 'SIGNAL,IN-USE,SSID', 'device', 'wifi', 'list', '--rescan', rescan]
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        self.poll(proc, self.parse_wifi_list)
        # Also get the list of stored connections to apply to the wifi list
        ccmd = ['nmcli', '--get-values', 'NAME', 'connection', 'show']
        cproc = Popen(ccmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        self.poll(cproc, self.parse_connections)

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
            if callback:
                callback(proc)
            else:
                # If no callback was provided forward directly to error handling
                self.nmcli_error_handling(proc)

    def nmcli_error_handling(self, proc):
        stdout, stderr = proc.communicate()
        returncode = proc.returncode
        app = App.get_running_app()
        if not hasattr(app, 'notify'): return #to prevent an Exception when notify isnt available yet (happens on FIRMWARE_RESATRT)
        notify = app.notify
        if stderr:
            Logger.info('NetworkManager: ' + stderr.strip())
        if "Secrets were required, but not provided" in stdout:
            self.dispatch('on_wrong_pw')
            notify.show("Wrong password", "Secrets were required, but not provided.", level="warning")
        if returncode ==3:
            notify.show("NetworkManager timeout", "Operation timed out. Please try again later.", level="warning")
        elif 4 <= returncode <= 7:
            notify.show("NetworkManager", "Operation failed. Please try again later", level="warning")
        elif returncode == 8:
            Logger.error('Wifi: NetworkManager not running')
            self.state = 3
        elif returncode == 10:
            notify.show("NetworkManager", "Network not found. Please try again later", level="warning")
        elif returncode != 0:
            self.state = 10
            Logger.error("NetworkManager: nmcli failed, returning " + str(returncode))
        else:
            # Finally, if everything is fine, return standard output. Otherwise None is returned
            return stdout

    def parse_connections(self, proc):
        self.parse_wifi_list(proc, True)

    def parse_wifi_list(self, proc, connections=False):
        stdout = self.nmcli_error_handling(proc)
        if not stdout:
            return

        # Remember the output for each command
        if not connections:
            self.scan_output = stdout
        elif connections:
            self.connections_output = stdout

        # Only proceed if output of both commands is present
        if self.scan_output and self.connections_output:
            wifi_list = []
            for wifi in self.scan_output.splitlines():
                # Only allow two splits in case some doofus puts ':' in the wifi name
                f = wifi.split(':', 2)
                in_use = '*' in f[1]
                # create a dictionary for each network containing the fields
                entry = {'signal': int(f[0]), 'in-use': in_use, 'ssid': f[2]}
                stored = entry['ssid'] in self.connections_output.splitlines()
                entry['stored'] = stored
                # Put in-use network to beginning of list
                if entry['in-use']:
                    wifi_list.insert(0, entry)
                else:
                    wifi_list.append(entry)
            self.networks = wifi_list
            self.dispatch('on_networks', self.networks)
            # Reset output cache for next update
            self.scan_output = self.connections_output = None

    def connect(self, ssid, password):
        # Connect a new, unknown network
        if self.state:
            return
        cmd = ['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password]
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        self.poll(proc, self.process_connections)

    def up(self, ssid):
        # Connect to an existing wifi connection
        if self.state:
            return
        cmd = ['nmcli', 'connection', 'up', ssid]
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        self.poll(proc, self.process_connections)

    def down(self, ssid):
        # Disconnect a connected wifi network and disable autoconnect until next reboot
        if self.state:
            return
        cmd = ['nmcli', 'connection', 'down', ssid]
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        self.poll(proc, self.process_connections)

    def delete(self, ssid):
        # Remove a connection along with its stored password
        if self.state:
            return
        cmd = ['nmcli', 'connection', 'delete', ssid]
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        self.poll(proc, self.process_connections)

    def process_connections(self, proc):
        # Receive finished processes to change connections (up, down, delete, connect)
        stdout = self.nmcli_error_handling(proc)
        if not stdout:
            return

        # Somehow requesting the wifi list right after some actions returns empty output
        Clock.schedule_once(partial(self.get_wifi_list, no_rescan=True), 1)

    def get_connection_types(self, *args):
        if self.state:
            return
        cmd = ['nmcli', '--get-values', 'TYPE', 'connection', 'show', '--active']
        proc = Popen(cmd, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        self.poll(proc, self.parse_connection_types)

    def parse_connection_types(self, proc):
        stdout = self.nmcli_error_handling(proc)
        if not stdout:
            return

        wifi = eth = False
        for i in stdout.splitlines():
            if i.endswith("wireless"):
                wifi = True
            elif i.endswith("ethernet"):
                eth = True
        self.connection_types['wifi'] = wifi
        self.connection_types['eth'] = wifi


    def on_networks(self, value):
        Logger.debug('Wifi: Wifi scan complete returning {} networks'.format(len(value)))

    def on_wrong_pw(self, value):
        pass


wifi = Wifi()


class RectangleButton(BaseButton):
    pass

class SetItem(FloatLayout, RectangleButton):
    pass


class SI_Wifi(SetItem):

    # The string that is displayed by the label.
    # Holds the current wifi connection and possibly the signal strength as well.
    # [0]: ssid or message, [1]: formatted as ssid if true, as message otherwise
    display = ListProperty(['', False])

    def __init__(self, **kwargs):
        super(SI_Wifi, self).__init__(**kwargs)
        self.network_manager = App.get_running_app().network_manager
        self.network_manager.bind(on_connected_ssid=self.update)
        # Set default messages after everything is set up and running
        Clock.schedule_once(self.late_setup, 0)

    def late_setup(self, dt):
        if self.network_manager.available:
            self.display = [self.network_manager.connected_ssid or "...",
                bool(self.network_manager.connected_ssid)]
        else:
            self.display = ['not available', False]

    def on_release(self, *args):
        # don't open wifiscreen when wifi doesn't work
        if self.network_manager.available:
            mgr = self.parent.parent.parent.manager
            mgr.current = 'WifiScreen'

    def update(self, instance, value):
        """Called whenever the active wifi connection changes"""
        if value:
            self.display = [value, True]
        else: # value = "" <==> currently no wifi connection
            self.display = ['not connected', False]

    def on_display(self, instance, value):
        """
        Applies the new text to display in the Label whenever the
        text got updated
        """
        label = self.ids.right_label
        label.text = value[0]
        if value[1]:
            label.color = p.light_gray
            label.italic = False
        else:
            label.color = p.medium_light_gray
            label.italic = True


class SI_WifiAccessPoint(SetItem):

    def __init__(self, ap, **kwargs):
        self.ap = ap
        super(SI_WifiAccessPoint, self).__init__(**kwargs)

    def on_release(self):
        # Present different options when wifi is stored by NM
        if self.ap.saved:
            self.popup = ConnectionPopup(self.ap)
            self.popup.open()
        elif not self.ap.encrypted:
            self.ap.connect()
        else:
            self.popup = PasswordPopup(self.ap)
            self.popup.open()

    def get_color(self):
        if self.ap.saved:
            if self.ap.in_use:
                return [0, 0.7, 0, 1]
            return [0.7, 0, 0, 1]
        return p.light_gray


class WifiScreen(Screen):

    def __init__(self, **kwargs):
        super(WifiScreen, self).__init__(**kwargs)
        self.network_manager = App.get_running_app().network_manager
        self.message = '...'
        Clock.schedule_once(self.set_message, 0)
        # Amount of seconds between wifi rescans in seconds
        self.freq = 10
        self.network_manager.bind(on_access_points=self.update)

    def on_pre_enter(self):
        # pre_enter: This function is executed when the animation starts
        assert(self.network_manager.available)
        self.network_manager.wifi_scan()
        self.network_manager.set_scan_frequency(self.freq)
        self.update(None, self.network_manager.access_points)

    def set_message(self, dt=None, msg=None):
        message = msg or self.message
        box = self.ids.wifi_box
        box.clear_widgets()
        label = Label(
                text = message,
                italic = True,
                color = p.medium_light_gray,
                size_hint = (1, None),
                text_size = (p.screen_width, None),
                height = 110,
                font_size = p.normal_font,
                padding = (p.padding, p.padding),
                halign = 'center')
        box.add_widget(label)

    def update(self, instance, value):
        # Repopulate the list of networks when wifi.networks changes
        box = self.ids.wifi_box
        box.clear_widgets()
        if value:
            for ap in value:
                entry = SI_WifiAccessPoint(ap)
                box.add_widget(entry)
        # In case no networks were found
        else:
            self.set_message(msg='no wifi networks detected')


class PasswordPopup(BasePopup):

    txt_input = ObjectProperty(None)

    def __init__(self, ap, **kwargs):
        self.app = App.get_running_app()
        self.ap = ap
        self.title = self.ap.ssid
        super(PasswordPopup, self).__init__(**kwargs)
        self.network_manager = App.get_running_app().network_manager
        self.txt_input.bind(on_text_validate=self.confirm)
        self.network_manager.bind(on_wrong_password=self.wrong_pw)
        # If focus is set immediately, keyboard will be covered by popup
        Clock.schedule_once(self.set_focus_on, 0.4)

    def set_focus_on(self, *args):
        self.txt_input.focus = True

    def confirm(self, *args):
        self.password = self.txt_input.text
        try:
            self.ap.connect(self.password)
        except:
            self.app.notify.show("Connection Failed", "Find out why", delay=4)
        self.dismiss()

    def wrong_pw(self, instance):
        # Avoid a network being stored with the wrong password
        # TODO
        raise NotImplementedError()
        wifi.delete(self.ssid)
        self.open()
        self.set_focus_on()
        app = App.get_running_app()
        app.notify.show("Wrong Password", "Secrets were required, but not provided",
                level="warning", delay=4)
        return True


class ConnectionPopup(BasePopup):

    def __init__(self, ap, **kwargs):
        self.network_manager = App.get_running_app().network_manager
        self.ap = ap
        super(ConnectionPopup, self).__init__(**kwargs)

    def toggle_connected(self):
        if self.ap.in_use:
            self.down()
        else:
            self.up()

    def up(self):
        self.ap.up()
        self.dismiss()

    def down(self):
        self.ap.down()
        self.dismiss()

    def delete(self):
        self.ap.delete()
        self.dismiss()

