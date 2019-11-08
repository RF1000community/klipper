import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.app import App
from kivy.logger import Logger
from kivy.graphics.vertex_instructions import RoundedRectangle, Ellipse
from kivy.graphics.context_instructions import Color
import parameters as p
from settings import wifi

class TimeLabel(Label):

    time = StringProperty("00:00")

    def __init__(self, **kwargs):
        self.update_clock = None
        self.set_seconds(False)
        super(TimeLabel, self).__init__(**kwargs)
    
    def start_clock(self):
        if self.seconds:
            self.update_clock = Clock.schedule_interval(self.get_time_str, 1)
        else:
            # How many seconds are left to the next full minute
            offset = 60 - time.time() % 60
            Clock.schedule_once(self.start_updates, offset)

    def start_updates(self, dt):
        self.update_clock = Clock.schedule_interval(self.get_time_str, 60)
        Clock.schedule_once(self.get_time_str, 1)

    def get_time_str(self, *args):
        if self.seconds:
            string = time.strftime("%H:%M:%S")
        else:
            string = time.strftime("%H:%M")
        self.time = string

    def set_seconds(self, seconds):
        # Can change how the time is displayed. Also takes care of the update cycle.
        self.seconds = seconds
        if self.update_clock:
            self.update_clock.cancel()
        self.get_time_str()
        self.start_clock()

    def on_touch_down(self, touch):
        # Swap between seconds/no seconds time format when time is touched.
        if self.collide_point(*touch.pos):
            self.set_seconds(not(self.seconds))
            return True
        return super(TimeLabel, self).on_touch_down(touch)

class ConnectionIcon(Widget):
    
    def __init__(self, **kwargs):
        self.topright = [0,0]
        super(ConnectionIcon, self).__init__(**kwargs)
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt):
        padding = 2
        import math
        full_radius = self.height - 2*padding
        full_size = [2*radius, 2*radius]
        cutoff = radius - math.cos(math.pi/4) * radius
        cutoff = int(cutoff+0.5)
        self.width = size[0] - 2*cutoff + padding
        full_pos = [self.topright[0] - (size[0] - cutoff) - padding,
                    self.topright[1] - size[1] - padding]

        self.transparent = [0, 0, 0, 0]
        with self.canvas:
            self.wifi_color = Color(rgba=self.transparent)
            self.wifi = Ellipse(pos=full_pos, size=full_size, angle_start=315, angle_end=405)
            self.eth_color = Color(rgba=self.transparent)
            self.eth = 
        self.adjust_signal()


class Notifications(FloatLayout):

    def __init__(self, padding=(10, 10), height=100, **kwargs):
        super(Notifications, self).__init__(**kwargs)
        self.root_widget = App.get_running_app().root
        self.size_hint = (None, None)
        self.size = self.root_widget.width - 2*padding[0], height
        self.x = self.root_widget.x + padding[0]
        self.top = self.root_widget.top - p.status_bar_height - padding[1]
        self.active = False
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt):
        with self.canvas:
            self.bg_color = Color(rgba=p.red)
            RoundedRectangle(pos=self.pos, size=self.size, radius=(p.radius,p.radius))

        padding = (10, 10)
        title = Label(
                size_hint = (None, None),
                font_size = p.normal_font,
                bold = True,
                padding = padding)
        title.size = (self.width, title.font_size + 2*padding[1])
        title.text_size = title.size
        title.x = self.x
        title.top = self.top
        self.add_widget(title)
        self.title_label = title

        message = Label(
                size_hint = (None, None),
                font_size = p.normal_font,
                padding = padding)
        message.size = (self.width, message.font_size + 2*padding[1])
        message.text_size = message.size
        message.x = self.x
        message.top = title.y
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
        if not(level in color_presets.keys()):
            raise Exception("Unrecognized log level preset " + level)

        # Only show one Notification at a time
        if self.active:
            self.hide()
        self.title_label.text = title
        self.message_label.text = message

        if type(color) is str and color in color_presets.keys():
            self.bg_color.rgba = color_presets[color]
        elif type(color) in (list, tuple):
            self.bg_color.rgba = color
        else:
            self.bg_color.rgba = color_presets[level]

        if log:
            if title:
                if level in("info", "success"):
                    Logger.info("Notify: " + title)
                elif level == "warning":
                    Logger.warning("Notify: " + title)
                elif level == "error":
                    Logger.error("Notify: " + title)
            if message:
                if level in("info", "success"):
                    Logger.info("Notify: " + message)
                elif level == "warning":
                    Logger.warning("Notify: " + message)
                elif level == "error":
                    Logger.error("Notify: " + message)

        self.root_widget.add_widget(self)
        self.active = True
        # Schedule automatic hiding
        self.update_clock = Clock.schedule_once(self.hide, delay)

    def hide(self, *args):
        self.update_clock.cancel()
        self.root_widget.remove_widget(self)
        self.active = False

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.hide()
            return True
        return super(Notifications, self).on_touch_down(touch)
