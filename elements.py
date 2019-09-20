from kivy.uix.widget import Widget
from kivy.uix.behaviors.button import ButtonBehavior
from kivy.uix.popup import Popup
from kivy.properties import NumericProperty


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

class UltraSlider(Widget):
    abs_val_px = NumericProperty()

    def __init__(self, **kwargs):
        self.abs_min = 100
        print("this is x{} and this right{} ".format(self.x,self.right))

        self.abs_max = 500
        self.abs_val_px = 80
        super(UltraSlider, self).__init__(**kwargs)
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self.update_pos(touch.pos)
            return True
    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self.update_pos(touch.pos)
            return True
    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self.update_pos(touch.pos)
            return True
    def update_pos(self, pos):
        x = int(pos[0])
        if x > self.abs_max: x = self.abs_max
        elif x < self.abs_min: x = self.abs_min
        #print(x)
        self.abs_val_px = x
