from os.path import dirname, expanduser, join
kgui_dir = dirname(__file__)
sdcard_path = expanduser('~/sdcard')
history_file = join(sdcard_path, ".history.json")

#never assume pixels are square :}
disp_vertical_stretch = 1.05

large_font = 32
normal_font = 23
small_font = 17
extra_small_font = 14
screen_width = 600
screen_height = 1024
mars = 1.1 * screen_height
radius = 10
icon_radius = 4.5
popup_radius = 15
status_bar_height = 29
btn_height = 80
btn_stop = 65
progress_bar_height = 10
tab_height = 100
#generate even spacing based on all contents on homescreen
small_padding = 15
btn_divider_padding = 8
padding = (screen_height\
        - status_bar_height\
        - btn_height*6\
        - btn_stop\
        - progress_bar_height\
        - tab_height)\
        /float(7)#remaining space has to contain 9* padding and 1* hpadding
notification_padding = status_bar_height
notification_text_padding = 20
btn_spacing = padding + btn_height
h_padding = padding*disp_vertical_stretch
btn_temp_width = 158
btn_width = screen_width - 3*h_padding - btn_temp_width

background = [0.065,0.065,0.065,1]
notification_shadow = (0.065, 0.065, 0.065, 0.6) #doesnt do anything
popup = (0.15,0.15,0.15,1)
divider = (1,1,1,0.09)
btn = (1,1,1,0.08)
btn_outline = (1,1,1,0.095)
btn_disabled = (1,1,1,0.35)
nozzle = (0.15, 0.15, 0.15, 1)
nozzle_selected = (0.3, 0.3, 0.3, 1)

translucent_white = (1,1,1,0.1)
accent = (0.15,0.4,0.45,1)
flat_accent = (0.24,0.34,0.36,0.8)
red = (0.83,0.05,0,1)
green = (0,1,0.25,1)
medium_dark_gray = (0.15, 0.15, 0.15, 1)
medium_gray = (0.2,0.2,0.2,1)
medium_light_gray = (0.35,0.35,0.35,1)
light_gray = (0.7,0.7,0.7,1)

notify_info = (0.28,0.28,0.28,0.65)
notify_warning = (0.44,0.31,0.11,0.7)
notify_error = (0.6,0.1,0.1,0.8)
notify_success = (0.1,0.4,0.2,0.8)


"""
Kivy Guide
https://blog.kivy.org/2019/06/widget-interactions-between-python-and-kv/
Screens (of screenmanager) are relative Layouts (new root for coordinate system)
setting properties of parent class in kv rules doesnt work if they are assigned to a value in parent rule
Defining Properties in kv is often bad since it happens too late, and prohibits setting them in __init__
LABELS: try setting hints to None if it does shit e.g. setting size doesnt work
    size: outer dimensions of the label widget, available space, can be set to texture_size to show everything
    text_size: can be set to limit texture size e.g. cut off text, can be set to size to show all that fits bounding box for text
    texture_size: size of the actual text not cut off(outer dimensions), can set font_size
    always size_hint: None, None when setting size: needed
    halign or valign set position of text within text_size
in canvas: e.g. self.*** acceses the 'parent' widget of the canvas, unlike in other child Instances like Label:
pos: coordinates are always relative to the innermost Layout, not Widget you are in
Widgets: always define size first then pos at least when using top or right.. x:
Never Put comments after canvas: Instruction
f-strings in kv are not reevaluated if properties change, format() is
How to access Instances or their methods:
    in kv to on_propertychange: id.method() id can be bound within root widget
    in py someinstance.bind(someinstances on_propertychange = self.method_to_bind) passes instance and every property
    by instantiating in python, storing instance
    in python self.ids["id"].method() instances of child widges can be accessed by id (ids is dict with instance as value)
THREAD SAFETY: 
    Clock methods (e.g. Clock.schedule_once()) are thread safe, can be used do execute methods in Kivy thread from somewhere else
    reactor.register_async_callback should also be thread safe, since it uses a Queue
    Simple Assignments are thread safe because of GIL
"""



