import json
import urllib2 # is called urllib.request for py3
import threading
import logging

from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.properties import NumericProperty

import parameters as p
from settings import SetItem
from elements import *


class UpdateScreen(Screen):
    def __init__(self, **kwargs):
        super(UpdateScreen, self).__init__(**kwargs)
        Clock.schedule_once(self.draw_releases, 0)

    def draw_releases(self, dt):
        Download("https://api.github.com/repos/D4SK/klipperui/releases", [None,None,False], self.finish_drawing_releases).start()

    def finish_drawing_releases(self, releases):
        releases = json.JSONDecoder().decode(releases)
        self.ids.box.clear_widgets()
     
        for release in releases:
            entry = SI_Release(release['zipball_url'], left_title = release['tag_name'], right_title = release['published_at'].split("T")[0])
            self.ids.box.add_widget(entry)

class Download(threading.Thread):
    def __init__(self, url, comm_list, result_handler):
        super(Download, self).__init__()
        self.url = url
        self.comm_list = comm_list # [bytes, totalbytes, cancel_signal]
        self.result_handler = result_handler

    def run(self):
        super(Download, self).run()
        CHUNK_SIZE=32768
        for i in range(20): # TODO make cleaner
            response = urllib2.urlopen(self.url)
            total_size = response.info().getheader('Content-Length')
            if total_size:
                break
        else:
            logging.info("Download Failed")
        total_size.strip()
        total_size = int(total_size)
        self.comm_list[1] = total_size
        bytes_so_far = 0
        data = []

        # download chunks
        while not self.comm_list[2]:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            bytes_so_far += len(chunk)
            data += chunk
            self.comm_list[0] = bytes_so_far

        result = "".join(data)
        Clock.schedule_once(lambda dt: self.result_handler(result))

class UpdatePopup(BasePopup):
    comm_list = ListProperty([0, 1, False]) # Lists allow passing a reference, whereas ints are copied
    def __init__(self, version_tag, url, **kwargs):
        self.version = version_tag
        super(UpdatePopup, self).__init__(**kwargs)
        Download(url, self.comm_list, self.download_finished).start()

    def download_finished(self, data):
        self.data = file
        #self.ids.progress_bar.value = 1
        self.ids.confirm.enabled = True
    
    def install(self):
        pass

    def dismiss(self, **kwargs):
        super(UpdatePopup, self).dismiss(**kwargs)
        self.comm_list[2] = True #stop signal for download thread (doesnt get garbage collected, downloader has reference)



class SI_Release(SetItem):
    def __init__(self, url, **kwargs):
        super(SI_Release, self).__init__(**kwargs)
        self.url = url
