import os
import json
import urllib
import io
import threading
import logging
import tarfile
import subprocess
import traceback

from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.properties import NumericProperty

from . import parameters as p
from .settings import SetItem
from .elements import *


class UpdateScreen(Screen):
    def __init__(self, **kwargs):
        super(UpdateScreen, self).__init__(**kwargs)
        self.klipper_dir = os.path.dirname(os.path.dirname(os.path.dirname(p.kgui_dir)))

        Clock.schedule_once(self.draw_releases, 0)

    def draw_releases(self, dt):
        self.ids.message = "Installed Version: " + self.get_git_version()
        FileDownload("https://api.github.com/repos/D4SK/klipperui/releases", [None,None,False], self.finish_drawing_releases).start()

    def finish_drawing_releases(self, releases):
        releases = json.load(releases)
        self.ids.box.clear_widgets()

        for release in releases:
            entry = SI_Release(release['tarball_url'], left_title = release['tag_name'], right_title = release['published_at'].split("T")[0])
            self.ids.box.add_widget(entry)

    def get_git_version(self):
        klippy_dir = os.path.dirname(os.path.dirname(p.kgui_dir))


        # Obtain version info from "git" program
        prog = ('git', '-C', self.klipper_dir, 'describe', '--always', '--tags', '--long', '--dirty')
        try:
            process = subprocess.Popen(prog, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            ver, err = process.communicate()
            retcode = process.wait()
            if retcode == 0:
                return ver.strip().decode()
            else:
                logging.debug("Error getting git version: %s", err)
        except OSError:
            logging.debug("Exception on run: %s", traceback.format_exc())

        with open(os.path.join(klippy_dir, '.version')) as h:
            return h.read().rstrip().decode()
        return ""

class FileDownload(threading.Thread):
    def __init__(self, url, comm_list, result_handler):
        super(FileDownload, self).__init__()
        self.url = url
        self.comm_list = comm_list # [bytes, totalbytes, cancel_signal]
        self.result_handler = result_handler

    def run(self):
        super(FileDownload, self).run()
        CHUNK_SIZE=32768
        for i in range(20):
            try:
                response = urllib.urlopen(self.url)
                total_size = response.info().getheader('Content-Length')
                total_size.strip()
                break

            except Exception:
                pass
            logging.warning("Downlaod Retry")
        else:
            logging.warning("Download Failure: with url: {}".format(self.url))
            return
        total_size = int(total_size)
        self.comm_list[1] = total_size
        bytes_so_far = 0
        data = io.StringIO()

        # download chunks
        while not self.comm_list[2]:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            bytes_so_far += len(chunk)
            data.write(chunk)
            self.comm_list[0] = bytes_so_far
        data.seek(0)
        Clock.schedule_once(lambda dt: self.result_handler(data))

class UpdatePopup(BasePopup):
    comm_list = ListProperty([0, 1, False]) # Lists allow passing a reference, whereas ints are copied
    def __init__(self, version_tag, url, **kwargs):
        self.version = version_tag
        super(UpdatePopup, self).__init__(**kwargs)
        FileDownload(url, self.comm_list, self.download_finished).start()

    def download_finished(self, data):
        self.data = data
        self.ids.confirm.enabled = True

    def install(self):
        # as a convention klipper is always installed in HOME directory
        install_dir = os.path.expanduser('~')
        tar = tarfile.open(fileobj = self.data, mode = 'r|gz')
        logging.info("extraxting {}".format(tar))
        tar.extractall(install_dir)
        tar.close()

    def dismiss(self, **kwargs):
        super(UpdatePopup, self).dismiss(**kwargs)
        self.comm_list[2] = True #stop signal for download thread (doesnt get garbage collected, downloader has reference)



class SI_Release(SetItem):
    def __init__(self, url, **kwargs):
        super(SI_Release, self).__init__(**kwargs)
        self.url = url
