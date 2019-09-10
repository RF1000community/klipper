from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.properties import ListProperty, StringProperty, ObjectProperty
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.behaviors.button import ButtonBehavior

class ClearRoundButton(ButtonBehavior, Widget):
    def on_press(self):
        self.pressed = True
    def on_release(self):
        self.pressed = False
class ClearButton(ButtonBehavior, Widget):
    def on_press(self):
        self.pressed = True
    def on_release(self):
        self.pressed = False
class Btn_Stop(ClearRoundButton):
    pass
class Btn_Play(ClearRoundButton):
    pass
class Btn(ClearRoundButton):
    pass
class Btn_Outline(ClearRoundButton):
    pass
class Btn_Temp(ClearRoundButton):
    pass

class Btn_Arrow(ClearRoundButton):
    pass
class Btn_Popup(Widget):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if touch.x-self.x<self.width/2:
                self.pressed1 = True
            else:
                self.pressed2 = True
            return True
        return super(Btn_Popup, self).on_touch_down(touch)
    def on_touch_up(self, touch):
        if self.pressed1 or self.pressed2:
            self.pressed1 = self.pressed2 =  False
            return True
        return super(Btn_Popup, self).on_touch_up(touch)
class BasePopup(Popup):
    pass
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
        return super(Btn_Triple, self).on_touch_down(touch)
    def on_touch_up(self, touch):
        if self.pressed1 or self.pressed2 or self.pressed3:
            self.pressed1 = self.pressed2 = self.pressed3 = False
            return True
        return super(Btn_Triple, self).on_touch_up(touch)
class Btn_TripleZ(Widget):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if touch.y-self.y<self.h1:
                self.pressed1 = True
            elif touch.y-self.y>self.h1 and touch.y-self.y<(self.h1+self.h2):
                self.pressed2 = True
            else:
                self.pressed3 = True
            return True
        return super(Btn_TripleZ, self).on_touch_down(touch)
    def on_touch_up(self, touch):
        if self.pressed1 or self.pressed2 or self.pressed3:
            self.pressed1 = self.pressed2 = self.pressed3 = False
            return True
        return super(Btn_TripleZ, self).on_touch_up(touch)
