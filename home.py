# coding: utf-8

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.properties import ListProperty, StringProperty, ObjectProperty, BooleanProperty
from kivy.clock import Clock
from kivy.uix.widget import Widget
from elements import *
#  self.ids.big_button.text = "
from kivy.graphics.vertex_instructions import RoundedRectangle, Ellipse, Line
from kivy.graphics.context_instructions import Color
import parameters as p

import random


class Btn_Stop(RoundButton):
    def stop(self):
        print("stop print")
class Btn_Play(RoundButton):
    def play(self):
        print("start printing")
    def pause(self):
        print("pause print")
class Btn(RoundButton):
    pass
class Btn_Outline(RoundButton):
    def calibrate(self):
        print("OnCalibrate")
class Btn_Temp(RoundButton):
    pass
class Btn_Arrow(RoundButton):
    pass
class Btn_Triple(Widget):
    pass
class Btn_TripleZ(Widget):
    def up(self):
        print("move Z up")
    def down(self):
        print("move Z down")
    def stop(self):
        print("stop Z")
    def home(self):
        print("Home Z Axis")
class XyField(Widget):

    mm_pos = ListProperty()
    display = StringProperty()

    def __init__(self, **kwargs):
        super(XyField, self).__init__(**kwargs)
        self.point_radius = 10
        self.point_color = [1, 1, 1, 1]
        self.line_color = 1,1,1,0.5
        self.background_color = p.button
        self.mm_pos = [0, 0]
        #Probably temporary
        self.printer_dimensions = [random.randint(50, 2000), random.randint(50, 2000)]
        print(self.printer_dimensions)

        Clock.schedule_once(self.init_drawing, 0)

    def init_drawing(self, dt):
        with self.canvas:
            Color(rgba=self.background_color)
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[p.radius,])
            
            Color(rgba=self.line_color)
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
            self.update_pos(touch.pos)
            return True

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self.update_pos(touch.pos)
            return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self.update_pos(touch.pos)
            self.hide_lines()
            return True

    def update_pos(self, pos):
        x = int(pos[0])
        y = int(pos[1])
        x, y = self.check_bounds(x, y)
        self.update_drawing(x, y)
        self.get_mm_pos(x, y)

    def check_bounds(self, x, y):
        if x < self.origin[0]:
            x = self.origin[0]
        elif x > self.limits[0]:
            x = self.limits[0]

        if y < self.origin[1]:
            y = self.origin[1]
        elif y > self.limits[1]:
            y = self.limits[1]

        return x, y
        
    def update_drawing(self, x, y):
        self.line_x.points=[x, self.y, x, self.top]
        self.line_y.points=[self.x, y, self.right, y]
        self.point.pos=[x-self.point_radius, y-self.point_radius]

    def hide_lines(self):
        self.line_x.points=[0, 0]
        self.line_y.points=[0, 0]

    def get_mm_pos(self, x, y):
        #Convert to float to avoid python2 integer division
        ratio_x = float(x - self.origin[0]) / (self.limits[0] - self.origin[0])
        ratio_y = float(y - self.origin[1]) / (self.limits[1] - self.origin[1])
        
        self.mm_pos = [self.printer_dimensions[0] * ratio_x, 
                       self.printer_dimensions[1] * ratio_y]

    def on_mm_pos(self, instance, value):
        self.display = 'X: {:.0f}mm  Y: {:.0f}mm'.format(*value)


class TempSlider(UltraSlider):
    def init_drawing(self, dt):
        self.buttons = [[0,14,"Off",None],[70,0,"PLA\ncold pull",None],[90,-68/2,"ABS/PETG\ncold pull",None],[210,68/2,"PLA",None],[230,0,"PETG",None],[250,-68/2,"ABS",None]]
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
            s = "{}°C".format(self.val)
        return s
    def get_px_from_val(self, val):
        x = (float(val-40)/float(280-40))*self.px_width+self.px_min
        if x < self.px_min: x = self.px_min
        return x
    def send_temp_B(self):
        print("Sent Temp of {} to nozzle".format(self.val))
    def recieve_temp_B(self):
        self.val = 0