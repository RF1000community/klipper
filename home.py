# coding: utf-8
import logging
import random

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics.context_instructions import Color
from kivy.graphics.vertex_instructions import RoundedRectangle, Ellipse, Line
from kivy.properties import ListProperty, StringProperty, NumericProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget

from elements import *
import parameters as p


class XyField(Widget):

    pressed = BooleanProperty(False)
    enabled = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(XyField, self).__init__(**kwargs)
        self.point_radius = 10
        self.app = App.get_running_app()
        self.printer_dimensions = (self.app.pos_max['x'] - self.app.pos_min['x'],
                                   self.app.pos_max['y'] - self.app.pos_min['y'])
        self.app.bind(pos=self.update_with_mm)
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt):
        #Calculate bounds of actual field
        self.origin = [self.x+self.point_radius, self.y+self.point_radius]
        self.limits = [self.right-self.point_radius, self.top-self.point_radius]
        self.px = self.origin

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.enabled:
            touch.grab(self)
            self.update_with_px(touch.pos)
            self.pressed = True
            return True
        return False

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self.update_with_px(touch.pos)
            return True
        return False

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self.update_with_px(touch.pos)
            self.app.send_pos(x=self.mm[0], y=self.mm[1], speed=40)
            self.pressed = False
            return True
        return False

    def update_with_px(self, px_input):
        if self.enabled:
            px_input = (int(px_input[0]), int(px_input[1]))
            self.px = self.apply_bounds(px_input[0], px_input[1])
            self.set_mm_with_px(self.px)

    def update_with_mm(self, instance=None, mm=[0,0,0]):
        self.set_px_with_mm(mm)
        self.mm = mm[:3]

    def apply_bounds(self, x, y):
        if x < self.origin[0]:
            x = self.origin[0]
        elif x > self.limits[0]:
            x = self.limits[0]

        if y < self.origin[1]:
            y = self.origin[1]
        elif y > self.limits[1]:
            y = self.limits[1]
        return [x, y]

    def set_mm_with_px(self, px):
        ratio_x = float(px[0] - self.origin[0]) / (self.limits[0] - self.origin[0])
        ratio_y = float(px[1] - self.origin[1]) / (self.limits[1] - self.origin[1])

        self.mm[0] = self.printer_dimensions[0] * ratio_x
        self.mm[1] = self.printer_dimensions[1] * ratio_y

    def set_px_with_mm(self, mm):
        self.px = [(self.limits[0] - self.origin[0]) * float(mm[0]) / self.printer_dimensions[0] + self.origin[0],
                   (self.limits[1] - self.origin[1]) * float(mm[1]) / self.printer_dimensions[1] + self.origin[1]]


class TempSlider(UltraSlider):

    def __init__(self, **kwargs):
        super(TempSlider, self).__init__(**kwargs)
        App.get_running_app().get_temp()
        self.buttons = []
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
            s = "{}°C".format(self.val)
        return s
 

class BedTempSlider(UltraSlider):
    def __init__(self, **kwargs):
        super(BedTempSlider, self).__init__(**kwargs)
        App.get_running_app().get_temp()
        self.buttons = [[0,0,"Off",None],
                        [60,0,"PLA",None],
                        [90,0,"PETG",None],
                        [110,0,"ABS",None]]

    def get_val_from_px(self, x):
        v = int(((x-self.px_min)/self.px_width)*(140-30)+30)
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
            s = "{}°C".format(self.val)
        return s
    def get_px_from_val(self, val):
        x = (float(val-30)/float(140-30))*self.px_width+self.px_min
        if x < self.px_min: x = self.px_min
        return x


class ExtTempSlider(UltraSlider):
    def __init__(self, **kwargs):
        super(ExtTempSlider, self).__init__(**kwargs)
        App.get_running_app().get_temp()
        self.buttons = [
            [0,14,"Off",1,None],
            [70,0,"PLA\ncold pull",1,None],
            [90,-68/2,"ABS/PETG\ncold pull",1,None],
            [210,68/2,"PLA",1,None],
            [230,0,"PETG",1,None],
            [250,-68/2,"ABS",1,None]]
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
            s = "{}°C".format(self.val)
        return s
    def get_px_from_val(self, val):
        x = (float(val-40)/float(280-40))*self.px_width+self.px_min
        if x < self.px_min: x = self.px_min
        return x

"""
class ExtTempOffsetSlider(UltraOffsetSlider):
    def __init__(self, **kwargs:
        super(ExtTempSlider, self).__init__(**kwargs)
        App.get_running_app().get_temp()
        self.buttons = [
            [0,14,"Off",None],
            [210,68/2,"PLA",None],
            [230,0,"PETG",None],
            [250,-68/2,"ABS",None]]
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
        offset = str(self.offset)
        if self.offset >= 0: offset = "+"+ offset
        if self.val == 0:  return "Off {}".format(offset)
        else:              return "{}°C {}".format(self.val, offset)

    def get_px_from_val(self, val):
        x = (float(val-40)/float(280-40))*self.px_width+self.px_min
        if x < self.px_min: x = self.px_min
        return x
"""
from pytictoc import TicToc

class FilamentChooserPopup(BasePopup):
    library_tab = BooleanProperty(True)
    def __init__(self, tool_id, **kwargs):
        super(FilamentChooserPopup, self).__init__(**kwargs)
        self.app = App.get_running_app()
        self.tool_id = tool_id
        self.selected = [None, None, None]
        self.options = [[], [], []]
        Clock.schedule_once(self.draw_options, 0)


    def draw_options(self, dt=None):
        tm = TicToc()
        tm.tic()
        self.selected_guid = None

        # Calculate options to draw based on selection
        if self.library_tab:
            # get material library from filament manager as type-manufacturer-color tree of dicts
            tmc = self.app.filament_manager.tmc_to_guid

            # always show types
            self.options = [ [[t,None,1,None] for t in tmc.keys()], [], [] ] 
            if self.selected[0]:
                # type is selected, show manufacturers
                self.options[1] = [[m, None, 1, None] for m in tmc[self.selected[0].text].keys()]
                if self.selected[1]:
                    # type and manufacturer is selected, show colors
                    self.options[2] = [["", c, 1, None] for c in tmc[self.selected[0].text][self.selected[1].text].keys()]
                    if self.selected[2]:
                        # type and manufacturer and color is selected, we have a material guid
                        self.selected_guid = tmc[self.selected[0].text][self.selected[1].text][self.selected[2].hex_color]
        else:
            self.options = [ [["jkfopjio",None,1,None] for t in range(4)], [], [] ] 


        self.ids.option_stack.clear_widgets()
        for i, group in enumerate(self.options):
            if i:
                self.ids.option_stack.add_widget(OptionDivider())
            for option in group:
                option[3] = Option(level=i, amount=option[2], text=option[0], hex_color=option[1])
                option[3].bind(on_press=self.on_selected)
                self.ids.option_stack.add_widget(option[3])
        """
        # redraw changed options 
        found_change = False
        for i, old_group, new_group in zip(range(len(self.options)), self.options, options):
            if i: self.ids.option_stack.add_widget(OptionDivider()) # no divider before first group

            if len(old_group) == len(new_group) and not found_change:
                # check that nothings changed
                for old_option, new_option in zip(old_group, new_group):
                    if old_option[:3] != new_option[:3]:
                        found_change = True
                        self.remove(old_option)
                        self.draw(new_option, level=i)
                        old_option = new_option # this updates self.options
            else:
                # redraw all options of this group
                found_change = True
                for option in old_group:
                    self.remove(option)
                for option in new_group:
                    self.draw(option, level=i)
                old_group = new_group # this updates self.options
        """
        tm.toc()

    def draw(self, option, level=0):
        option[3] = Option(level=level, amount=option[2], text=option[0], hex_color=option[1])
        option[3].bind(on_press=self.on_selected)
        self.ids.option_stack.add_widget(option[3])

    def remove(self, option):
        self.ids.option_stack.remove_widget(option[3])

    def on_library_tab(self, instance, tab):
        self.draw_options()

    def on_selected(self, option):
        for sel_option in self.selected[option.level:]:
            if sel_option: # unselect and remove all options of later level
                sel_option.selected = False
                sel_option = None
        self.selected[option.level] = option
        self.draw_options()

class Option(BaseButton):
    def __init__(self, hex_color=None, amount=1, level=0, guid=None, **kwargs):
        self.option_color = (0,0,0,0)
        self.amount = amount
        self.level = level
        self.hex_color = hex_color
        self.guid = guid
        if hex_color is not None:
            self.option_color = calculate_filament_color(hex_to_rgb(hex_color)) + [1]
        super(Option, self).__init__(**kwargs)

    def on_press(self):
        self.selected = True

class OptionDivider(Widget):
    pass

class BtnTriple(Widget):
    filament_color = ListProperty([random.randint(0,100)/100. for i in range(3)])
    filament_color_adjusted = ListProperty([0,0,0])
    filament_amount = NumericProperty(0.6)

    def __init__(self, **kwargs):
        super(BtnTriple, self).__init__(**kwargs)
        Clock.schedule_once(self.on_filament_color, 0)

    def on_filament_color(self, *args):
        self.filament_color_adjusted = calculate_filament_color(self.filament_color)

def calculate_filament_color(filament_color):
    """ Calculate the lightness of an rgb color.
        This is equal to the average between the minimum and
        maximum value."""
    l = 0.5*(max(filament_color) + min(filament_color))
    # darken if color is to bright
    if l > 0.48:
        return [c*0.48/l for c in filament_color]
    else:
        return filament_color

def hex_to_rgb(h):
    """"Converts hex color to rgba float format"""
    return [int(h[i:i + 2], 16) / 255. for i in (1, 3, 5)]