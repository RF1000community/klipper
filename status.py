import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.app import App


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
