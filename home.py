# coding: utf-8
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import ListProperty, NumericProperty, StringProperty, BooleanProperty, ObjectProperty
from kivy.uix.widget import Widget

from .elements import BaseButton, BtnSlider, BasePopup, UltraSlider
from . import parameters as p

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
        fm = app.filament_manager

        self.buttons = [[0, 0, "Off", None]] #[value, pos_offset, text, instance]
        if self.tool_id == 'B':
            self.val_min = 30
            self.val_max = 140
            if fm:
                loaded_material = fm.get_status()['loaded']
                for material in loaded_material:
                    if material['guid']:
                        material_type = fm.get_info(material['guid'], "./m:metadata/m:name/m:material", "")
                        bed_temp = fm.get_info(material['guid'], "./m:settings/m:setting[@key='heated bed temperature']", 0)
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
            if fm:
                tool_idx = int(self.tool_id[-1])
                loaded_material = fm.get_status()['loaded']
                if loaded_material[tool_idx]['guid']:
                    material_type = fm.get_info(loaded_material[tool_idx]['guid'], "./m:metadata/m:name/m:material", "")
                    ext_temp = fm.get_info(loaded_material[tool_idx]['guid'],"./m:settings/m:setting[@key='print temperature']", 0)
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
            s = "Off"
        else:
            s = f"{self.val}°C"
        return s

    def get_px_from_val(self, val):
        x = ((val-self.val_min)/(self.val_max-self.val_min))*self.width + self.x
        x = max(self.x, x)
        return x

class BtnTriple(Widget):
    filament_amount = NumericProperty()
    filament_color = ListProperty([0,0,0,0])
    title = StringProperty()
    tool_id = StringProperty()
    tool_idx = NumericProperty()
    extruder_id = StringProperty()
    def __init__(self, **kwargs):
        self.app = App.get_running_app()
        try:
            self.app.printer.register_event_handler("filament_manager:material_changed", self.update_material)
            self.app.printer.register_event_handler("klippy:ready", self.update_material)
        except AttributeError:
            pass
        self.app.bind(print_state=self.update_material)
        self.material = {'guid':None, 'amount':0}
        super().__init__(**kwargs)

    def update_material(self, *_):
        self.fm = self.app.filament_manager
        if not self.fm:
            return
        if not self.tool_id: # kv ui not initialized yet
            Clock.schedule_once(self.update_material, 0)
            return
        material = self.fm.get_status()['loaded']
        if len(material) > self.tool_idx:
            self.material = material[self.tool_idx]

        if self.material['guid']:
            material_type = self.fm.get_info(self.material['guid'], "./m:metadata/m:name/m:material", "")
            hex_color = self.fm.get_info(self.material['guid'], "./m:metadata/m:color_code", "#ffffff")
            self.filament_color = calculate_filament_color(hex_to_rgb(hex_color)) + [1]
            self.filament_amount = self.material['amount']
            if self.material['state'] == 'loading':
                self.title = "Loading..."
            elif self.material['state'] == 'unloading':
                self.title = "Unloading..."
            else:
                self.title = f"{self.material['amount']*1000:3.0f}g {material_type}\n(unload)"
        else:
            self.title = "Load Material"
            self.filament_color = (0,0,0,0)

    def load_unload(self):
        if not self.material['guid']:
            FilamentChooserPopup(self.extruder_id).open()
        elif self.material['state'] == 'loaded':
            FilamentPopup(self.extruder_id, False, self.material['guid'], amount=self.material['amount']).open()


class FilamentChooserPopup(BasePopup):
    tab_2 = BooleanProperty(False)
    sel = ListProperty()
    sel_2 = ListProperty()
    def __init__(self, extruder_id, **kwargs):
        self.app = App.get_running_app()
        self.fm = self.app.filament_manager
        self.extruder_id = extruder_id
        self.show_more = [False, False, False]
        self.sel = [None, None, None, None] # selected [type, manufacturer, color, guid]
        self.sel_2 = [None, None, None] # selected [amount, idx, guid]
        self.widgets = [[], [], []]
        super().__init__(**kwargs)
        Clock.schedule_once(self.draw_options, 0)

    def draw_options(self, dt=None, change_level=0):
        """ (re)draw material library from filament_manager
            this is performance-critical, but instanciating the widgets takes 98% of time ~100ms """
        options = [[], [], []]
        self.sel[3] = None
        self.ids.btn_confirm.text = "Select"
        self.ids.btn_confirm.enabled = False

        # 1. generate options to draw based on selection
        # get material library from filament manager as type-manufacturer-color tree of dicts
        tmc = self.fm.tmc_to_guid

        # always show types
        options = [[{'level':0, 'text':t, 'key':t} for t in list(tmc)], [], []]
        if self.sel[0]:
            # type is selected, show manufacturers
            # autoselect if there's only one manufacturer, or 'Generic' and none is selected
            manufacturers = list(tmc[self.sel[0]])
            if len(manufacturers) == 1:
                self.sel[1] = manufacturers[0]
            elif self.sel[1] is None and 'Generic' in manufacturers:
                self.sel[1] = 'Generic'
            options[1] = [{'level':1, 'text':m, 'color':p.light_gray, 'font_size':p.small_font, 'key':m}
                         for m in manufacturers]
            if self.sel[1]:
                # type and manufacturer is selected, show colors
                # autoselect if there's only one color
                colors = list(tmc[self.sel[0]][self.sel[1]])
                if len(colors) == 1:
                    self.sel[2] = colors[0]
                options[2] = [{'level':2, 'hex_color':c, 'key':c} for c in colors]
                if self.sel[2]:
                    # type and manufacturer and color is selected, we have a material guid
                    self.sel[3] = tmc[self.sel[0]][self.sel[1]][self.sel[2]]
                    self.ids.btn_confirm.text = f"Select {self.sel[1]} {self.sel[0]}"
                    self.ids.btn_confirm.enabled = True

        # sort types by how many manufactures make them
        # tmc[option.text] is the dict of manufacturers for the selected type (e.g. for PLA)
        options[0].sort(key = lambda option: len(tmc[option['key']]), reverse=True)
        # sort manufacturers alphabetically, "Generic" always first
        options[1].sort(key = lambda option: option['text'].lower() if option['text']!='Generic' else '\t')

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
            elif len(options) > i+1: # if next group exists we draw a normal divider
                divider = OptionDivider(self, level=i)
                self.ids.option_stack.add_widget(divider)
                self.widgets[i].append(divider)

    def draw_options_2(self, dt=None):
        """ draw recently unloaded materials from filament_manager """
        self.ids.option_stack.clear_widgets()
        self.ids.btn_confirm.text = "Select"
        self.ids.btn_confirm.enabled = False
        materials = self.fm.get_status()['unloaded']
        for i, material in enumerate(materials):
            self.ids.option_stack.add_widget(Option(
                self, 
                guid=material['guid'],
                amount=material['amount'],
                unloaded_idx=i,
                font_size=p.small_font,
                key=i,
                hex_color=self.fm.get_info(material['guid'], "./m:metadata/m:color_code", "#ffffff"),
                text=self.fm.get_info(material['guid'], './m:metadata/m:name/m:brand', "")+\
                ' '+ self.fm.get_info(material['guid'], './m:metadata/m:name/m:material', "")))
        if self.sel_2:
            self.ids.btn_confirm.enabled = True

    def on_tab_2(self, instance, tab_2):
        if tab_2:
            self.draw_options_2()
        else:
            self.draw_options()

    def do_selection(self, option):
        if self.tab_2:
            self.sel_2 = [option.amount, option.unloaded_idx, option.guid]
            self.draw_options_2()
        else:
            for i in range(option.level + 1, len(self.sel)):
                self.sel[i] = None
            self.sel[option.level] = option.key
            self.draw_options(change_level=option.level + 1)

    def confirm(self):
        if self.tab_2:
            FilamentPopup(self.extruder_id, True, self.sel_2[2], unloaded_idx=self.sel_2[1], amount=self.sel_2[0]).open()
        else:
            FilamentPopup(self.extruder_id, True, self.sel[3]).open()
        self.dismiss()

class Option(BaseButton):
    selected = BooleanProperty(False)
    def __init__(self, filamentchooser, key, hex_color=None, amount=1, unloaded_idx=None, 
                level=0, guid=None, font_size=p.normal_font-2, color=(1,1,1,1), **kwargs):
        self.key = key
        self.filamentchooser = filamentchooser
        self.option_color = (0,0,0,0)
        self.amount = amount
        self.level = level
        self.hex_color = hex_color
        self.guid = guid
        self.unloaded_idx = unloaded_idx
        if hex_color is not None:
            self.option_color = calculate_filament_color(hex_to_rgb(hex_color)) + [1]
        super().__init__(**kwargs)
        self.multiline = True
        self.max_lines = 2
        self.shorten_from = 'right'
        self.font_size = font_size
        self.color = color

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
            # if self.height is 0 => Options are hidden (we might set True = True...)
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
    """ this shows info, and an amount slider on a material coming from one of 3 sources:
        - chosen from library       (extruder_id, new=True, guid)
        - from unloaded materials   (extruder_id, new=True, guid, amount, unloaded_idx)
        - currently loaded material (extruder_id, new=False, guid, amount) """
    amount = NumericProperty(1)
    def __init__(self, extruder_id, new, guid, amount=1, unloaded_idx=None, **kwargs):
        self.app = App.get_running_app()
        self.fm = self.app.filament_manager
        self.reactor = self.app.reactor
        self.extruder_id = extruder_id
        self.new = new # set wether the popup is for loading a new material or unloading
        self.guid = guid
        self.amount = amount
        self.unloaded_idx = unloaded_idx
        self.filament_type = self.fm.get_info(guid, "./m:metadata/m:name/m:material", "")
        self.manufacturer = self.fm.get_info(guid, "./m:metadata/m:name/m:brand", "")
        hex_color = self.fm.get_info(guid, "./m:metadata/m:color_code", "#ffffff")
        self.filament_color = calculate_filament_color(hex_to_rgb(hex_color)) + [1]
        super().__init__(**kwargs)

    def confirm(self):
        if self.new:
            self.reactor.register_async_callback(
                lambda e: self.fm.load(self.extruder_id, guid=self.guid,
                amount=self.ids.filament_slider.val/1000, unloaded_idx=self.unloaded_idx))
        else:
            self.reactor.register_async_callback(
                lambda e: self.fm.unload(self.extruder_id))
        self.dismiss()


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


def calculate_filament_color(filament_color):
    """ Calculate filament color thats not to light for text. 
        Also the lightness of an rgb color.
        This is equal to the average between the minimum and
        maximum value."""
    #lightness = 0.5*(max(filament_color) + min(filament_color))
    return [c*0.6 for c in filament_color]

def hex_to_rgb(h):
    """ Converts hex color to rgba float format
        accepts strings like '#ffffff' or "#FFFFFF" """
    return [int(h[i:i + 2], 16) / 255. for i in (1, 3, 5)]
