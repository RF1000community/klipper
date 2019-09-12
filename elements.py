from kivy.uix.widget import Widget
from kivy.uix.behaviors.button import ButtonBehavior
from kivy.uix.popup import Popup

class BaseButton(ButtonBehavior, Widget):
    def on_touch_up(self, touch):
        if self.pressed: 
            self.pressed = False
        super(BaseButton, self).on_touch_up(touch)
        return
class RoundButton(BaseButton):
    pass
class BasePopup(Popup):
    def confirm(self):
        self.dismiss()
