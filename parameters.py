large_font = 34
normal_font = 20
small_font = 17
extra_small_font = 14
screen_width = 600
screen_height = 1024
padding = 50
padding_hint = padding/screen_width
radius = 5
popup_radius = 12



background = [0.1,0.1,0.1,1]
popup = 0.15,0.15,0.15,1
divider = 1,1,1,0.2
button = 1,1,1,0.1
button_outline = 1,1,1,0.2
medium_gray = [0.2,0.2,0.2,1]
medium_light_gray = [0.35,0.35,0.35,1]
light_gray = [0.7,0.7,0.7,1]
translucent_white = 1,1,1,0.1
accent = [0.2, 0.71, 0.9, 1]
red = 0.9,0,0,1


# The default directory of the filechooser
fc_starting_path = '~/'


#Kivy Guide
#LABELS: try setting hints to None if it does shit e.g. setting size doesnt work
    # size: outer dimensions of the label widget, available space, can be set to texture_size to show everything 
    # text_size: can be set to limit texture size e.g. cut off text, can be set to size to show all that fits, 
    # texture_size: size of the actual text not cut off(outer dimensions), can set font_size
    # always size_hint: None, None when setting size: needed
# in canvas: e.g. self.*** acceses the 'parent' widget of the canvas, unlike in other child Instances like Label:
# pos: coordinates are always relative to the innermost Layout, not Widget you are in
# Widgets: always define size first then pos at least when using top or right.. x:
