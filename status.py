import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.app import App
from kivy.logger import Logger
from kivy.graphics.vertex_instructions import RoundedRectangle
from kivy.graphics.context_instructions import Color
import parameters as p

class TimeLabel(Label):

    time = StringProperty("00:00")

    def __init__(self, **kwargs):
        self.update = None
        self.set_seconds(False)
        super(TimeLabel, self).__init__(**kwargs)
    
    def start_clock(self):
        if self.seconds:
            self.update = Clock.schedule_interval(self.get_time_str, 1)
        else:
            # How many seconds are left to the next full minute
            offset = 60 - time.time() % 60
            Clock.schedule_once(self.start_updates, offset)

    def start_updates(self, dt):
        self.update = Clock.schedule_interval(self.get_time_str, 60)
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
        if self.update:
            self.update.cancel()
        self.get_time_str()
        self.start_clock()

    def on_touch_down(self, touch):
        # Swap between seconds/no seconds time format when time is touched.
        if self.collide_point(*touch.pos):
            self.set_seconds(not(self.seconds))
            return True
        return super(TimeLabel, self).on_touch_down(touch)

class Notifications(FloatLayout):

    def __init__(self, **kwargs):
        super(Notifications, self).__init__(**kwargs)
        self.root_widget = App.get_running_app().root
        self.size_hint = (None, None)
        self.size = self.root_widget.width - 20, 100
        self.x = self.root_widget.x + 10
        self.top = self.root_widget.top - p.status_bar_height - 10
        self.active = False
        self.title = "Title"
        self.message = "Hello Computer!"
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt):
        with self.canvas:
            self.bg_color = Color(rgba=p.red)
            RoundedRectangle(pos=self.pos, size=self.size, radius=(p.radius,p.radius))

        title = Label(text = self.title)
        title.size_hint = (None, None)
        title.font_size = p.normal_font
        title.bold = True
        title.size = title.texture_size
        title.pos_hint = {'x': 0.1, 'y': 0.8}
        title.align = 'left'
        self.add_widget(title)

        message = Label(text = self.message)
        message.size_hint = (None, None)
        message.font_size = p.normal_font
        message.size = message.texture_size
        message.pos_hint = {'x': 0.1, 'top': 0.75}
        message.align = 'left'
        self.add_widget(message)

    def show(self):
        # Only show one Notification at a time
        if self.active:
            self.hide()
        self.root_widget.add_widget(self)
        Logger.info("Notification: I'm not even properly set up :(")

    def hide(self):
        self.root_widget.remove_widget(self)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.hide()
            return True
        return super(Notifications, self).on_touch_down(touch)
