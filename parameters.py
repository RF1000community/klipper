large_font = 30
normal_font = 20
small_font = 17
extra_small_font = 14

side_padding = 50
radius = 5

screen_width = 600
screen_height = 1024

background = [0.1,0.1,0.1,1]
medium_gray = [0.2,0.2,0.2,1]
medium_light_gray = [0.4,0.4,0.4,1]
light_gray = [0.7,0.7,0.7,1]
translucent_white = 1,1,1,0.1
red = 1,0,0,1


#Kivy Guide
#LABELS: try setting hints to None if it does shit e.g. setting size doesnt work
    # size: outer dimensions of the label widget, available space, can be set to texture_size to show everything 
    # text_size: can be set to limit texture size e.g. cut off text, can be set to size to show all that fits, 
    # texture_size: size of the actual text not cut off(outer dimensions), can set font_size
# in canvas: e.g. self.*** acceses the 'parent' widget of the canvas, unlike in other child Instances like Label:
# pos: coordinates are always relative to the innermost Layout, not Widget you are in