from kivy.uix.widget import Widget
from kivy.uix.behaviors.button import ButtonBehavior
from kivy.uix.popup import Popup
from kivy.properties import NumericProperty, BooleanProperty, StringProperty, ListProperty
from kivy.uix.vkeyboard import VKeyboard
from kivy.clock import Clock
from kivy.app import App



class BaseButton(ButtonBehavior, Widget):
    def on_press(self):
        super(BaseButton, self).on_press()
        #print(get_instance("temp_A").pressed)
        print(get_id(get_instance("temp_A")))
class RoundButton(BaseButton):
    pass
class Btn_Slider(BaseButton):
    val = NumericProperty()
    px = NumericProperty()
    s_title = StringProperty()
    offset = NumericProperty()

class BasePopup(Popup):
    pass

class UltraSlider(Widget):
    px = NumericProperty() #absolute position of dot in px
    disp = StringProperty()#value displayed by label
    pressed = BooleanProperty(False)
    def __init__(self, **kwargs):
        self.buttons = list() #list of lists: e.g. [[val,offset,"name",the instance]]
        self.val = float()    #value, passed to printer, not in px
        self.btn_last_active = None
        self.recieve_val()
        super(UltraSlider, self).__init__(**kwargs)
        Clock.schedule_once(self.init_drawing, 0)
    def init_drawing(self, dt):
        self.px_max = self.right-54
        self.px_min = self.x+54
        self.px_width = self.px_max-self.px_min
        self.px = self.get_px_from_val(self.val)
        self.disp = self.get_disp_from_val(self.val)
        for b in self.buttons:
            b[3] = Btn_Slider(y=self.y,  px=self.get_px_from_val(b[0]),  val=b[0],  offset=b[1],  s_title=b[2])
            b[3].bind(on_press=self.on_button)
            self.add_widget(b[3])
    def on_touch_down(self, touch):
        if touch.pos[0] > self.px_min-30 and touch.pos[0] < self.px_max+30 and \
           touch.pos[1] > self.y + 85 -15 and touch.pos[1] < self.y + 85 + 15:
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
        if x > self.px_max: x = self.px_max
        elif x < self.px_min: x = self.px_min
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
        return ""
    def get_px_from_val(self,val):#requires px_max to be set, do not use in __init__
        self.px = int(val)
        return self.px
    def send_val(self):
        return
    def recieve_val(self):
        return

class AccSlider(UltraSlider):
    def init_drawing(self, dt):
        self.buttons = [[36,0,"default",None],]
        super(AccSlider, self).init_drawing(dt)
    def get_val_from_px(self, x):
        return int(((x-self.px_min)/(self.px_width))*(50-3)+3)
    def get_disp_from_val(self, val):
        return "{}m/s^2".format(self.val)
    def get_px_from_val(self, val):
        return (float(val-3)/float(50-3))*(self.px_width)+self.px_min
    def send_val(self):
        print("Sent Accelleration of {} to printer".format(self.val))
    def recieve_val(self):
        self.val = 36

class TempSlider(UltraSlider):
    def init_drawing(self, dt):
        self.buttons = [[0,14,"Off",None],[70,0,"  PLA  cold pull",None],[90,-68/2,"ABS/PET cold pull",None],[210,68/2,"PLA",None],[230,0,"PETG",None],[250,-68/2,"ABS",None]]
        super(TempSlider, self).init_drawing(dt)
    def get_val_from_px(self, x):
        v = int(((x-self.px_min)/self.px_width)*(280-40)+40)
        for b in self.buttons:
            if v >= b[0]-2 and v <= b[0]+2:
                v = b[0]
                self.px = self.get_px_from_val(v)
                break
        if v <= 42: v = 0
        return v
    def get_disp_from_val(self, val):
        if self.val == 0:
            s = "Off"
        else:
            s = "{}C".format(self.val)
        return s
    def get_px_from_val(self, val):
        x = (float(val-40)/float(280-40))*self.px_width+self.px_min
        if x < self.px_min: x = self.px_min
        return x
    def send_val(self):
        print("Sent Temp of {} to nozzle {}".format(self.val, get_instance_id(self)))
    def recieve_val(self):
        self.val = 0


class FlowSlider(UltraSlider):        
        # self.val = (abs_x-self.px_min)*100/(self.px_max-self.px_min)
        # if self.val%10 <=2:
        #     self.val -= self.val%10
        #     self.px = self.val*(self.px_max-self.px_min)/100
        # elif self.val%10 >= 8:
        #     self.val -= self.val%10
        #     self.px = self.val*(self.px_max-self.px_min)/100 +self.px_min
    def __init__(self, **kwargs):
        self.sticky_vals = ((0,0))
        super(UltraSlider, self).__init__(**kwargs)
    
    def get_px_from_val(self,abs_x):#  v sets settable range
        self.val = (abs_x-self.px_min)*(60-3)/(self.px_max-self.px_min)
        for k in self.sticky_vals:
            if self.val > k[0]-k[1] and self.val < k[0]+k[1]:
                self.val = k[0]
                self.px = self.val*(self.px_max-self.px_min)/100
        self.disp = "{}m/s".format(round(self.val,1))

#The ultimate weapon for spagetti code:
def get_id(inst, root_widget = None):
    if root_widget is None: root_widget = App.get_running_app().root
    q = list(root_widget.ids.values())
    while 1:
        c = q.pop(0)
        if inst in list(c.ids.values()):
            for k in c.ids.keys():
                if c.ids[k] == inst: return k
        q.extend(list(c.ids.values()))

def get_instance(id, root_widget = None):#BFS => always gives the highest level instance with id
    if root_widget is None: root_widget = App.get_running_app().root
    q = list(root_widget.ids.values())
    while 1:
        c = q.pop(0)
        if id in c.ids: return c.ids[id]
        q.extend(list(c.ids.values()))


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


