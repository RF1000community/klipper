# coding: utf-8
from functools import partial
from subprocess import Popen, PIPE, STDOUT
import logging
import os, time

from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.properties import ListProperty, ObjectProperty, NumericProperty, DictProperty, StringProperty, BooleanProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.screenmanager import Screen

from elements import *
import parameters as p


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
        self.connection_types['eth'] = eth


    def on_networks(self, value):
        Logger.debug('Wifi: Wifi scan complete returning {} networks'.format(len(value)))

    def on_wrong_pw(self, value):
        pass


wifi = Wifi()


class RectangleButton(BaseButton):
    pass

class SetItem(FloatLayout, RectangleButton):
    left_title = StringProperty()
    right_title = StringProperty()


class SIWifi(SetItem):

    # The string that is displayed by the label.
    # Holds the current wifi connection and possibly the signal strength as well.
    # [0]: ssid or message, [1]: formatted as ssid if true, as message otherwise
    display = ListProperty(['', False])

    def __init__(self, **kwargs):
        super(SIWifi, self).__init__(**kwargs)
        self.freq = 10
        # Assuming very much that the Setting Screen will NEVER be the default on load
        self.do_update = False
        wifi.bind(on_networks=self.update)
        # Set default messages and maybe bind to main tab switches
        # after everything is set up and running
        Clock.schedule_once(self.late_setup, 0)

    def on_release(self, *args):
        # don't open wifiscreen when wifi doesn't work
        #if not wifi.state:
        mgr = self.parent.parent.parent.manager
        mgr.current = 'WifiScreen'

    def on_pre_enter(self):
        return # is this right?
        # Yes, update control logic is currently bypassed to update
        # every 10 seconds for the icon in the status bar.
        wifi.update_freq = self.freq

    def late_setup(self, dt):
        if wifi.state:
            self.display = ['not available', False]
        else:
            self.display = ['...', False]
        #root = App.get_running_app().root
        #tab = root.ids.tabs
        #tab.bind(current_tab=self.control_update)

    def control_update(self, instance, value):
        return # is this right?
        if value == instance.ids.set_tab:
            self.do_update = True
            wifi.get_wifi_list(no_rescan=True)
            wifi.update_freq = self.freq
        elif self.do_update:
            self.do_update = False
            #Disable scanning updates
            wifi.update_freq = 30

    def update(self, instance, value):
        """Process the wifi list and check if the first entry is in use"""
        if value[0]['in-use']:
            self.display = [value[0]['ssid'], True]
        else:
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


class SIWifiNetwork(SetItem):

    def __init__(self, network, **kwargs):
        self.network = network
        super(SIWifiNetwork, self).__init__(**kwargs)

    def on_release(self):
        #Present different options when wifi is stored by NM
        if self.network['stored']:
            self.popup = ConnectionPopup(self.network)
        else:
            self.popup = PasswordPopup(self.network)
        self.popup.open()

    def get_color(self):
        if self.network['stored']:
            if self.network['in-use']:
                return [0, 0.7, 0, 1]
            return [0.7, 0, 0, 1]
        return p.light_gray


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
        return
        wifi.update_freq = self.freq

    def set_message(self, dt, msg=None):
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
            for network in value:
                entry = SIWifiNetwork(network)
                box.add_widget(entry)
        # In case no networks were found
        else:
            self.set_message(msg='no wifi networks detected')


class PasswordPopup(BasePopup):

    txt_input = ObjectProperty(None)

    def __init__(self, network, **kwargs):
        self.network = network
        self.ssid = self.network['ssid']
        self.title = self.ssid
        super(PasswordPopup, self).__init__(**kwargs)
        self.txt_input.bind(on_text_validate=self.confirm)
        wifi.bind(on_wrong_pw=self.wrong_pw)
        # If focus is set immediately, keyboard will be covered by popup
        Clock.schedule_once(self.set_focus_on, 0.2)

    def set_focus_on(self, *args):
        self.txt_input.focus = True

    def confirm(self, *args):
        self.password = self.txt_input.text
        wifi.connect(self.ssid, self.password)
        self.dismiss()

    def wrong_pw(self, instance):
        # Avoid a network being stored with the wrong password
        wifi.delete(self.ssid)
        self.open()
        self.set_focus_on()
        app = App.get_running_app()
        app.notify.show("Wrong Password", "Secrets were required, but not provided",
                level="warning", delay=4)
        return True


class ConnectionPopup(BasePopup):

    def __init__(self, network, **kwargs):
        self.network = network
        self.ssid = self.network['ssid']
        self.connected = self.network['in-use']
        super(ConnectionPopup, self).__init__(**kwargs)

    def toggle_connected(self):
        if self.connected:
            self.down()
        else:
            self.up()

    def up(self):
        wifi.up(self.ssid)
        self.dismiss()

    def down(self):
        wifi.down(self.ssid)
        self.dismiss()

    def delete(self):
        wifi.delete(self.ssid)
        self.dismiss()

class SITimezone(SetItem):

    def __init__(self, **kwargs):
        super(SITimezone, self).__init__(**kwargs)
        self.set_timezone()

    def set_timezone(self):
        if os.path.exists("/etc/localtime"):
            self.right_title = os.path.basename(os.readlink("/etc/localtime"))
        else:
            self.right_title = "not available"

class TimezonePopup(BasePopup):

    def __init__(self, **kwargs):
        super(TimezonePopup, self).__init__(**kwargs)
        self.region_selection = None

    def confirm(self):
        selection = self.ids.rv.data[self.ids.rv_box.selected_nodes[0]]
        self.ids.rv_box.selected_nodes = []
        if not self.region_selection: # 1. selection (region/continent) just done, fill rv with actual timezones
            self.region_selection = selection['text']
            timezone_pseudofiles = next(os.walk("/usr/share/zoneinfo/" + self.region_selection))[2]
            timezone_pseudofiles.sort()
            self.ids.rv.data = [{'text': timezone} for timezone in timezone_pseudofiles]
            self.ids.rv.refresh_from_data()
            self.ids.rv.scroll_y = 1
            self.title = "Choose Timezone"
        else: # 2. selection (timezone) just done
            os.system("sudo unlink /etc/localtime")
            os.system("sudo ln -s /usr/share/zoneinfo/{}/{} /etc/localtime".format(self.region_selection, selection['text']))
            # update Timezone shown in Settings and Time in Statusbar
            root_ids = App.get_running_app().root.ids
            root_ids.tabs.ids.set_tab.ids.setting_screen.ids.si_timezone.set_timezone()
            root_ids.status_bar.ids.time.get_time_str()
            self.dismiss()

class TimezoneRV(RecycleView):
    def __init__(self, **kwargs):
        super(TimezoneRV, self).__init__(**kwargs)
        # initally filled with all regions/continents
        region_folders = next(os.walk("/usr/share/zoneinfo/"))[1]
        region_folders.sort()
        # remove some folders we don't want to show
        for folder in ["SystemV", "Etc", "posix", "right"]:
            if folder in region_folders:
                region_folders.remove(folder)
            else:
                logging.warning("Pleas Update Timezones: {} could not be removed from list".format(folder))
        self.data = [{'text': region} for region in region_folders]

class TimezoneRVBox(LayoutSelectionBehavior, RecycleBoxLayout):
    # Adds selection behaviour to the view
    pass

class TimezoneRVItem(RecycleDataViewBehavior, Label):
    # Add selection support to the Label
    index = None
    selected = BooleanProperty(False)

    def refresh_view_attrs(self, rv, index, data):
        # Catch and handle the view changes
        self.index = index
        return super(TimezoneRVItem, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        # Add selection on touch down
        if super(TimezoneRVItem, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        # Respond to the selection of items in the view
        self.selected = is_selected
