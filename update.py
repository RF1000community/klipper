import logging

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen

from .elements import Divider, BasePopup
from .git_update import githelper
from . import parameters as p
from .settings import SetItem


class SIUpdate(SetItem):
    """Entry in SettingScreen, opens UpdateScreen"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.right_title = githelper.get_current_version()


class UpdateScreen(Screen):
    """Screen listing all releases"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        githelper.bind(releases=self.draw_releases)
        # Avoid rebuilding the screen on every entry
        Clock.schedule_once(self.draw_releases, 0)

    def draw_releases(self, *args):
        self.ids.box.clear_widgets()
        self.ids.box.add_widget(Divider(pos_hint={'center_x':0.5}))
        for release in githelper.releases:
            self.ids.box.add_widget(SIRelease(release))

    def fetch(self):
        githelper.fetch()


class SIRelease(SetItem):
    """Releases as displayed in a list on the UpdateScreen"""

    def __init__(self, release, **kwargs):
        self.release = release
        super().__init__(**kwargs)
        self.left_title = self.release.version
        self.right_title = str(self.release.date)

    def on_release(self, **kwargs):
        super().on_release(**kwargs)
        UpdatePopup(self.release).open()


class UpdatePopup(BasePopup):
    """Dialog with release info and confirmation for installation"""

    def __init__(self, release, **kwargs):
        self.release = release
        super().__init__(**kwargs)

    def install(self):
        self.dismiss()
        InstallPopup().open()
        self.release.install()


class InstallPopup(BasePopup):
    """Popup shown while installing with live stdout display"""

    def __init__(self, **kwargs):
        githelper.bind(install_output=self.update)
        githelper.bind(on_install_finished=self.on_finished)
        super().__init__(**kwargs)

    def update(self, instance, value):
        self.ids.output_label.text = value

    def on_finished(self, instance, returncode):
        """Replace the abort button with reboot prompt"""
        self.ids.content.remove_widget(self.ids.btn_abort)
        if returncode > 0:
            notify = App.get_running_app().notify
            notify.show("Installation failed",
                    f"Installer exited with returncode {returncode}",
                    level="error")
            # Repurpose the "Reboot later" button for exiting
            self.ids.btn_cancel.y = self.y
            self.ids.btn_cancel.width = self.width
            self.ids.btn_cancel.text = "Close"
        else:
            # Theses buttons were previously on mars
            self.ids.btn_cancel.y = self.y
            self.ids.btn_reboot.y = self.y

    def terminate(self):
        githelper.terminate_installation()
