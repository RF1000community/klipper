import os
import logging
import subprocess
import site
import requests

from os.path import dirname
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.properties import NumericProperty

from . import parameters as p
from .settings import SetItem
from .elements import *
if not "KGUI_TESTING" in os.environ:
    from util import get_git_version

class UpdateScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        #self.klipper_dir = dirname(dirname(dirname(p.kgui_dir)))
        Clock.schedule_once(self.draw_releases, 0)

    def draw_releases(self, dt):
        if not "KGUI_TESTING" in os.environ:
            self.ids.message.text = "You're on Version " + get_git_version()
        response = requests.get("https://api.github.com/repos/D4SK/klipperui/releases")
        if response.ok:
            releases = response.json()
            self.ids.box.clear_widgets()
            self.ids.box.add_widget(Divider(pos_hint={'center_x':0.5}))
            self.ids.box.add_widget(SIRelease("master", "latest beta version"))
            for release in releases:
                self.ids.box.add_widget(SIRelease(release['tag_name'], release['published_at'].split("T")[0]))

    def run_command(command, output_property):
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            elif output:
                current = getattr(self, output_property)
                setattr(self, output_property, current + output)
        rc = process.poll()
        return rc

class UpdatePopup(BasePopup):
    message = StringProperty()
    def __init__(self, version, details, **kwargs):
        super().__init__(**kwargs)
        self.version = version
        self.details = details

    def update(self):
        pass

    def full_install(self):
        # as a convention klipper is always installed in HOME directory
        install_dir = os.path.expanduser('~')
      
    def dismiss(self, **kwargs):
        super().dismiss(**kwargs)

class SIRelease(SetItem):
    def __init__(self, version, details, **kwargs):
        self.version = version
        self.details = details
        self.left_title = version
        self.right_title = details
        super().__init__(**kwargs)

    def on_release(self, **kwargs):
        super().on_release(**kwargs)
        UpdatePopup(self.version, self.details).open()