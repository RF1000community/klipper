# coding: utf-8
from kivy.properties import ListProperty, StringProperty
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.app import App
from kivy.graphics.vertex_instructions import RoundedRectangle, Ellipse, Line
from kivy.graphics.context_instructions import Color
import logging
from elements import *
import parameters as p

import random


class XyField(Widget):

    mm_pos = ListProperty([0,0])
    display = StringProperty()
    enabled = BooleanProperty()
    point_color = ListProperty(p.button_disabled)
    def __init__(self, **kwargs):
        super(XyField, self).__init__(**kwargs)
        self.point_radius = 10
        self.app = App.get_running_app()
        #self.bind(enabled=self.setter('app.printer_objects_available'))
        if not self.app.testing: self.printer_dimensions = (self.app.pos_max[0]-self.app.pos_min[0], self.app.pos_max[1]-self.app.pos_min[1])
        else: self.printer_dimensions = (777,777)
        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt):
        with self.canvas:
            Color(rgba=p.button_outline)
            self.bg_rect = Line(width=1, rounded_rectangle=(self.x, self.y, self.width, self.height, p.radius))
            
            Color(rgba=p.button_outline)
            #Vertical line, 
            self.line_x = Line(points=[0, 0])
            #Horizontal line
            self.line_y = Line(points=[0, 0])

            Color(rgba=self.point_color)
            self.point = Ellipse(pos=self.pos, size=2*[self.point_radius*2])
            
        #Calculate bounds of actual field
        self.origin = [self.x+self.point_radius, self.y+self.point_radius]
        self.limits = [self.right-self.point_radius, self.top-self.point_radius]

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            self.update_with_px(touch.pos)
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
            self.hide_lines()
            return True
        return False

    def update_with_px(self, pos):
        if self.enabled:
            pos = (int(pos[0]), int(pos[1]))
            pos = self.update_drawing(pos[0],pos[1])
            self.get_mm_pos(pos)
            self.app.send_xyz(x=self.mm_pos[0], y=self.mm_pos[1])

    def update_with_mm(self, mm):
        self.update_drawing(self.get_px_pos(mm))
        self.mm_pos = mm
   
    def update_drawing(self, x, y):
        if x < self.origin[0]:
            x = self.origin[0]
        elif x > self.limits[0]:
            x = self.limits[0]

        if y < self.origin[1]:
            y = self.origin[1]
        elif y > self.limits[1]:
            y = self.limits[1]

        self.line_x.points=[x, self.y, x, self.top]
        self.line_y.points=[self.x, y, self.right, y]
        self.point.pos=[x-self.point_radius, y-self.point_radius]
        return (x, y)

    def hide_lines(self):
        self.line_x.points=[0, 0]
        self.line_y.points=[0, 0]

    def get_mm_pos(self, px):
        #Convert to float to avoid python2 integer division
        ratio_x = float(px[0] - self.origin[0]) / (self.limits[0] - self.origin[0])
        ratio_y = float(px[1] - self.origin[1]) / (self.limits[1] - self.origin[1])
        
        self.mm_pos = [self.printer_dimensions[0] * ratio_x, 
                       self.printer_dimensions[0] * ratio_y]

    def get_px_pos(self, mm):
        self.px = [(self.limits[0] -self.origin[0]) * self.printer_dimensions[0] / float(mm[0]),
                   (self.limits[1] -self.origin[1]) * self.printer_dimensions[1] / float(mm[1])]

    def on_mm_pos(self, instance, value):
        self.display = 'X: {:.0f}mm  Y: {:.0f}mm'.format(*value)

    def on_enabled(self, instance, value):
        logging.info("set point_color@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        if self.enabled: self.point_color = [1,1,1,1]
        else: self.point_color = p.button_disabled

class SpeedSlider(UltraSlider):
    def init_drawing(self, dt):
        self.val = App.get_running_app().recieve_speed()
        self.buttons = [[100,0,"no multiplier",None]]
        super(SpeedSlider, self).init_drawing(dt)

    def get_val_from_px(self, x):
        return int(((x-self.px_min)/(self.px_width))*(500-10)+10)

    def get_disp_from_val(self, val):
        if val == 100:
            self.px = self.get_px_from_val(val)
        return "{}%".format(val)

    def get_px_from_val(self, val):
        return int((float(val-10)/(500-10))*(self.px_width)+self.px_min)

class FlowSlider(UltraSlider):        
    def init_drawing(self, dt):
        self.val = App.get_running_app().recieve_flow()
        self.buttons = [[100,0,"no multiplier",None]]
        super(FlowSlider, self).init_drawing(dt)

    def get_val_from_px(self, x):
        return int(((x-self.px_min)/(self.px_width))*(110-90)+90)

    def get_disp_from_val(self, val):
        if val == 100:
            self.px = self.get_px_from_val(val)
        return "{}%".format(val)

    def get_px_from_val(self, val):
        return int((float(val-90)/(110-90))*(self.px_width)+self.px_min)

class FanSlider(UltraSlider):
    def init_drawing(self, dt):
        self.val = App.get_running_app().recieve_fan()
        self.buttons = []
        super(FanSlider, self).init_drawing(dt)

    def get_val_from_px(self, x):
        return int(((x-self.px_min)/(self.px_width))*(100))

    def get_disp_from_val(self, val):
        return "{}%".format(val)

    def get_px_from_val(self, val):
        return int((float(val)/(100))*(self.px_width)+self.px_min)


class BedTempSlider(UltraSlider):
    def init_drawing(self, dt):
        self.val = App.get_running_app().recieve_temp_bed()
        self.buttons = [[0,0,"Off",None],[60,0,"PLA",None],[90,0,"PETG",None],[110,0,"ABS",None]]
        super(BedTempSlider, self).init_drawing(dt)
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
    def init_drawing(self, dt):
        if   self.creator.idpy == "A": self.val = App.get_running_app().recieve_temp_A()
        elif self.creator.idpy == "B": self.val = App.get_running_app().recieve_temp_A()
        self.buttons = [
            [0,14,"Off",None],[70,0,"PLA\ncold pull",None],[90,-68/2,"ABS/PETG\ncold pull",None],
            [210,68/2,"PLA",None],[230,0,"PETG",None],[250,-68/2,"ABS",None]]
        super(ExtTempSlider, self).init_drawing(dt)
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
