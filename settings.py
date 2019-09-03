from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.properties import ListProperty, StringProperty, ObjectProperty
from kivy.clock import Clock
#Only for test, will be removed later
import time


class SetItem(FloatLayout):
    pass

class WifiNetwork(SetItem):
    ssid = StringProperty()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.popup = PasswordPopup(ssid=self.ssid)
            self.popup.open()
            return True
        return super(WifiNetwork, self).on_touch_down(touch)

class WifiScreen(Screen):

    ssid_list = ListProperty()
    
    def __init__(self, **kwargs):
        super(WifiScreen, self).__init__(**kwargs)
        # Amount of seconds between wifi rescans in seconds
        self.freq = 30

    def on_pre_enter(self):
        # pre_enter: This function is executed when the animation starts
        Clock.schedule_once(self.get_ssid_list, -1)
        self.update_clock = Clock.schedule_interval(self.get_ssid_list, self.freq)

    def on_leave(self):
        Clock.unschedule(self.update_clock)

    def on_ssid_list(self, instance, val):
        # Repopulate the list of networks when self.ssid_list changes
        box = self.ids.wifi_box
        box.clear_widgets()
        for i in val:
            entry = WifiNetwork()
            entry.ssid = i
            box.add_widget(entry)

    def get_ssid_list(self, dt):
        # on_ssid_list() is only called when this list is different to the previous list
        hms = time.strftime("%H:%M:%S")
        s = int(time.time())%7 + 2
        names = []
        for i in range(s):
            names.append(hms+'.'+str(i))
        print names
        self.ssid_list = names

class PasswordPopup(Popup):
    
    password = StringProperty()
    txt_input = ObjectProperty(None)
    
    def __init__(self, ssid, **kwargs):
        self.ssid = ssid
        self.title = ssid
        super(PasswordPopup, self).__init__(**kwargs)
        self.txt_input.bind(on_text_validate=self.connect)

    def connect(self, instance=None):
        self.dismiss()
        self.password = self.txt_input.text
        print self.password


#DEPRECATED
#    def on_touch_up(self, touch):
#        if self.collide_point(*touch.pos):
#            popup = SsidList()
#            popup.open()
#            return True

#class SsidList(Popup):
#    
#    ssid_list = ListProperty()
#    
#    def __init__(self, **kwargs):
#        self.title = 'Wifi'
#        self.get_content()
#        super(SsidList, self).__init__(title=self.title, content=self.content, **kwargs)
#
#    def get_content(self):
#        scroll = ScrollView(size_hint = (1, None))
#        box = BoxLayout(orientation = 'vertical', size_hint_y = None)
#        
#        for i in self.get_ssid_list():
#            label = Label(text = i)
#            label.size_hint_y = None
#            label.height = 100
#            box.add_widget(label)
#
#        box.height = box.minimum_height
#        scroll.add_widget(box)
#        self.content = scroll 
#
#
#    def get_ssid_list(self):
#        self.ssid_list = ['wifi1', 'wifi2', 'wifi3', 'wifi4']
#        return self.ssid_list      
#
