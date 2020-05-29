import os
import subprocess

from kivy.clock import Clock
from kivy.event import EventDispatcher

from .elements import ErrorPopup
from . import parameters as p

class GitHelper(EventDispatcher):
    # TODO: git fetch
    #       branches

    # If you want to receive updates from a different remote, change this value
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

    def _execute(self, cmd, catch=True):
        """Execute a git command, and return its stdout
        This function blocks until git returns
        """
        cmd = self._base_cmd + cmd
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            if not catch:
                raise
            #ErrorPopup(title="Git failed", proc.stdout + "\n" + proc.stderr).open()
            print(proc.stdout, proc.stderr)
        # The output always ends with a newline, we don't want that
        return proc.stdout.rstrip()

    def fetch(self):
        cmd = ["fetch", "--recurse-submodules", self.REMOTE]
        self._execute(cmd)

    def get_git_version(self):
        """Return the git version number"""
        git_version = self._execute(["--version"])
        # Strip prefix "git version " from output
        if git_version.startswith("git version "):
            git_version = git_version[12:]
        return git_version

    def get_current_version(self):
        """Get version with commit info if not on tagged commit
        mostly useful for displaying
        """
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
            version = self._execute(cmd, catch=False)
        except subprocess.CalledProcessError:
            return None
        else:
            return version

    def get_nearest_version(self, commitish):
        cmd = ["describe", "--tags", "--abbrev=0", "--match", self.RELEASES, commitish]
        return self._execute(cmd)

    def get_releases(self):
        """Return a list of all releases, sorted by newest first"""
        cmd = ["for-each-ref", "--sort=-version:refname", "--python",
               "--format=(%(refname:strip=-1), %(committerdate:unix))",
               "refs/tags/" + self.RELEASES]
        data = self._execute(cmd).splitlines()
        releases = []
        for e in data:
            tag, timestamp = eval(e)
            version = tag[len(self.RELEASES)-1:]
            rel = Release(name=tag, time=int(timestamp), version=version)
            rel.current = tag == self.get_exact_version()
            releases.append(rel)
        return releases

    def get_branches(self):
        cmd = ["for-each-ref", "--sort=-authordate", "--python",
               "--format=(%(refname:strip=-1), %(authordate:unix), %(objectname))",
               "refs/remotes/" + self.REMOTE]
        remote_data = self._execute(cmd).splitlines()
        remote_branches = []
        for e in remote_data:
            name, timestamp, hash_ = eval(e)
            branch = Branch(name=name, time=int(timestamp), commit=hash_)
            remote_branches.append(branch)

        cmd[-1] = "refs/heads"
        local_data = self._execute(cmd).splitlines()
        local_branches = []
        for e in local_data:
            name, timestamp, hash_ = eval(e)
            branch = Branch(name=name, time=int(timestamp), commit=hash_, local=True)
            local_branches.append(branch)
        return (local_branches, remote_branches)

    def install_release(self, release):
        """Change working directory to the release and execute the install script"""
        cmd = ["checkout", "--recurse-submodules", "--detach", release]
        self._install()

    def _install(self):
        """Run the installation script"""
        if self._install_process is not None: # Install is currently running
            logging.warning("Updater: Attempted to install while script is running")
            return
        # Capture both stderr and stdout in stdout
        self._install_process = Popen(["sudo", self.INSTALL_SCRIPT],
                capture_output=True, text=True, stderr=subprocess.STDOUT)
        Clock.schedule_once(self._poll_install_process, 0.5)

    def _poll_install_process(self):
        """Keep track of when the installation is finished and if it succeded"""
        #TODO: Live display of status outputs in GUI maybe
        if self._install_process.poll() is not None:
            self.dispatch("on_install_finished")
            if self._install_process.returncode > 0:
                # Error occured
                ErrorPopup(title="Installation Error",
                        message=self._install_process.stdout).open()
            self._install_process = None
        else: # Still running, check again in 0.5 seconds
            Clock.schedule_once(self._poll_install_process, 0.5)

    def on_install_finished(self):
        pass


class Release:
    """A release that corresponds to a tag"""

    def __init__(self, *, name, time, version=None):
        self.name = name
        self.version = version or name
        self.current = False
        self.release_date = time

    def install(self):
        pass


class Branch(Release):
    """A branch that can be installed like a release"""

    def __init__(self, *, commit, local=False, **kwargs):
        self.commit = commit
        self.local = local
        super().__init__(**kwargs)

    def update(self):
        pass
