from kivy.app import App
from kivy.uix.screenmanager import Screen

from .elements import Divider, BasePopup
from .git_update import GitHelper
from . import parameters as p
from .settings import SetItem


class SIUpdate(SetItem):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.right_title = GitHelper().get_current_version()

class UpdateScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.githelper = GitHelper()

    def on_pre_enter(self):
        self.draw_releases()
        return #FIXME fetch in background
        if self.githelper.fetch() is False:
            App.get_running_app().notify.show(
                    "Couldn't fetch new updates",
                    "Check your internet connection and try again",
                    level="info", delay=4)

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

class InstallPopup(BasePopup):

    def __init__(self):
        pass


class SIRelease(SetItem):

    def __init__(self, release):
        self.release = release
        super().__init__(**kwargs)

    def on_release(self, **kwargs):
        super().on_release(**kwargs)
        UpdatePopup(self.release).open()
