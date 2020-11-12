# coding: utf-8
import logging
import os
import re
import subprocess

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.screenmanager import Screen
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.textinput import TextInput

from .elements import BaseButton, BasePopup
from . import parameters as p


class SettingTab(TabbedPanelItem):

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.ids.screen_man.current = "SettingScreen"
        return super().on_touch_down(touch)


class RectangleButton(BaseButton):
    pass


class SetItem(FloatLayout, RectangleButton):
    left_title = StringProperty()
    right_title = StringProperty()


class SIWifi(SetItem):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.network_manager = App.get_running_app().network_manager
        self.network_manager.bind(connected_ssid=self.update)
        # Set default messages after everything is set up and running
        Clock.schedule_once(self.update, 0)

    def update(self, *args):
        if self.network_manager.available:
            self.right_title = self.network_manager.connected_ssid or "not connected"
        else:
            self.right_title = "not available"


class ConsoleScreen(Screen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        app = App.get_running_app()
        # should hopefully be thread safe
        self.fd = app.printer.get_start_args().get("gcode_fd")
        self.reactor = app.reactor
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, *args):
        self.ids.console_input.bind(on_text_validate=self.confirm)

    def on_pre_enter(self):
        self.ids.console_label.text += "Test text from python \n \n \n some more of that test ext"
        self.ids.console_input.focus = True
        self.ids.console_scroll.scroll_y = 0
        self.scheduled_polling = Clock.schedule_interval(self.poll, 1)

    def on_leave(self):
        Clock.unschedule(self.scheduled_polling)

    def poll(self, dt):
        pass
        # with open(os.ttyname(self.fd), 'r') as fd:
        #     while 1:
        #         newdata = fd.read(4096)
        #         #if not newdata:
        #         break
        #         self.ids.console_label.text += newdata

        #     # except BlockingIOError:
        #     #     newdata = "..."
        #     #     break

        #     logging.info(f"ids {self.ids}\n\n\n")
        #     logging.warning("lol")
        #     logging.info(f"scroll ids{self.ids.console_scroll.ids}\n\n\n")

    def confirm(self, *args):
        cmd = self.ids.console_input.text + "\n"
        with open(os.ttyname(self.fd), 'w') as fd:
            fd.write(cmd)
        self.ids.console_input.text = ""
        self.ids.console_label.text += cmd.encode()


class WifiScreen(Screen):

    def on_pre_enter(self):
        """Update the recycleview and trigger frequent scanning"""
        wifi = self.ids.wifi
        network_manager = wifi.network_manager
        if not network_manager.available:
            # Sanity check, SIWifi Button should be disabled in this case
            self.manager.current = "SettingScreen"
            return
        network_manager.wifi_scan()
        network_manager.set_scan_frequency(10)
        wifi.update(None, network_manager.access_points)

    def on_leave(self):
        """Disable frequent scanning which slows down the wifi device"""
        if self.ids.wifi.network_manager.available:
            self.ids.wifi.network_manager.set_scan_frequency(0)


class Wifi(RecycleView):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.network_manager = App.get_running_app().network_manager
        self.network_manager.bind(on_access_points=self.update)

    def update(self, instance, value):
        # Repopulate the list of networks
        if value:
            self.message = ""
            self.data = [{'ap':value[0], 'height':1}] + [{'ap': ap, 'height':110} for ap in value]
            self.refresh_from_data()
        else:
            self.data = []
            self.refresh_from_data()
            self.message = "No Networks found"


class WifiBox(LayoutSelectionBehavior, RecycleBoxLayout):
    # Adds selection behaviour to the view
    pass


class WifiItem(RecycleDataViewBehavior, Label):
    ap = ObjectProperty()
    pressed = BooleanProperty(False)
    index = None

    def refresh_view_attrs(self, rv, index, data):
        # Catch and handle the view changes
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            self.pressed = True
            return True

    def on_touch_up(self, touch):
        was_pressed = self.pressed
        self.pressed = False
        if super().on_touch_up(touch):
            return True
        if self.collide_point(*touch.pos) and was_pressed:

            if self.ap.saved:
                ConnectionPopup(self.ap).open()
            elif not self.ap.encrypted:
                self.ap.connect()
            else:
                PasswordPopup(self.ap).open()

            return True
        return False


class PasswordPopup(BasePopup):

    txt_input = ObjectProperty(None)

    def __init__(self, ap, **kwargs):
        self.app = App.get_running_app()
        self.ap = ap
        self.title = self.ap.ssid
        super().__init__(**kwargs)
        self.network_manager = App.get_running_app().network_manager
        self.txt_input.bind(on_text_validate=self.confirm)
        self.network_manager.bind(on_connect_failed=self.connect_failed)
        # If focus is set immediately, keyboard will be covered by popup
        Clock.schedule_once(self.set_focus_on, 0)

    def set_focus_on(self, *args):
        self.txt_input.focus = True

    def confirm(self, *args):
        self.password = self.txt_input.text
        try:
            self.ap.connect(self.password)
        except:
            self.app.notify.show("Connection Failed", "Find out why",
                    delay=4, level="warning")
        self.dismiss()

    def connect_failed(self, instance):
        # Avoid a network being stored with the wrong password
        self.ap.delete()
        self.open()
        self.set_focus_on()
        self.app.notify.show("connection failed", "Verify the password or try again later",
                level="warning", delay=4)
        return True


class ConnectionPopup(BasePopup):

    def __init__(self, ap, **kwargs):
        self.app = App.get_running_app()
        self.network_manager = self.app.network_manager
        self.ap = ap
        super().__init__(**kwargs)

    def toggle_connected(self):
        if self.ap.in_use:
            self.down()
        else:
            self.up()

    def up(self):
        try:
            self.ap.up()
        except:
            self.app.notify.show("Connection failed",
                    "Please try again later", delay=6, level="warning")
        self.dismiss()

    def down(self):
        try:
            self.ap.down()
        except:
            self.app.notify.show("Failed to disconnect",
                    "Please try again later", delay=6, level="warning")
        self.dismiss()

    def delete(self):
        try:
            self.ap.delete()
        except:
            self.app.notify.show("Failed to delete connection",
                    "Please try again later", delay=6, level="warning")
        self.dismiss()


class SITimezone(SetItem):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_timezone()

    def set_timezone(self):
        if os.path.exists("/etc/localtime"):
            self.right_title = os.path.basename(os.readlink("/etc/localtime"))
        else:
            self.right_title = "not available"


class TimezonePopup(BasePopup):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
            os.system(f"sudo ln -s /usr/share/zoneinfo/{self.region_selection}/{selection['text']} /etc/localtime")
            # update Timezone shown in Settings and Time in Statusbar
            root_ids = App.get_running_app().root.ids
            root_ids.tabs.ids.set_tab.ids.setting_screen.ids.si_timezone.set_timezone()
            root_ids.status_bar.ids.time.get_time_str()
            self.dismiss()


class TimezoneRV(RecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # initally filled with all regions/continents
        region_folders = next(os.walk("/usr/share/zoneinfo/"))[1]
        region_folders.sort()
        # remove some folders we don't want to show
        for folder in ["SystemV", "Etc", "posix", "right"]:
            if folder in region_folders:
                region_folders.remove(folder)
            else:
                logging.warning(f"Please update Timezones: {folder} could not be removed from list")
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
        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        # Add selection on touch down
        if super().on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        # Respond to the selection of items in the view
        self.selected = is_selected

class HostnamePopup(BasePopup):
    """
    Popup for changing the hostname.
    """

    txt_input = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.txt_input.bind(on_text_validate=self.confirm)

    def confirm(self, *args):
        text = self.txt_input.text
        cmd = ["sudo", "hostnamectl", "set-hostname", text]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            app = App.get_running_app()
            app.notify("Failed to set hostname",
                       "hostnamectl finished with exit-code "
                       + str(proc.returncode),
                       level="error",
                       delay=30)
            logging.warning("hostnamectl: " + proc.stdout + " " + proc.stderr)            
        else:
            self.dismiss()

class HostnameTextInput(TextInput):
    """
    Modify TextInput to only input lower- and uppercase ASCII letters,
    digits and hyphens, and not more than 64 characters in total.
    """

    pat = re.compile(r"[^-a-zA-Z0-9]")

    def insert_text(self, substring, from_undo=False):
        filtered = re.sub(self.pat, "", substring)
        max_len = 64 - len(self.text)
        limited = filtered[:max_len]
        return super().insert_text(limited, from_undo=from_undo)
