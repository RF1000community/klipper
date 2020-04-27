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
    tool_id = StringProperty()

    def __init__(self, **kwargs):
        self.btn_last_active = None
        self.initialized = False
        super(UltraSlider, self).__init__(**kwargs)
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt=None):
        app = App.get_running_app()
        app.get_temp()
        fil_man = app.filament_manager

        self.buttons = [[0, 0, "Off", None]] #[value, pos_offset, text, instance]
        if self.tool_id == 'B':
            self.val_min = 30
            self.val_max = 140
            if fil_man:
                loadeds = fil_man.get_status()['loaded']
                for loaded in loadeds:
                    if loaded:
                        material_type = fil_man.get_material_info(
                                loaded[0], "./m:metadata/m:name/m:material")
                        bed_temp = fil_man.get_material_info(loaded[0],
                                "./m:settings/m:setting[@key='heated bed temperature']")
                        if bed_temp:
                            self.buttons.append([int(bed_temp), 0, material_type, None])
            else: # show some generic temperatures
                self.buttons = [
                    [0,0,"Off",None],
                    [60,0,"PLA",None],
                    [90,0,"PETG",None],
                    [110,0,"ABS",None]]
        else:
            self.val_min = 40
            self.val_max = 280
            if fil_man:
                extruder_idx = int(self.tool_id[-1])
                loadeds = fil_man.get_status()['loaded']
                loaded = None
                if len(loadeds) > extruder_idx:
                    loaded = loadeds[extruder_idx]
                if loaded:
                    material_type = fil_man.get_material_info(
                            loaded[0], "./m:metadata/m:name/m:material")
                    ext_temp = fil_man.get_material_info(loaded[0],
                            "./m:settings/m:setting[@key='print temperature']")
                    if ext_temp:
                        self.buttons.append([int(ext_temp), 0, material_type, None])
            else:
                self.buttons = [
                    [0,14,"Off",None],
                    [70,0,"PLA\ncold pull",None],
                    [90,-68/2,"ABS/PETG\ncold pull",None],
                    [210,68/2,"PLA",None],
                    [230,0,"PETG",None],
                    [250,-68/2,"ABS",None]]
        self.px_max = self.right - p.padding
        self.px_min = self.x + p.padding
        self.px_width = self.px_max - self.px_min
        self.px = self.get_px_from_val(self.val)
        self.disp = self.get_disp_from_val(self.val)
        for b in self.buttons:
            b[3] = BtnSlider(y=self.y, px=self.get_px_from_val(b[0]), 
                              val=b[0], offset=b[1], s_title=b[2])
            b[3].bind(on_press=self.on_button)
            self.add_widget(b[3])
        self.highlight_button()
        self.initialized = True

    def get_val_from_px(self, x):
        v = int(((x-self.px_min)/self.px_width)*(self.val_max-self.val_min)+self.val_min)
        for b in self.buttons:
            if v >= b[0]-2 and v <= b[0]+2:
                v = b[0]
                self.px = self.get_px_from_val(v)
                break
        if v <= self.val_min + 2:
            v = 0
        return v

    def get_disp_from_val(self, val):
        if self.val == 0:
            s = "Off"
        else:
            s = "{}°C".format(self.val)
        return s

    def get_px_from_val(self, val):
        x = (float(val-self.val_min)/float(self.val_max-self.val_min))*self.px_width+self.px_min	
        if x < self.px_min: x = self.px_min	
        return x

class BtnTriple(Widget):
    filament_color = ListProperty([0,0,0,0])
    filament_amount = NumericProperty(0)
    title = StringProperty()
    tool_id = StringProperty()
    extruder_id = StringProperty()
    def __init__(self, **kwargs):
        self.app = App.get_running_app()
        self.material = None
        self.app.printer.register_event_handler("filament_manager:material_changed", self.update_material)
        self.app.bind(printer_objects_available=self.update_material)
        self.app.bind(print_state=self.update_material)
        super(BtnTriple, self).__init__(**kwargs)

    def update_material(self, *_):
        if not self.tool_id: # kv ui not initialized yet
            Clock.schedule_once(self.update_material, 0)
            return
        self.fil_man = self.app.filament_manager
        if not self.fil_man:
            self.title = "filament_manager\nnot configured"
            return
        extruder_idx = int(self.tool_id[-1])
        loaded_material = self.fil_man.get_status()['loaded']
        self.material = None
        if len(loaded_material) > extruder_idx:
            self.material = loaded_material[extruder_idx]

        if self.material:
            material_type = self.fil_man.get_material_info(self.material[0], "./m:metadata/m:name/m:material")
            brand = self.fil_man.get_material_info(self.material[0], "./m:metadata/m:name/m:brand")
            hex_color = self.fil_man.get_material_info(self.material[0], "./m:metadata/m:color_code")
            self.filament_color = calculate_filament_color(hex_to_rgb(hex_color)) + [1]
            self.filament_amount = self.material[1]
            if self.material[2] == 'loading':
                self.title = "Loading..."
            elif self.material[2] == 'unloading':
                self.title = "Unloading..."
            else:
                self.title = "{:3.0f}g\n{} {}".format(self.material[1]*1000, brand, material_type)
        else:
            self.title = "Load Material"
            self.filament_color = (0,0,0,0)
        
    def load_unload(self):
        if not self.material:
            FilamentChooserPopup(self.extruder_id).open()
        elif self.material[2] == 'loaded':
            FilamentPopup(self.extruder_id, False, self.material[0], amount=self.material[1]).open()


class FilamentChooserPopup(BasePopup):
    tab_2 = BooleanProperty(False)
    def __init__(self, extruder_id, **kwargs):
        self.app = App.get_running_app()
        self.fil_man = self.app.filament_manager
        self.extruder_id = extruder_id
        self.show_less = [True, True, True]
        self.sel = [None, None, None, None] # selected [type, manufacturer, color, guid]
        self.sel_2 = (None, None, None) # selected (amount, idx, guid)
        self.options = [[], [], []]
        super(FilamentChooserPopup, self).__init__(**kwargs)
        Clock.schedule_once(self.draw_options, 0)

    def draw_options(self, dt=None):
        self.options = [[], [], []]
        self.sel[3] = None
        self.ids.option_stack.clear_widgets()
        self.ids.btn_confirm.text = "Select"
        self.ids.btn_confirm.enabled = False
        # Calculate options to draw based on selection
        if not self.tab_2:
            # get material library from filament manager as type-manufacturer-color tree of dicts
            tmc = self.fil_man.tmc_to_guid

            # always show types
            self.options = [[Option(self, level=0, text=t, selected=(t==self.sel[0])) 
                           for t in tmc.keys()], [], []] 
            if self.sel[0]:
                # type is selected, show manufacturers
                # autoselect if there's only one manufacturer, or 'Generic' and none is selected
                manufacturers = tmc[self.sel[0]].keys()
                if len(manufacturers) == 1:
                    self.sel[1] = manufacturers[0]
                elif self.sel[1] is None and 'Generic' in manufacturers:
                    self.sel[1] = 'Generic'
                self.options[1] = [Option(self, level=1, text=m, color=p.light_gray,
                                  font_size=p.small_font, selected=(m==self.sel[1]))
                                  for m in manufacturers]
                if self.sel[1]:
                    # type and manufacturer is selected, show colors
                    # autoselect if there's only one color
                    colors = tmc[self.sel[0]][self.sel[1]].keys()
                    if len(colors) == 1:
                        self.sel[2] = colors[0]
                    self.options[2] = [Option(self, level=2, hex_color=c, selected=(c==self.sel[2])) 
                                      for c in colors]
                    if self.sel[2]:
                        # type and manufacturer and color is selected, we have a material guid
                        self.sel[3] = tmc[self.sel[0]][self.sel[1]][self.sel[2]]
                        self.ids.btn_confirm.text = "Select {} {}".format(self.sel[1], self.sel[0])
                        self.ids.btn_confirm.enabled = True

            # sort types by how many manufactures make them
            # tmc[option.text] is the dict of manufacturers for the selected type (e.g. for PLA)
            self.options[0].sort(key = lambda option: len(tmc[option.text]), reverse=True)
            # sort manufacturers alphabetically, "Generic" always first
            self.options[1].sort(key = lambda option: option.text.lower() if option.text!='Generic' else '\t')

            # now draw generated options
            for i in range(len(self.options)):
                max_amount = (15 if i == 0 else 10)
                if len(self.options[i]) < max_amount or not self.show_less[i]:
                    for option in self.options[i]:
                        self.ids.option_stack.add_widget(option)
                    if len(self.options) > i+1:
                        self.ids.option_stack.add_widget(OptionDivider(self, level=i))
                else: # hidden options
                    for option in self.options[i][:max_amount]:
                        self.ids.option_stack.add_widget(option)
                    if self.options[i]: # draw the show_more divider even if next group is empty
                        self.ids.option_stack.add_widget(OptionDivider(self, level=i, height=0))
                self.ids.btn_confirm.text = "Select"

        else:   
            materials = self.fil_man.get_status()['unloaded']
            for i, (guid, amount) in enumerate(materials):
                option = Option(
                    self, guid=guid, selected=(self.sel_2[1]==i),
                    amount=amount, unloaded_idx=i, font_size=p.small_font,
                    hex_color=self.fil_man.get_material_info(guid, "./m:metadata/m:color_code"),
                    text=self.fil_man.get_material_info(guid, "./m:metadata/m:name/m:brand") + " "
                        +self.fil_man.get_material_info(guid, "./m:metadata/m:name/m:material"))
                self.options[0].append(option)
                self.ids.option_stack.add_widget(option)
            if self.sel_2:
                self.ids.btn_confirm.text = "Select"
                self.ids.btn_confirm.enabled = True

    def on_tab_2(self, instance, tab):
        self.draw_options()

    def do_selection(self, option):
        if self.tab_2:
            self.sel_2 = (option.amount, option.unloaded_idx, option.guid)
        else:
            self.sel[option.level] = option.text or option.hex_color
            for i in range(len(self.sel)):
                if i > option.level:
                    self.sel[i] = None
        self.draw_options()

    def confirm(self):
        if self.tab_2:
            FilamentPopup(self.extruder_id, True, self.sel_2[2], unloaded_idx=self.sel_2[1], amount=self.sel_2[0]).open()
        else:
            FilamentPopup(self.extruder_id, True, self.sel[3]).open()
        self.dismiss()

class Option(BaseButton):
    selected = BooleanProperty(False)
    def __init__(self, filamentchooser, selected, hex_color=None, amount=1, unloaded_idx=None, 
                level=0, guid=None, font_size=p.normal_font-2, color=(1,1,1,1), **kwargs):
        self.selected = selected
        self.filamentchooser = filamentchooser
        self.option_color = (0,0,0,0)
        self.amount = amount
        self.level = level
        self.hex_color = hex_color
        self.guid = guid
        self.unloaded_idx = unloaded_idx
        if hex_color is not None:
            self.option_color = calculate_filament_color(hex_to_rgb(hex_color)) + [1]
        super(Option, self).__init__(**kwargs)
        self.multiline = True
        self.max_lines = 2
        self.shorten_from = 'right'
        self.font_size = font_size
        self.color = color

    def on_press(self, **kwargs):
        self.selected = True
        self.filamentchooser.do_selection(self)

class OptionDivider(BaseButton):
    def __init__(self, filamentchooser, level, **kwargs):
        self.level = level
        self.filamentchooser = filamentchooser
        super(OptionDivider, self).__init__(**kwargs)

    def on_touch_down(self, touch):
        # Add selection on touch down
        if touch.pos[1] > self.y and touch.pos[1] < self.y + self.actual_height:
            self.filamentchooser.show_less[self.level] = not self.filamentchooser.show_less[self.level]
            self.filamentchooser.draw_options()
            return True
        if super(OptionDivider, self).on_touch_down(touch):
            return True
        return False

class FilamentPopup(BasePopup): 
    """ this shows info, and an amount slider on a material coming from one of 3 sources:
        - chosen from library       (extruder_id, new=True, guid)
        - from unloaded materials   (extruder_id, new=True, guid, amount, unloaded_idx)
        - currently loaded material (extruder_id, new=False, guid, amount) """
    amount = NumericProperty(1)
    def __init__(self, extruder_id, new, guid, amount=1, unloaded_idx=None, **kwargs):
        self.app = App.get_running_app()
        self.fil_man = self.app.filament_manager
        self.reactor = self.app.reactor
        self.extruder_id = extruder_id
        self.new = new # set wether the popup is for loading a new material or unloading
        self.guid = guid
        self.amount = amount
        self.unloaded_idx = unloaded_idx
        self.manufacturer = self.fil_man.get_material_info(guid, "./m:metadata/m:name/m:brand")
        self.filament_type = self.fil_man.get_material_info(guid, "./m:metadata/m:name/m:material")
        hex_color = self.fil_man.get_material_info(guid, "./m:metadata/m:color_code")
        self.filament_color = calculate_filament_color(hex_to_rgb(hex_color)) + [1]
        super(FilamentPopup, self).__init__(**kwargs)

    def confirm(self):
        if self.new:
            self.reactor.register_async_callback(
                lambda e: self.fil_man.load(self.extruder_id, amount=self.ids.filament_slider.val/1000., 
                                            guid=self.guid, unloaded_idx=self.unloaded_idx))
        else:
            self.reactor.register_async_callback(
                lambda e: self.fil_man.unload(self.extruder_id))
        self.dismiss()

class FilamentSlider(UltraSlider):
    filament_color = ListProperty([0,0,0,0])
    active = BooleanProperty(True)
    def __init__(self, **kwargs):
        self.val_min = 0
        self.val_max = 1000
        self.unit = "g"
        self.round_to = 0
        super(FilamentSlider, self).__init__(**kwargs)

    def on_touch_down(self, touch):
        if self.initialized\
        and self.active\
        and touch.pos[0] > self.px_min - 30 and touch.pos[0] < self.px_max + 30\
        and touch.pos[1] > self.y - 18 and touch.pos[1] < self.top + 18:
            self.pressed = True
            touch.grab(self)
            x = self.apply_bounds(touch.pos[0])
            self.val = self.get_val_from_px(x)
            self.disp = self.get_disp_from_val(self.val)
            if self.btn_last_active is not None: self.btn_last_active[3].active = False
            self.changed = True
            return True
        return super(UltraSlider, self).on_touch_down(touch)


def calculate_filament_color(filament_color):
    """ Calculate filament color thats not to light for text. 
        Also the lightness of an rgb color.
        This is equal to the average between the minimum and
        maximum value."""
    #lightness = 0.5*(max(filament_color) + min(filament_color))
    return [c*0.6 for c in filament_color]

def hex_to_rgb(h):
    """"Converts hex color to rgba float format"""
    return [int(h[i:i + 2], 16) / 255. for i in (1, 3, 5)]
