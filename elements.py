from kivy.uix.widget import Widget
from kivy.uix.behaviors.button import ButtonBehavior
from kivy.uix.popup import Popup
from kivy.properties import NumericProperty, BooleanProperty, StringProperty, ListProperty
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
class Btn_Slider(BaseButton):
    val = NumericProperty()
    px = NumericProperty()



class BasePopup(Popup):
    def confirm(self):
        self.dismiss()
class UltraSlider(Widget):
    px = NumericProperty() #absolute position of dot in px
    disp = StringProperty()#value displayed by label
    pressed = BooleanProperty(False)
    active_buttons = ListProperty()
    def __init__(self, **kwargs):
        self.val = float()#value, passed to printer, not in px
        self.recieve_val()
        self.px = self.get_px_from_val(self.val)
        self.sticky_vals = list()
        self.btn_last_active = None
        self.buttons = [[200,0,"200",None],[400,0,"default",None]]
        super(UltraSlider, self).__init__(**kwargs)
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt):
        self.abs_max = self.right-54
        self.abs_min = self.x+54
        for b in self.buttons:
            self.active_buttons.append(False)
            b[3] = Btn_Slider(y=self.y,  px=self.get_px_from_val(b[0]),  val=b[0],  offset=b[1],  s_title=b[2])
            self.add_widget(b[3])
            b[3].bind(on_press=self.on_button)

    def on_touch_down(self, touch):
        if touch.pos[0] > self.abs_min-30 and touch.pos[0] < self.abs_max+30 and \
           touch.pos[1] > self.y + 80 -15 and touch.pos[1] < self.y + 80 + 15:
            self.pressed = True
            touch.grab(self)
            x = self.apply_bounds(touch.pos[0])
            self.val = self.get_val_from_px(x)
            self.disp = self.get_disp_from_val(self.val)
            if self.btn_last_active is not None: self.btn_last_active[3].active = False
            return True
        return super(UltraSlider, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            x = self.apply_bounds(touch.pos[0])
            self.val = self.get_val_from_px(x)
            self.disp = self.get_disp_from_val(self.val)
            return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            self.pressed = False
            x = self.apply_bounds(touch.pos[0])
            self.px = x
            self.val = self.get_val_from_px(x)
            self.disp = self.get_disp_from_val(self.val)
            self.highlight_button()

            touch.ungrab(self)
            return True
        return super(UltraSlider, self).on_touch_up(touch)

    def apply_bounds(self, x):
        if x > self.abs_max: x = self.abs_max
        elif x < self.abs_min: x = self.abs_min
        return x

    def highlight_button(self):
        if self.btn_last_active is not None: self.btn_last_active[3].active = False
        for b in self.buttons:
            if b[0] == self.val:
                b[3].active = True
                self.btn_last_active = b
    def on_button(self, instance):
        self.val = instance.val
        self.px = self.get_px_from_val(instance.val)
        self.highlight_button()
        self.disp = self.get_disp_from_val(instance.val)
            
    def get_val_from_px(self,x):
        return x
    def get_disp_from_val(self, val):
        return "{}%".format(round(self.val,1))
    def get_px_from_val(self,val):
        self.px = int(val)
        return self.px

    def send_val(self):
        return

    def recieve_val(self):
        self.val = 300
    
class AccelerationSlider(UltraSlider):
    def __init__(self, **kwargs):
        self.sticky_vals = ((35,0))
        super(UltraSlider, self).__init__(**kwargs)
    
    def get_px_from_val(self,abs_x):#  v sets settable range
        self.val = (abs_x-self.abs_min)*(60-3)/(self.abs_max-self.abs_min)
        for k in self.sticky_vals:
            if self.val > k[0]-k[1] and self.val < k[0]+k[1]:
                self.val = k[0]
                self.px = self.val*(self.abs_max-self.abs_min)/100
        self.disp = "{}m/s".format(round(self.val,1))
class TemperatureSlider(UltraSlider):
    def __init__(self, **kwargs):
        self.sticky_vals = ((0,0))
        super(UltraSlider, self).__init__(**kwargs)
    
    def get_px_from_val(self,abs_x):#  v sets settable range
        self.val = (abs_x-self.abs_min)*(60-3)/(self.abs_max-self.abs_min)
        for k in self.sticky_vals:
            if self.val > k[0]-k[1] and self.val < k[0]+k[1]:
                self.val = k[0]
                self.px = self.val*(self.abs_max-self.abs_min)/100
        self.disp = "{}m/s".format(round(self.val,1))      
class FlowSlider(UltraSlider):        
        # self.val = (abs_x-self.abs_min)*100/(self.abs_max-self.abs_min)
        # if self.val%10 <=2:
        #     self.val -= self.val%10
        #     self.px = self.val*(self.abs_max-self.abs_min)/100
        # elif self.val%10 >= 8:
        #     self.val -= self.val%10
        #     self.px = self.val*(self.abs_max-self.abs_min)/100 +self.abs_min
    def __init__(self, **kwargs):
        self.sticky_vals = ((0,0))
        super(UltraSlider, self).__init__(**kwargs)
    
    def get_px_from_val(self,abs_x):#  v sets settable range
        self.val = (abs_x-self.abs_min)*(60-3)/(self.abs_max-self.abs_min)
        for k in self.sticky_vals:
            if self.val > k[0]-k[1] and self.val < k[0]+k[1]:
                self.val = k[0]
                self.px = self.val*(self.abs_max-self.abs_min)/100
        self.disp = "{}m/s".format(round(self.val,1))   



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


