import os
import subprocess
import requests

from os.path import dirname
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen

from . import parameters as p
from .settings import SetItem
from .elements import Divider, BasePopup
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
        self.ids.box.clear_widgets()
        self.ids.box.add_widget(Divider(pos_hint={'center_x':0.5}))

        releases = requests.get("https://api.github.com/repos/D4SK/klipperui/releases")
        if releases.ok:
            releases = releases.json()
            for release in releases:
                self.ids.box.add_widget(SIRelease(release['tag_name'], release['published_at'].split("T")[0]))

        branches = requests.get("https://api.github.com/repos/D4SK/klipperui/branches")
        if branches.ok:
            branches = branches.json()
            for branch in branches:
                self.ids.box.add_widget(SIRelease(branch['name'], "for development only"))

class UpdatePopup(BasePopup):
    def __init__(self, version, details, **kwargs):
        self.version = version
        self.details = details
        super().__init__(**kwargs)

    def update(self):
        # as a convention klipper is always installed in HOME directory
        install_dir = os.path.expanduser('~')
        self.run_in_tty("some update script ")
        # exit klipper to terminal
        App.get_running_app().quit()

    def run_in_tty(self, command):
        #TODO
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    
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
