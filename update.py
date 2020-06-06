import logging

from kivy.clock import Clock
from kivy.uix.screenmanager import Screen

from .elements import Divider, BasePopup
from .git_update import githelper
from . import parameters as p
from .settings import SetItem


class SIUpdate(SetItem):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.right_title = githelper.get_current_version()

class UpdateScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.githelper = githelper
        # Avoid rebuilding the screen on every entry
        Clock.schedule_once(self.draw_releases, 0)

    def draw_releases(self, *args):
        self.ids.box.clear_widgets()
        self.ids.box.add_widget(Divider(pos_hint={'center_x':0.5}))

        releases = self.githelper.get_releases()
        for release in self.githelper.get_releases():
            self.ids.box.add_widget(SIRelease(release))


class UpdatePopup(BasePopup):

    def __init__(self, release, **kwargs):
        self.release = release
        super().__init__(**kwargs)

    def update(self):
        self.release.install()
        self.dismiss()
        ip = InstallPopup()
        ip.open()


class InstallPopup(BasePopup):

    def __init__(self, **kwargs):
        githelper.bind(install_output=self.update)
        super().__init__(**kwargs)

    def update(self, instance, value):
        self.ids.output_label.text = value

class SIRelease(SetItem):

    def __init__(self, release, **kwargs):
        self.release = release
        super().__init__(**kwargs)
        self.left_title = self.release.version
        self.right_title = str(self.release.date)

    def on_release(self, **kwargs):
        super().on_release(**kwargs)
        UpdatePopup(self.release).open()
