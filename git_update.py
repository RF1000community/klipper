import logging
import os
import subprocess
from threading import Thread

from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import StringProperty, ListProperty

from .elements import ErrorPopup
from . import parameters as p


class GitHelper(EventDispatcher):

    # If you want to receive updates from a different remote, change this value
    REMOTE = "origin"
    INSTALL_SCRIPT = os.path.join(p.klipper_dir, "scripts/install-kgui.sh")
    # Filter tags that are considered a release
    # TODO change to differentiate klipper and klipperui releases
    #      maybe prepend "kgui" or "release" instead of "v"?
    RELEASES = "v*"

    install_output = StringProperty()
    releases = ListProperty()

    def __init__(self):
        # Use klipperui repository and no pager (-P)
        self._base_cmd = ["git", "-C", p.klipper_dir, "-P"]
        self._install_process = None
        self._terminate_installation = False

        # Dispatched whenever an installation is finished, succesfully or not
        self.register_event_type("on_install_finished")
        self.register_event_type("on_fetch_failed")
        self.get_releases()
        # Leave some time after startup in case WiFi isn't connected yet
        self._fetch_retries = 0
        self.fetch_clock = Clock.schedule_once(self.fetch, 15)

    def _execute(self, cmd, ignore_errors=False):
        """Execute a git command, and return its stdout
        This function blocks until git returns.
        In case of an error an error message is displayed,
        unless ignore_errors is set to True.
        """
        cmd = self._base_cmd + cmd
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 and not ignore_errors:
            #ErrorPopup(title="Git failed", proc.stdout + "\n" + proc.stderr).open()
            logging.error("Git: Operation failed: " + " ".join(cmd))
            logging.error("Git: " + proc.stdout + " " + proc.stderr)
        # The output always ends with a newline, we don't want that
        return proc.stdout.rstrip("\n")

    def fetch(self, *args, retries=2):
        # Fetch automatically every 24h = 86400s
        self.fetch_clock.cancel()
        self.fetch_clock = Clock.schedule_once(self.fetch, 86400)

        self._fetch_retries = retries
        logging.info("Git: Fetching updates")
        cmd = self._base_cmd + ["fetch", "--recurse-submodules", self.REMOTE]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True)
        self.poll(proc)

    def poll(self, proc):
        if proc.poll() is None:
            Clock.schedule_once(lambda dt: self.poll(proc), 0.5)
        elif proc.returncode != 0:
            logging.warning("Git: fetching failed: " +
                    proc.stdout.read() + " " + proc.stderr.read())
            self.dispatch("on_fetch_failed")
        else:
            self.get_releases()

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
        must match one of get_releases()
        If not on release commit, return None
        """
        cmd = ["describe", "--tags", "--exact-match", "--match", self.RELEASES]
        version = self._execute(cmd, ignore_errors=True)
        return version

    def get_nearest_version(self, commitish):
        cmd = ["describe", "--tags", "--abbrev=0", "--match", self.RELEASES, commitish]
        return self._execute(cmd)

    def get_releases(self):
        """Return a list of all releases, sorted by newest first"""
        cmd = ["for-each-ref", "--sort=-version:refname", "--python",
               "--format=(%(refname:strip=-1), %(creatordate:short-local))",
               "refs/tags/" + self.RELEASES]
        data = self._execute(cmd).splitlines()
        current = self.get_exact_version()
        releases = []
        for e in data:
            tag, datestring = eval(e)
            version = tag[len(self.RELEASES)-1:]
            rel = Release(name=tag, date=datestring, version=version)
            rel.current = tag == current
            releases.append(rel)
        self.releases = releases

    def get_branches(self):
        """Return a list of all branches
        This includes local branches as well as remote tracking branches
        from the remote specified in self.REMOTE. If a branch with the
        same name exists locally as well as on the remote, prefer the
        local branch.
        """
        cmd = ["for-each-ref", "--sort=-authordate", "--python",
               "--format=(%(refname:strip=-1), %(authordate:short-local), %(objectname), %(HEAD))",
               "refs/heads"]
        branches = []
        local_data = self._execute(cmd).splitlines()
        local_names = set()
        for e in local_data:
            name, timestamp, hash_, head = eval(e)
            branch = Branch(name=name, time=int(timestamp), commit=hash_, local=True)
            if head == '*':
                branch.current = True
            branches.append(branch)
            local_names.add(name)

        cmd[-2] = cmd[-2].replace(", %(HEAD)", "")
        cmd[-1] = "refs/remotes/" + self.REMOTE
        remote_data = self._execute(cmd).splitlines()
        for e in remote_data:
            name, timestamp, hash_ = eval(e)
            if name not in local_names:
                branch = Branch(name=name, time=int(timestamp), commit=hash_)
                branches.append(branch)
        return branches

    def is_dirty(self):
        """Return true if the working tree is dirty"""
        cmd = ["diff-index", "--quiet", "HEAD"]
        cmd = self._base_cmd + cmd
        proc = subprocess.run(cmd)
        return bool(proc.returncode)

    def checkout_release(self, release):
        """Change working directory to the release and execute the install script"""
        if self.is_dirty():
            App.get_running_app().notify.show(
                    "Program files changed",
                    "Revert or commit changes before updating",
                    level="warning",
                    delay=15)
            raise FileExistsError
        cmd = ["checkout", "--recurse-submodules", release]
        self._execute(cmd)

    def install(self):
        """Run the installation script"""
        if self._install_process is not None: # Install is currently running
            logging.warning("Update: Attempted to install while script is running")
            return
        # Capture both stderr and stdout in stdout
        self._install_process = subprocess.Popen(self.INSTALL_SCRIPT, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        Thread(target=self._capture_install_output).start()

    def _capture_install_output(self):
        """
        Run in a seperate thread as proc.stdout.readline() blocks until
        the next line is received.
        """
        proc = self._install_process
        self.install_output = ""
        while True:
            if self._terminate_installation:
                self._install_process.terminate()
                logging.info("Update: Installation aborted!")
                self.dispatch("on_install_finished", None)
                self._terminate_installation = False
                self._install_process = None
                break
            line = proc.stdout.readline()
            if not line:
                rc = proc.wait()
                self.dispatch("on_install_finished", rc)
                self._install_process = None
                break
            # Highlight important lines
            if line.startswith("===>"):
                line = "[b][color=ffffff]" + line + "[/color][/b]"
            self.install_output += line

    def terminate_installation(self):
        self._terminate_installation = True

    def on_install_finished(self, returncode):
        pass
    def on_fetch_failed(self):
        if self._fetch_retries > 0:
            self._fetch_retries -= 1
            self.fetch()


class Release:
    """A release that corresponds to a tag"""

    def __init__(self, *, name, date, version=None, curent=None):
        """
        name        tagname or branchname
        date        string representing the date of the release
        version     version number of the release
        current     True if this exact tag is currently checked out
        """
        self.name = name
        self.date = date
        self.version = version or name
        self.current = False

    def install(self):
        try:
            githelper.checkout_release(self.name)
        except FileExistsError:
            raise
        githelper.install()


class Branch(Release):
    """A branch that can be installed like a release"""

    def __init__(self, *, commit, local=False, **kwargs):
        """All arguments must be kwargs"""
        self.commit = commit
        self.local = local
        super().__init__(**kwargs)

    def update(self):
        pass

githelper = GitHelper()
