import os
import subprocess

from kivy.clock import Clock
from kivy.event import EventDispatcher

from elements import ErrorPopup
import parameters as p

KLIPPER_DIR = os.path.dirname(os.path.dirname(os.path.dirname(p.kgui_dir)))

class GitHelper(EventDispatcher):

    REMOTE = "origin"
    # Filter tags that are considered a release
    # TODO change to differentiate klipper and klipperui releases
    #      maybe prepend "kgui" or "release" instead of "v"?
    RELEASES = "v*"

    def __init__(self):
        # Use klipperui repository and no pager (-P)
        self._base_cmd = ["git", "-C", KLIPPER_DIR, "-P"]
        self._install_process = None

        # Events
        # Dispatched whenever an installation is finished, succesfully or not
        self.register_event_type("on_install_finished")

    def _execute(self, cmd):
        """Execute a git command, and return its stdout
        This function blocks until git returns
        """
        cmd = self._base_cmd + cmd
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return proc.stdout

    def get_current_verion(self):
        cmd = ["describe", "--tags", "--dirty"]
        version = self._execute(cmd)
        # Strip v in beginning and newline on end
        version = version[len(self.RELEASES)-1:].rstrip()
        return version

    def get_exact_version(self):
        """Return only the exact version
        must match one of get_release()
        """
        cmd = ["describe", "--tags", "--exact-match", "--match", RELEASES]
        try:
            version = self._execute(cmd)
        except subprocess.CalledProcessError:
            return None
        else:
            return version

    def get_releases(self):
        """Return a list of all tags describing releases, sorted by newest first"""
        cmd = ["tag", "--list", "--sort=-version:refname", self.RELEASES]
        return self._execute(cmd).splitlines()

    def install_release(self, release):
        """Change working directory to the release and execute the install script"""
        cmd = ["checkout", "--detach", release]
        self._install()

    def _install(self):
        """Run the installation script"""
        if self._install_process is not None: # Install is currently running
            logging.warning("Updater: Attempted to install while script is running")
            return
        cmd = os.path.join(KLIPPER_DIR, "scripts/install-kgui.sh")
        # Capture both stderr and stdout in stdout
        self._install_process = Popen(cmd, capture_output=True, text=True,
                stderr=subprocess.STDOUT)
        Clock.schedule_once(self._poll_install_process, 0.5)

    def _poll_install_process(self):
        """Keep track of when the installation is finished and if it succeded"""
        #TODO: Live display of status outputs in GUI maybe
        if self._install_process.poll() is not None:
            self.dispatch("on_install_finished")
            if self._install_process.returncode > 0:
                # Error occured
                ErrorPopup(title="Installation Error", message=self._install_process.stdout)
            self._install_process = None
        else: # Still running, check again in 0.5 seconds
            Clock.schedule_once(self._poll_install_process, 0.5)

    def on_install_finished(self):
        pass
