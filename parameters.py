from os.path import dirname, expanduser, join
from kivy.config import Config
from kivy.metrics import dp, sp
screen_width = Config.getint('graphics', 'width')
screen_height = Config.getint('graphics', 'height')

# the real dp() and sp() functions somehow dont work here
def dp(val):
     return int(val * screen_width/600)
sp = dp

kgui_dir = dirname(__file__)
klipper_dir = dirname(dirname(dirname(kgui_dir)))
sdcard_path = expanduser('~/Files')
usb_mount_dir = 'USB-Device'
history_file = join(sdcard_path, ".history.json")

#never assume pixels are square :}
disp_vertical_stretch = 1.05
large_font = sp(32)
normal_font = sp(23)
small_font = sp(17)
extra_small_font = sp(14)
mars = 1.1 * screen_height
radius = dp(10)
icon_radius = dp(4.5)
popup_radius = dp(15)
status_bar_height = dp(29)
btn_height = dp(80)
btn_stop = dp(65)
progress_bar_height = dp(10)
tab_height = dp(100)
#generate even spacing based on all contents on homescreen
small_padding = dp(15)
btn_divider_padding = dp(8)
padding = (screen_height\
        - status_bar_height\
        - btn_height*6\
        - btn_stop\
        - progress_bar_height\
        - tab_height)\
        /7 # remaining space has to contain 7* padding
notification_padding = status_bar_height
notification_text_padding = dp(20)
btn_spacing = padding + btn_height
h_padding = padding*disp_vertical_stretch
btn_temp_width = dp(158)
btn_width = screen_width - 3*h_padding - btn_temp_width

background = [0.065, 0.065, 0.065, 1]
notification_shadow = (0.065, 0.065, 0.065, 0.45)
floating_button_shadow = (0.03, 0.03, 0.03, 0.4)
popup = (0.15, 0.15, 0.15, 1)
divider = (1, 1, 1, 0.09)
btn = [1, 1, 1, 0.08]
btn_outline = (1, 1, 1, 0.095)
btn_disabled = (1, 1, 1, 0.35)
nozzle = (0.15, 0.15, 0.15, 1)
nozzle_selected = (0.3, 0.3, 0.3, 1)

translucent_white = (1, 1, 1, 0.1)
accent = (0.15, 0.4, 0.45, 1)
flat_accent = (0.24, 0.34, 0.36, 0.8)
red = (0.72, 0, 0.08, 1)
green = (0, 1, 0.25, 1)
medium_dark_gray = (0.15, 0.15, 0.15, 1)
medium_gray = (0.2, 0.2, 0.2, 1)
medium_light_gray = [0.35, 0.35, 0.35, 1]
light_gray = [0.7, 0.7, 0.7, 1]

notify_info = (0.28, 0.28, 0.28, 0.65)
notify_warning = (0.44, 0.31, 0.11, 0.7)
notify_error = (0.6, 0.1, 0.1, 0.8)
notify_success = (0.1, 0.4, 0.2, 0.8)
