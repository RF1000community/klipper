import os
import subprocess

from kivy.clock import Clock
from kivy.event import EventDispatcher

from elements import ErrorPopup
import parameters as p

class GitHelper(EventDispatcher):
    # TODO: git fetch
    #       branches

    REMOTE = "origin"
    INSTALL_SCRIPT = os.path.join(p.klipper_dir, "scripts/install-kgui.sh")
    # Filter tags that are considered a release
    # TODO change to differentiate klipper and klipperui releases
    #      maybe prepend "kgui" or "release" instead of "v"?
    RELEASES = "v*"

    def __init__(self):
        # Use klipperui repository and no pager (-P)
        self._base_cmd = ["git", "-C", p.klipper_dir, "-P"]
        self._install_process = None

        # Dispatched whenever an installation is finished, succesfully or not
        self.register_event_type("on_install_finished")

    def _execute(self, cmd):
        """Execute a git command, and return its stdout
        This function blocks until git returns
        """
        cmd = self._base_cmd + cmd
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # The output always ends with a newline, we don't want that
        return proc.stdout.rstrip()

    def get_git_version(self):
        """Return the git version number"""
        git_version = self._execute(["--version"])
        # Strip prefix "git version " from output
        if git_version.startswith("git version "):
            git_version = git_version[12:]
        return git_version

    def get_current_version(self):
        """Get version with commit info if not on tagged commit, mostly useful for displaying"""
        cmd = ["describe", "--tags", "--dirty"]
        version = self._execute(cmd)
        # Strip v in beginning
        version = version[len(self.RELEASES)-1:]
        return version

    def get_exact_version(self):
        """Return only the exact version
        must match one of get_release()
        If not on release commit, return None
        """
        cmd = ["describe", "--tags", "--exact-match", "--match", self.RELEASES]
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
        # Capture both stderr and stdout in stdout
        self._install_process = Popen(self.INSTALL_SCRIPT, capture_output=True,
                text=True, stderr=subprocess.STDOUT)
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
