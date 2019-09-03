from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen#, Screenmanager
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.properties import ListProperty, StringProperty
from kivy.clock import Clock


class SetItem(FloatLayout):
    pass

class SettingWifi(SetItem):
    ssid = StringProperty()

class WifiScreen(Screen):
    
    def __init__(self, **kwargs):
        super(WifiScreen, self).__init__(**kwargs)
        print(self.size, self.pos)
        Clock.schedule_once(self.update, 1)


    def update(self, dt):
        self.get_ssid_list()
        for i in self.ssid_list:
            entry = SettingWifi()
            entry.ssid = i
            self.ids['wifi_box'].add_widget(entry)



    def get_ssid_list(self):
        # Mockup list
        self.ssid_list = ['wifi1', 'wifi2', 'wifi3', 'wifi4']



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
