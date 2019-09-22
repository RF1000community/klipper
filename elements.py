from kivy.uix.widget import Widget
from kivy.uix.behaviors.button import ButtonBehavior
from kivy.uix.popup import Popup
from kivy.properties import NumericProperty, BooleanProperty, StringProperty
from kivy.uix.vkeyboard import VKeyboard
from kivy.clock import Clock


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
    disp_val = StringProperty()
    pressed = BooleanProperty(False)
    def __init__(self, **kwargs):
        self.val = str()
        super(UltraSlider, self).__init__(**kwargs)
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt):
        self.abs_max = self.right-54
        self.abs_min = self.x+54

    def on_touch_down(self, touch):
        #print("x is {} and right is {} ".format(self.x,self.right))

        if touch.pos[0] > self.abs_min and touch.pos[0] < self.abs_max and \
           touch.pos[1] > self.y + 70-15 and touch.pos[1] < self.y + 70+15:
            self.pressed = True
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
            self.update_pos(touch.pos, True)
            self.pressed = False
            return True
    def update_pos(self, pos, update_val_px = False):
        x = int(pos[0])
        if x > self.abs_max: x = self.abs_max
        elif x < self.abs_min: x = self.abs_min
        self.px_val_conversion(x)
        #print(x)
        self.abs_val_px = x
    def px_val_conversion(self,abs_x):
        self.val = (abs_x-self.abs_min)*100/(self.abs_max-self.abs_min)
        self.disp_val = "{}%".format(round(self.val,1))
        if self.val == 0:
            self.disp_val = "Off"

        print(self.disp_val)

class UltraKeyboard(VKeyboard):
    # Copy of VKeyboard, only overwrite two methods
    # Changed parts marked with <<<<<<<<>>>>>>>>>

    def process_key_on(self, touch):
        if not touch:
            return
        x, y = self.to_local(*touch.pos)
        key = self.get_key_at_pos(x, y)
        if not key:
            return

        key_data = key[0]
        displayed_char, internal, special_char, size = key_data
        line_nb, key_index = key[1]

        # save pressed key on the touch
        ud = touch.ud[self.uid] = {}
        ud['key'] = key

        # for caps lock or shift only:
        uid = touch.uid
        if special_char is not None:
            # Do not repeat special keys
            if special_char in ('capslock', 'shift', 'layout', 'special'):
                if self._start_repeat_key_ev is not None:
                    self._start_repeat_key_ev.cancel()
                    self._start_repeat_key_ev = None
                self.repeat_touch = None
            if special_char == 'capslock':
                self.have_capslock = not self.have_capslock
                uid = -1
            elif special_char == 'shift':
                self.have_shift = True
            elif special_char == 'special':
                #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
                self.have_special = not self.have_special
                uid = -2
                if self.have_capslock:
                    self.active_keys.pop(-1, None)
                    self.have_capslock = False
                #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            elif special_char == 'layout':
                self.change_layout()

        # send info to the bus
        b_keycode = special_char
        b_modifiers = self._get_modifiers()
        if self.get_parent_window().__class__.__module__ == \
            'kivy.core.window.window_sdl2' and internal:
            self.dispatch('on_textinput', internal)
        else:
            self.dispatch('on_key_down', b_keycode, internal, b_modifiers)

        # save key as an active key for drawing
        self.active_keys[uid] = key[1]
        self.refresh_active_keys_layer()

    def process_key_up(self, touch):
        uid = touch.uid
        if self.uid not in touch.ud:
            return

        # save pressed key on the touch
        key_data, key = touch.ud[self.uid]['key']
        displayed_char, internal, special_char, size = key_data

        # send info to the bus
        b_keycode = special_char
        b_modifiers = self._get_modifiers()
        self.dispatch('on_key_up', b_keycode, internal, b_modifiers)

        if special_char == 'capslock':
            uid = -1
        #<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        elif special_char == 'special':
            uid = -2
        #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

        if uid in self.active_keys:
            self.active_keys.pop(uid, None)
            if special_char == 'shift':
                self.have_shift = False
            ##############################<<<<<<<<<<<<<<<<<<<<<<<
            elif special_char == 'special' and self.have_special:
                self.active_keys[-2] = key
            #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            if special_char == 'capslock' and self.have_capslock:
                self.active_keys[-1] = key
            self.refresh_active_keys_layer()


