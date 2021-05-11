import logging

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import ListProperty, NumericProperty, StringProperty, \
    BooleanProperty, DictProperty
from kivy.uix.widget import Widget

from .elements import BaseButton, BasePopup, UltraSlider
from .printer_cmd import hex_to_rgba, calculate_filament_color
from . import parameters as p
from . import printer_cmd


class XyField(Widget):

    pressed = BooleanProperty(False)
    enabled = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.point_radius = 10
        self.app = App.get_running_app()
        self.printer_dimensions = (self.app.pos_max['x'] - self.app.pos_min['x'],
                                   self.app.pos_max['y'] - self.app.pos_min['y'])
        self.app.bind(pos=self.update_with_mm)
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt):
        # Calculate bounds of actual field
        self.origin = [self.x + self.point_radius, self.y + self.point_radius]
        self.limits = [self.right - self.point_radius, self.top - self.point_radius]
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
            self.app.reactor.cb(printer_cmd.send_pos, x=self.mm[0], y=self.mm[1], speed=40)
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
    gcode_id = StringProperty()

    def __init__(self, **kwargs):
        self.btn_last_active = None
        self.initialized = False
        self.app = App.get_running_app()
        super(UltraSlider, self).__init__(**kwargs)
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt=None):
        self.app.reactor.cb(printer_cmd.get_temp)
        self.buttons = [[0, 0, "Off", None]] # [value, pos_offset, text, instance]
        if self.gcode_id == 'B':
            self.val_min = 30
            self.val_max = 140
            if self.app.material:
                loaded_material = self.app.material['loaded']
                for material in loaded_material:
                    if material['guid']:
                        self.buttons.append([float(material['bed_temp']), 0, material['material_type'], None])
            else: # show some generic temperatures
                self.buttons = [
                    [0,0,"Off",None],
                    [60,0,"PLA",None],
                    [90,0,"PETG",None],
                    [110,0,"ABS",None]]
        else:
            self.val_min = 40
            self.val_max = 280
            if self.app.material:
                tool_idx = int(self.gcode_id[-1])
                material = self.app.material['loaded'][tool_idx]
                if material['guid']:
                    self.buttons.append([float(material['print_temp']), 0, material['material_type'], None])
            else:
                self.buttons = [
                    [0,14,"Off",None],
                    [70,0,"PLA\ncold pull",None],
                    [90,-68/2,"ABS/PETG\ncold pull",None],
                    [210,68/2,"PLA",None],
                    [230,0,"PETG",None],
                    [250,-68/2,"ABS",None]]
        super().init_drawing()

    def get_val_from_px(self, x):
        v = int(((x-self.x)/self.width)*(self.val_max-self.val_min)+self.val_min)
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
            return "Off"
        else:
            return f"{self.val:.0f}°C"

    def get_px_from_val(self, val):
        x = ((val-self.val_min)/(self.val_max-self.val_min))*self.width + self.x
        return max(self.x, x)

class BtnTriple(Widget):
    filament_amount = NumericProperty()
    filament_color = ListProperty([0,0,0,0])
    title = StringProperty()
    gcode_id = StringProperty()
    tool_idx = NumericProperty()
    extruder_id = StringProperty()
    material = DictProperty({'guid': None, 'state': "no material", 'amount': 0,
                                'material_type': "", 'hex_color': None, 'brand': ""})

class FilamentChooserPopup(BasePopup):
    sel = ListProperty()
    sel_2 = DictProperty()
    tab_2 = BooleanProperty(False)
    def __init__(self, extruder_id, **kwargs):
        self.app = App.get_running_app()
        self.reactor = self.app.reactor
        self.extruder_id = extruder_id
        self.show_more = [False, False, False]
        self.sel = [None, None, None, None] # selected [type, brand, color, guid]
        self.sel_2 = {}
        self.widgets = [[], [], []]
        super().__init__(**kwargs)
        Clock.schedule_once(self.draw_options, 0)

    def draw_options(self, dt=None, change_level=0):
        """ (re)draw material library from filament_manager
            this is performance-critical, but instanciating the widgets takes 98% of time ~100ms """
        self.sel[3] = None
        self.ids.btn_confirm.text = "Select"
        self.ids.btn_confirm.enabled = False

        # 1. generate options to draw based on selection
        # get material library from filament manager as type-brand-color tree of dicts
        tbc = self.app.tbc_to_guid

        # always show types
        options = [[{'level':0, 'text':t, 'key':t} for t in list(tbc)], [], []]
        if self.sel[0]:
            # type is selected, show brands
            # autoselect if there's only one brand, or 'Generic' and none is selected
            brands = list(tbc[self.sel[0]])
            if len(brands) == 1:
                self.sel[1] = brands[0]
            elif self.sel[1] is None and 'Generic' in brands:
                self.sel[1] = 'Generic'
            options[1] = [{'level':1, 'material':{'brand': m}, 'text':m,'key':m} for m in brands]
            if self.sel[1]:
                # type and brand is selected, show colors
                # autoselect if there's only one color
                colors = list(tbc[self.sel[0]][self.sel[1]])
                if len(colors) == 1:
                    self.sel[2] = colors[0]
                options[2] = [{'level':2, 'material':{'hex_color': c}, 'key':c} for c in colors]
                if self.sel[2]:
                    # type and brand and color is selected, we have a material guid
                    self.sel[3] = tbc[self.sel[0]][self.sel[1]][self.sel[2]]
                    self.ids.btn_confirm.text = f"Select {self.sel[1]} {self.sel[0]}"
                    self.ids.btn_confirm.enabled = True

        # sort types by how many manufactures make them
        # tbc[option['key']] is the dict of brands for the selected type (e.g. for PLA)
        options[0].sort(key = lambda option: len(tbc[option['key']]), reverse=True)
        # sort brands alphabetically, "Generic" always first
        options[1].sort(key = lambda option: option['text'].lower() if option['text'] != 'Generic' else '\t')

        # 2. remove widgets that need to be updated (level >= change_level)
        for i in range(change_level, len(options)):
            for widget in self.widgets[i]:
                self.ids.option_stack.remove_widget(widget)
            self.widgets[i] = []

        # 3. draw new widgets
        for i in range(change_level, len(options)):
            max_amount = 50*self.show_more[i] + (15 if i == 0 else 10)
            # Options
            for option in options[i][:max_amount]:
                widget = Option(self, **option)
                self.ids.option_stack.add_widget(widget)
                self.widgets[i].append(widget)

            # Divider
            if len(options[i]) > max_amount: # hidden options, draw show more divider
                divider = OptionDivider(self, level=i, height=0)
                self.ids.option_stack.add_widget(divider)
                self.widgets[i].append(divider)
            elif len(options) > i + 1: # if next group exists we draw a normal divider
                divider = OptionDivider(self, level=i)
                self.ids.option_stack.add_widget(divider)
                self.widgets[i].append(divider)

    def draw_options_2(self, dt=None):
        """ draw recently unloaded materials from filament_manager """
        self.ids.option_stack.clear_widgets()
        self.ids.btn_confirm.text = "Select"
        self.ids.btn_confirm.enabled = False
        materials = self.app.material['unloaded']
        for i, material in enumerate(materials):
            material['unloaded_idx'] = i
            self.ids.option_stack.add_widget(Option(
                self, material=material, key=material['unloaded_idx'],
                text=material['brand'] + ' ' + material['material_type']))
        if self.sel_2:
            self.ids.btn_confirm.enabled = True

    def on_tab_2(self, instance, tab_2):
        self.ids.option_stack.clear_widgets() # tab1 only adaptively clears its 'own' widgets
        self.widgets = [[], [], []]
        if tab_2:
            self.draw_options_2()
        else:
            self.draw_options()

    def do_selection(self, option):
        if self.tab_2:
            self.sel_2 = option.material
            self.draw_options_2()
        else:
            for i in range(option.level + 1, len(self.sel)):
                self.sel[i] = None
            self.sel[option.level] = option.key
            self.draw_options(change_level=option.level + 1)

    def confirm(self):
        if self.tab_2:
            material = self.sel_2
        else:
            material = {
                'material_type': self.sel[0],
                'brand': self.sel[1],
                'hex_color': self.sel[2],
                'guid': self.sel[3],
                'amount': 1}
        FilamentPopup(self.extruder_id, True, material).open()
        self.dismiss()

class Option(BaseButton):
    selected = BooleanProperty(False)
    def __init__(self, filamentchooser, key, level=0, material={}, **kwargs):
        self.key = key
        self.filamentchooser = filamentchooser
        self.level = level
        self.material = material
        self.multiline = True
        self.max_lines = 2
        self.shorten_from = 'right'
        super().__init__(**kwargs)
        if 'amount' in material:
            self.amount = material['amount']
        if 'hex_color' in material:
            self.option_color = calculate_filament_color(hex_to_rgba(material['hex_color']))
        if 'brand' in material:
            self.font_size = p.small_font
            self.color = p.light_gray

    def on_press(self, *args):
        self.selected = True
        self.filamentchooser.do_selection(self)

class OptionDivider(BaseButton):
    def __init__(self, filamentchooser, level, **kwargs):
        self.level = level
        self.filamentchooser = filamentchooser
        super().__init__(**kwargs)

    def on_touch_down(self, touch):
        if touch.pos[1] > self.y and touch.pos[1] < self.y + self.actual_height:
            # If self.height is 0 => Options are hidden (we might set True = True...)
            if self.height == 0:
                self.filamentchooser.show_more[self.level] = True
            else:
                self.filamentchooser.show_more[self.level] = False
            self.filamentchooser.draw_options()
            return True
        if super().on_touch_down(touch):
            return True
        return False

class FilamentPopup(BasePopup):
    """ This shows info, and an amount slider on a material coming from one of 3 sources:
        - chosen from library       (extruder_id, new=True, material)
        - from unloaded materials   (extruder_id, new=True, material with 'unloaded_idx')
        - currently loaded material (extruder_id, new=False, material) """
    def __init__(self, extruder_id, new, material, **kwargs):
        self.app = App.get_running_app()
        self.reactor = self.app.reactor
        self.extruder_id = extruder_id
        self.new = new # set wether the popup is for loading a new material or unloading
        self.material = material
        self.unloaded_idx = None if not 'unloaded_idx' in material else material['unloaded_idx']
        self.filament_color = calculate_filament_color(hex_to_rgba(material['hex_color']))
        super().__init__(**kwargs)

    def confirm(self):
        if self.new:
            self.reactor.cb(self.load, self.extruder_id, guid=self.material['guid'],
                amount=self.ids.filament_slider.val/1000, unloaded_idx=self.unloaded_idx)
        else:
            self.reactor.cb(self.unload, self.extruder_id)
        self.dismiss()

    @staticmethod
    def load(e, printer, *args, **kwargs):
        printer.objects['filament_manager'].load(*args, **kwargs)
        printer_cmd.get_material(e, printer)

    @staticmethod
    def unload(e, printer, *args, **kwargs):
        printer.objects['filament_manager'].unload(*args, **kwargs)
        printer_cmd.get_material(e, printer)

class FilamentSlider(UltraSlider):

    filament_color = ListProperty([0,0,0,0])
    active = BooleanProperty(True)

    def __init__(self, **kwargs):
        self.val_min = 0
        self.val_max = 1000
        self.unit = "g"
        self.round_to = 0
        super().__init__(**kwargs)

    def on_touch_down(self, touch):
        # overwrite method to add disabling
        if self.active:
            return super().on_touch_down(touch)
        return super(UltraSlider, self).on_touch_down(touch)
