from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.properties import ListProperty, StringProperty, ObjectProperty
from kivy.clock import Clock
from kivy.uix.widget import Widget
class ClearButton(Widget):
    pass
class Btn(ClearButton):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.pressed = True
            return True
        return False
    def on_touch_up(self, touch):
        if self.pressed: 
            self.pressed =  False
            return True
        return False
class Btn_Double(Widget):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if touch.x-self.x<self.width/2:
                self.pressed1 = True
            else:
                self.pressed2 = True
            return True
        return False
    def on_touch_up(self, touch):
        if self.pressed1 or self.pressed2:
            self.pressed1 = self.pressed2 =  False
            return True
        return False
class Btn_Triple(Widget):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if touch.x-self.x<self.w1:
                self.pressed1 = True
            elif touch.x-self.x>self.w1 and touch.x-self.x<(self.w1+2+self.w2):
                self.pressed2 = True
            else:
                self.pressed3 = True
            return True
        return False
    def on_touch_up(self, touch):
        if self.pressed1 or self.pressed2 or self.pressed3:
            self.pressed1 = self.pressed2 = self.pressed3 = False
            return True
        return False
