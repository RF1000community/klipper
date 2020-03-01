import urllib2 # is called urllib.request for py3
import json

import logging
import os, time

from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.properties import ListProperty, ObjectProperty, NumericProperty, DictProperty, StringProperty, BooleanProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.screenmanager import Screen

from elements import *
from settings import SetItem
import parameters as p


class UpdateScreen(Screen):
    def __init__(self, **kwargs):
        super(UpdateScreen, self).__init__(**kwargs)
        Clock.schedule_once(self.draw_releases, 0)

    def download(self, url):
        CHUNK_SIZE=8192
        response = urllib2.urlopen(url)
        total_size = response.info().getheader('Content-Length').strip()
        total_size = int(total_size)
        bytes_so_far = 0
        data = []

        # download chunks
        while 1:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            bytes_so_far += len(chunk)
            data += chunk

            print("got {:3.0f}%".format(100*bytes_so_far/float(total_size)))

        return "".join(data)

    def draw_releases(self, dt):
        url = "https://api.github.com/repos/D4SK/klipperui/releases"
        releases = self.download(url)
        releases = json.JSONDecoder().decode(releases)
        self.ids.box.clear_widgets()
     
        for release in releases:
            entry = SI_Release(release['zipball_url'], left_title = release['tag_name'], right_title = release['published_at'].split("T")[0])
            self.ids.box.add_widget(entry)

class SI_Release(SetItem):
    def __init__(self, url, **kwargs):
        super(SI_Release, self).__init__(**kwargs)
        self.url = url