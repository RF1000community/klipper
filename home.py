from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.properties import ListProperty, StringProperty, ObjectProperty, BooleanProperty
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.behaviors.button import ButtonBehavior
#  self.ids.big_button.text = "

class BaseButton(ButtonBehavior, Widget):
    def on_touch_up(self, touch):
        if self.pressed: 
            self.pressed = False
            return True
        return super(BaseButton, self).on_touch_up(touch)

class Btn_Stop(BaseButton):
    pass
class Btn_Play(BaseButton):
    pass
class Btn(BaseButton):
    pass
class Btn_Outline(BaseButton):
    pass
class Btn_Temp(BaseButton):
    pass
class Btn_Arrow(BaseButton):
    pass
class BasePopup(Popup):
    def dismiss(self):
        return
    def confirm(self):
        self.dismiss()
class Btn_Triple(Widget):
    pass
class Btn_TripleZ(Widget):
    pass