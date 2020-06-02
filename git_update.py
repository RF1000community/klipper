import os
import subprocess

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import StringProperty

from .elements import ErrorPopup
from . import parameters as p

class GitHelper(EventDispatcher):
    # TODO: git fetch asynchronously
    #       test install

    # If you want to receive updates from a different remote, change this value
    REMOTE = "origin"
    INSTALL_SCRIPT = os.path.join(p.klipper_dir, "scripts/install-kgui.sh")
    # Filter tags that are considered a release
    # TODO change to differentiate klipper and klipperui releases
    #      maybe prepend "kgui" or "release" instead of "v"?
    RELEASES = "v*"

    install_output = StringProperty()

    def __init__(self):
        # Use klipperui repository and no pager (-P)
        self._base_cmd = ["git", "-C", p.klipper_dir, "-P"]
        self._install_process = None

        # Dispatched whenever an installation is finished, succesfully or not
        self.register_event_type("on_install_finished")

        #fetch_cmd = self._base_cmd + ["fetch", "--recurse-submodules", self.REMOTE]
        #subprocess.Popen(fetch_cmd, stdout=subprocess.PIPE, text=True)

    def _execute(self, cmd, catch=True):
        """Execute a git command, and return its stdout
        This function blocks until git returns.
        If catch=False, propagate any Exceptions that occur
        """
        cmd = self._base_cmd + cmd
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            if not catch:
                raise
            #ErrorPopup(title="Git failed", proc.stdout + "\n" + proc.stderr).open()
            #TODO this is only testing
            print(proc.stdout, proc.stderr)
        # The output always ends with a newline, we don't want that
        return proc.stdout.rstrip("\n")

    def fetch(self):
        try:
            self._execute(["fetch", "--recurse-submodules", self.REMOTE], catch=False)
            return True
        except subprocess.CalledProcessError:
            return False

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
        current = self.get_exact_version()
        releases = []
        for e in data:
            tag, timestamp = eval(e)
            version = tag[len(self.RELEASES)-1:]
            rel = Release(name=tag, time=int(timestamp), version=version)
            rel.current = tag == current
            releases.append(rel)
        return releases

    def get_branches(self):
        """Return a list of all branches
        This includes local branches as well as remote tracking branches
        from the remote specified in self.REMOTE. If a branch with the
        same name exists locally as well as on the remote, prefer the
        local branch.
        """
        cmd = ["for-each-ref", "--sort=-authordate", "--python",
               "--format=(%(refname:strip=-1), %(authordate:unix), %(objectname), %(HEAD))",
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

        cmd[-2] = "--format=(%(refname:strip=-1), %(authordate:unix), %(objectname))"
        cmd[-1] = "refs/remotes/" + self.REMOTE
        remote_data = self._execute(cmd).splitlines()
        for e in remote_data:
            name, timestamp, hash_ = eval(e)
            if name not in local_names:
                branch = Branch(name=name, time=int(timestamp), commit=hash_)
                branches.append(branch)
        return branches

    def checkout_release(self, release):
        """Change working directory to the release and execute the install script"""
        #TODO account for uncommitted changes: check if working directory is dirty?
        cmd = ["checkout", "--recurse-submodules", "--detach", release]
        self._execute(cmd)

    def install(self):
        """Run the installation script"""
        if self._install_process is not None: # Install is currently running
            logging.warning("Updater: Attempted to install while script is running")
            return
        # Capture both stderr and stdout in stdout
        self._install_process = Popen(self.INSTALL_SCRIPT, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        Thread(target=self._capture_install_output).start()

    def _capture_install_output(self):
        """Run in a seperate thread as proc.stdout.readline() blocks until
        the next line is received."""
        proc = self._install_process
        while True:
            line = proc.stdout.readline()
            if not line:
                self.dispatch("on_install_finished", proc.returncode)
                self._install_process = None
                break
            self.install_output += line

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

    def on_install_finished(self, returncode):
        pass


class Release:
    """A release that corresponds to a tag"""

    def __init__(self, *, name, time, version=None, curent=None):
        """
        name        tagname or branchname
        time        time of creation in seconds since epoch
        version     version number of the release
        current     True if this exact tag is currently checked out
        """
        self.name = name
        self.release_date = time
        self.version = version or name
        self.current = False

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
