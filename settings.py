# coding: utf-8
import logging
import os

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

from .elements import *
from . import parameters as p


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


class SIWifiAccessPoint(SetItem):

    def __init__(self, ap, **kwargs):
        self.ap = ap
        super().__init__(**kwargs)

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
        super().__init__(**kwargs)
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
            box.add_widget(Divider(pos_hint={'center_x':0.5}))
            for ap in value:
                box.add_widget(SIWifiAccessPoint(ap))
        # In case no networks were found
        else:
            self.set_message(msg='no wifi networks detected')


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
        Clock.schedule_once(self.set_focus_on, 0.4)

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
