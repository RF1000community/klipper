# coding: utf-8
from collections import deque
from time import time
from os.path import join, basename

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import NumericProperty, BooleanProperty, StringProperty, ListProperty
from kivy.uix.behaviors.button import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.vkeyboard import VKeyboard
from kivy.uix.widget import Widget

from . import parameters as p
import logging
import shutil


class Divider(Widget):
    pass

class BaseButton(Label):
    """ Lightweight adaptation of the kivy button class, with disable functionality """
    pressed = BooleanProperty(False)
    enabled = BooleanProperty(True)
    def __init__(self, **kwargs):
        self.register_event_type('on_press')
        self.register_event_type('on_release')
        super().__init__(**kwargs)

    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True
        if touch.is_mouse_scrolling:
            return False
        if not self.collide_point(touch.x, touch.y):
            return False
        if self in touch.ud:
            return False
        #a button with enabled=False can be placed above other buttons and they keep working
        if not self.enabled: 
            return False
        self.pressed = True
        self.dispatch('on_press')
        touch.grab(self)
        touch.ud[self] = True
        #set pressed=True for at least 180ms to allow gpu to render highlighting of the button. choose lower for faster gpu
        self.pressed_at_least_till = time() + 0.15
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            return True
        if super().on_touch_move(touch):
            return True
        return self in touch.ud

    def on_touch_up(self, touch):
        res = False
        if touch.grab_current is not self:
            return super().on_touch_up(touch)
        assert(self in touch.ud)
        touch.ungrab(self)
        if self.collide_point(*touch.pos) or not self.enabled:
            self.dispatch('on_release')
            res = True
        t = time()
        if t < self.pressed_at_least_till:
            Clock.schedule_once(self.do_release, self.pressed_at_least_till - t)
        else: self.pressed = False
        return res

    def do_release(self, arg):
        self.pressed = False
    def on_press(self):
        pass
    def on_release(self):
        pass

class RoundButton(BaseButton):
    pass

class BtnSlider(BaseButton):
    val = NumericProperty()
    px = NumericProperty()
    s_title = StringProperty()
    offset = NumericProperty()

class BasePopup(Popup):

    def __init__(self, creator=None, val=None, **kwargs):
        # makes this Popup recieve the instance of the calling button to
        # access its methods and e.g. heater_id
        self.creator = creator
        # a popup holds a value that can be passed to a slider, this
        # avoids the value being updated, and the slider reseting
        self.val = val
        super().__init__(**kwargs)

    def open(self, animation=False, **kwargs):
        super().open(animation=animation, **kwargs)
        app = App.get_running_app()
        app.notify.redraw()

    def dismiss(self, animation=False, **kwargs):
        super().dismiss(animation=animation, **kwargs)

class CriticalErrorPopup(BasePopup):
    message = StringProperty()

class ErrorPopup(BasePopup):
    message = StringProperty()

class StopPopup(BasePopup):
    pass

class PrintPopup(BasePopup):
    def __init__(self, path, filechooser=None, timeline=None, **kwargs):
        self.path = path
        self.filechooser = filechooser
        self.timeline = timeline
        super().__init__(**kwargs)

    def confirm(self):
        app = App.get_running_app()
        self.dismiss()
        new_path = self.path
        if 'USB Device' in self.path:
            new_path = join(p.sdcard_path, basename(self.path))
            app.notify.show(f"Copying {basename(self.path)} to Printer...")
            shutil.copy(self.path, new_path)

        app.send_print(new_path)
        tabs = app.root.ids.tabs
        tabs.switch_to(tabs.ids.home_tab)

class UltraSlider(Widget):
    """
    Simple slider widget

    kwargs:
    val_min, val_max    Minimum and Maximum for the output value,
                        used for px <-> conversion.
                        Defaults to 0 and 100
    unit                Unit string, appended to display value.
                        Defaults to "" (no unit)
    round_to            How many decimals to round val to, is passed to round().
    round_style         5 rounds lowest decimal place to multiples of 5... normally 1
    attributes:
    buttons     list of lists: e.g. [[val,offset,"name",the instance]]
    val         value, passed to printer, not in px

    The conversion methods get_px_from_val() and get_val_from_px()
    can be safely overwritten by inheritors for nonlinear conversion.
    """
    buttons = ListProperty()  #list of lists: e.g. [[val,offset,"name",the instance]]
    val = NumericProperty() #value, passed to printer, not in px
    val_min = NumericProperty()
    val_max = NumericProperty()
    unit = StringProperty()
    round_to = NumericProperty()
    round_style = NumericProperty(1)
    px = NumericProperty() #absolute position of dot in px
    disp = StringProperty() #value displayed by label
    pressed = BooleanProperty(False)
    changed = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        self.btn_last_active = None
        self.initialized = False
        super().__init__(**kwargs)
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt):
        self.px_max = self.right - p.padding
        self.px_min = self.x + p.padding
        self.px_width = self.px_max - self.px_min
        self.px = self.get_px_from_val(self.val)
        self.disp = self.get_disp_from_val(self.val)
        for b in self.buttons:
            b[3] = BtnSlider(y=self.y, px=self.get_px_from_val(b[0]), 
                              val=b[0], offset=b[1],  s_title=b[2])
            b[3].bind(on_press=self.on_button)
            self.add_widget(b[3])
        self.highlight_button()
        self.initialized = True

    def on_touch_down(self, touch):
        if touch.pos[0] > self.px_min - 30 and touch.pos[0] < self.px_max + 30\
        and touch.pos[1] > self.y + 95 - 18 and touch.pos[1] < self.y + 95 + 18\
        and self.initialized:
            self.pressed = True
            touch.grab(self)
            x = self.apply_bounds(touch.pos[0])
            self.val = self.get_val_from_px(x)
            self.disp = self.get_disp_from_val(self.val)
            if self.btn_last_active is not None: self.btn_last_active[3].active = False
            self.changed = True
            return True
        return super().on_touch_down(touch)

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
        return super().on_touch_up(touch)

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
        self.changed = True

    def get_px_from_val(self, val):
        """
        Function that converts values between val_min and val_max
        linearly, returning absolute pixel values between px_min and
        px_max.  If val is outside val_min and val_max, the returned
        pixel value is still cast within the slider.
        Requires px_max to be set, do not use in __init__
        """
        if val < self.val_min:
            val = self.val_min
        elif val > self.val_max:
            val = self.val_max
        m = float(self.px_max - self.px_min)/(self.val_max - self.val_min)
        px = self.px_min + m*(val - self.val_min)
        return int(px)

    def get_val_from_px(self, px):
        """
        Inverse function of get_px_from_val(),
        returns val rounded to an integer.
        """
        m = float(self.val_max - self.val_min)/(self.px_max - self.px_min)
        val = self.val_min + m*(px - self.px_min)
        return round(val/self.round_style, self.round_to)*self.round_style

    def get_disp_from_val(self, val):
        """Returns string of the value and the given unit string"""
        dec = max(0, self.round_to)
        return f"{val:.{dec}f}{self.unit}"


# class UltraOffsetSlider(UltraSlider):
#     pass


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


