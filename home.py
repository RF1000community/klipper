# coding: utf-8
import logging

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import ListProperty, NumericProperty, StringProperty
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
    def __init__(self, extruder_id, **kwargs):
        self.app = App.get_running_app()
        self.fil_man = self.app.filament_manager
        self.extruder_id = extruder_id
        self.selection = [None, None, None]
        self.selection_my = None
        self.selected_guid = None

        self.options = [[], [], []]
        super(FilamentChooserPopup, self).__init__(**kwargs)
        Clock.schedule_once(self.draw_options, 0)


    def draw_options(self, dt=None):
        tm = TicToc()
        tm.tic()
        self.options = [[], [], []]
        self.selected_guid = None
        logging.info("draw options with selecttion {}".format(self.selection))
        # Calculate options to draw based on selection
        if self.library_tab:
            # get material library from filament manager as type-manufacturer-color tree of dicts
            tmc = self.fil_man.tmc_to_guid

            # always show types
            self.options = [ [Option(self, level=0, text=t, selected=(t==self.selection[0])) for t in tmc.keys()], [], [] ] 
            if self.selection[0]:
                # type is selected, show manufacturers
                self.options[1] = [Option(self, level=1, text=m, selected=(m==self.selection[1])) for m in tmc[self.selection[0]].keys()]
                if self.selection[1]:
                    # type and manufacturer is selected, show colors
                    self.options[2] = [Option(self, level=2, hex_color=c, selected=(c==self.selection[2])) for c in tmc[self.selection[0]][self.selection[1]].keys()]
                    if self.selection[2]:
                        # type and manufacturer and color is selected, we have a material guid
                        self.selected_guid = tmc[self.selection[0]][self.selection[1]][self.selection[2]]
                        logging.info("material selected{}".format(self.selected_guid))
        
            # sort types by how many manufactures make them
            # tmc[option.text] is the dict of manufacturers for the current type option (e.g. for PLA)
            self.options[0].sort(key = lambda option: len(tmc[option.text]), reverse=True)
            # sort manufacturers alphabetically
            self.options[1].sort(key = lambda option: option.text, reverse=True)

            # now draw generated options
            self.ids.option_stack.clear_widgets()
            for i in range(len(self.options)):
                for option in self.options[i]:
                    self.ids.option_stack.add_widget(option)
                if len(self.options) > i+1 and self.options[i+1]:
                    self.ids.option_stack.add_widget(OptionDivider(height=0))
        else:

            materials = self.fil_man.loaded_material['unloaded']
            self.options[0] = [Option(self, guid=guid, selected=(self.selected_my==guid), amount=amount/1000,
                ext=self.fil_man.get_material_info(guid=guid, tags=[])) for guid, amount in materials]

        tm.toc()
        logging.info("time to draw:{}".format(tm.elapsed))

    def on_library_tab(self, instance, tab):
        self.draw_options()

    def do_selection(self, option):
        if self.library_tab:
            self.selection[option.level] = option.text or option.hex_color
            for i in range(len(self.selection)):
                if i> option.level:
                    self.selection[i] = None
        else:
            self.selection_my = option.guid
        self.draw_options()

class Option(BaseButton):
    selected = BooleanProperty(False)
    def __init__(self, filamentchooser, selected, hex_color=None, amount=1, level=0, guid=None, **kwargs):

        self.selected = selected
        self.filamentchooser = filamentchooser
        self.option_color = (0,0,0,0)
        self.amount = amount
        self.level = level
        self.hex_color = hex_color
        self.guid = guid
        if hex_color is not None:
            self.option_color = calculate_filament_color(hex_to_rgb(hex_color)) + [1]
        super(Option, self).__init__(**kwargs)
        self.multiline = True
        self.max_lines = 2
        self.shorten_from = 'right'
        self.font_size = p.normal_font - 2

    def on_press(self, **kwargs):
        
        self.filamentchooser.do_selection(self)
        self.selected = True

class OptionDivider(Widget):
    pass

class BtnTriple(Widget):
    filament_color = ListProperty([1,0,0])
    filament_color_adjusted = ListProperty([0,0,0])
    filament_amount = NumericProperty(0.99)
    title = StringProperty()
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