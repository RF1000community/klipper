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
    pass
class Btn_Play(RoundButton):
    pass
class Btn(RoundButton):
    pass
class Btn_Outline(RoundButton):
    pass
class Btn_Temp(RoundButton):
    pass
class Btn_Arrow(RoundButton):
    pass

class Btn_Triple(Widget):
    pass
class Btn_TripleZ(Widget):
    pass
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
