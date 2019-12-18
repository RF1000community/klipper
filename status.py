import logging
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import RoundedRectangle, Ellipse, Rectangle
from kivy.properties import StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

import parameters as p
from settings import wifi

class TimeLabel(Label):

    time = StringProperty("00:00")

    def __init__(self, **kwargs):
        self.update_clock = None
        self.get_time_str()
        self.start_clock()
        super(TimeLabel, self).__init__(**kwargs)

    def start_clock(self):
        # How many seconds are left to the next full minute
        offset = 60 - time.time() % 60
        Clock.schedule_once(self.start_updates, offset)

    def start_updates(self, dt):
        self.update_clock = Clock.schedule_interval(self.get_time_str, 60)
        Clock.schedule_once(self.get_time_str, 1)

    def get_time_str(self, *args):
        self.time = time.strftime("%H:%M")

class ConnectionIcon(Widget):

    def __init__(self, **kwargs):
        self.topright = []
        super(ConnectionIcon, self).__init__(**kwargs)
        Clock.schedule_once(self.init_drawing, 0)

        self.show_wifi = False
        self.show_eth = False
        wifi.bind(on_connection_types=self.set_icon)
        wifi.bind(on_networks=self.update_wifi)

    def init_drawing(self, dt):
        self.icon_padding = 2
        self.transparent = (0, 0, 0, 0)
        with self.canvas:
            self.wifi_color = Color(rgba=self.transparent)
            self.wifi = Ellipse(pos=(0, 0), size=(0, 0), angle_start=315, angle_end=405)
            self.eth_color = Color(rgba=p.red)
            self.eth = Rectangle(pos=(0, 0), size=(0, 0), source="Logos/ethernet.png")
        self.draw_nothing()

    def draw_wifi(self):
        padding = self.icon_padding
        h = self.height - 2*padding
        full_size = [2*h, 2*h]
        # cutoff = width of square h*h - width of cake slice (on one side)
        # 1/sqrt(2) = cos(pi/4) avoid trigonometric functions
        cutoff = int(h*(1 - 1/(2**(1./2))) + 0.5)
        self.width = full_size[0] - 2*cutoff + padding
        full_pos = [self.topright[0] - (full_size[0] - cutoff) - padding,
                    self.topright[1] - full_size[1] - padding]
        partial_size = [full_size[0] * self.signal, full_size[1] * self.signal]
        difference = h*(1 - self.signal)
        partial_pos = [full_pos[0] + difference, full_pos[1] + difference]

        self.wifi_color.rgba = p.translucent_white
        self.eth_color.rgba = self.transparent

        self.wifi.pos = partial_pos
        self.wifi.size = partial_size

    def draw_eth(self):
        padding = self.icon_padding
        h = self.height - 2*padding
        size = [h, h]
        self.width = size[0] + padding
        pos = [self.topright[0] - size[0] - padding,
               self.topright[1] - size[1] - padding]

        self.eth_color.rgba = p.medium_gray
        self.wifi_color.rgba = self.transparent

        self.eth.pos = pos
        self.eth.size = size

    def draw_nothing(self):
        self.width = 0
        self.eth_color.rgba = self.wifi_color.rgba = self.transparent

    def set_icon(self, instance, value):
        if value['eth']:
            self.draw_eth()
        elif value['wifi']:
            self.draw_wifi()
        else:
            self.draw_nothing()

    def update_wifi(self, instance, value):
        self.signal = value[0]['signal'] / 100.0
        self.draw_wifi()


class Notifications(FloatLayout):

    def __init__(self):
        super(Notifications, self).__init__()
        self.root_widget = App.get_running_app().root
        self.size_hint = (None, None)
        self.size = self.root_widget.width - 2*p.notification_padding, 110
        self.x = self.root_widget.x + p.notification_padding
        self.top = self.root_widget.top - p.notification_padding
        self.active = False
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt):
        with self.canvas:
            self.shadow_color = Color(rgba=p.notification_shadow)
            Rectangle(pos=(0, p.screen_height-220) ,size=(p.screen_width, 220))
            self.bg_color = Color(rgba=p.red)
            RoundedRectangle(pos=self.pos, size=self.size, radius=(p.radius, p.radius))

        title = Label(
                size_hint = (None, None),
                font_size = p.normal_font,
                bold = True,)
        title.size = (self.width, title.font_size)
        title.text_size = title.size
        title.x = self.x + p.notification_text_padding
        title.top = self.top - p.notification_text_padding
        self.add_widget(title)
        self.title_label = title

        message = Label(
                size_hint = (None, None),
                font_size = p.normal_font,)
        message.size = (self.width, message.font_size)
        message.text_size = message.size
        message.x = self.x + p.notification_text_padding
        message.top = title.y - p.notification_text_padding/2
        self.add_widget(message)
        self.message_label = message

    def show(self, title="", message="", level="info", log=True, delay=10, color=None):
        """
        Show a notification popup with the given parameters. If log is set,
        also write to the log file.

        Parameters:
        title   string      Title of the notification
        message string      Message body of the notification
        level   string      What log level preset to use.
        log     bool        Whether or not to write the notification in the logs.
        delay   int         Time until notification is automatically hidden in seconds
        color   rgba list   Background color of the notification. Overwrites the
                or string   value set by the level preset. Can also be the name of
                            different preset that the specified log level.
        """
        color_presets = {
                "info": p.notify_info,
                "warning": p.notify_warning,
                "error": p.notify_error,
                "success": p.notify_success}
        if level not in color_presets.keys():
            raise Exception("Unrecognized log level preset " + level)

        # Only show one Notification at a time
        if self.active:
            self.hide()
        self.title_label.text = title
        self.message_label.text = message

        if isinstance(color, str) and color in color_presets.keys():
            self.bg_color.rgba = color_presets[color]
        elif isinstance(color, (list, tuple)):
            self.bg_color.rgba = color
        else:
            self.bg_color.rgba = color_presets[level]

        if log:
            if title:
                if level in("info", "success"):
                    logging.info("Notify: " + title)
                elif level == "warning":
                    logging.warning("Notify: " + title)
                elif level == "error":
                    logging.error("Notify: " + title)
            if message:
                if level in("info", "success"):
                    logging.info("Notify: " + message)
                elif level == "warning":
                    logging.warning("Notify: " + message)
                elif level == "error":
                    logging.error("Notify: " + message)

        window = self.root_widget.get_root_window()
        window.add_widget(self)
        self.active = True
        # Schedule automatic hiding
        self.update_clock = Clock.schedule_once(self.hide, delay)

    def hide(self, *args):
        self.update_clock.cancel()
        self.root_widget.get_root_window().remove_widget(self)
        self.active = False

    def redraw(self):
        # Redraw the notification on top of the window. Used in BasePopup.open()
        if self.active:
            window = self.root_widget.get_root_window()
            window.remove_widget(self)
            window.add_widget(self)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.hide()
            return True
        return super(Notifications, self).on_touch_down(touch)
