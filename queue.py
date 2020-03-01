# coding: utf-8
from functools import partial
from subprocess import Popen, PIPE, STDOUT
import logging
import os, time

from kivy.app import App
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.logger import Logger
from kivy.properties import ListProperty, ObjectProperty, NumericProperty, DictProperty, StringProperty, BooleanProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.screenmanager import Screen

from elements import *
import parameters as p


class FC(RecycleView):
    path = StringProperty()
    def __init__(self, **kwargs):
        super(FC, self).__init__(**kwargs)
        self.app = App.get_running_app()
        self.load_queue(in_background=False)
        self.app.bind(queued_files=self.load_queue)
        self.app.bind(print_state=self.load_queue)

    def load_queue(self, instance=None, queue=None, in_background=True):
        queue = [{'name': basename(qd),
                  'details': (self.app.print_state.capitalize() if i==0 else "{}.".format(i)),
                  'path': qd} for i,qd in enumerate(self.app.queued_files)]
        self.data = queue 
        self.refresh_from_data()
        if not in_background and 'fc_box' in self.ids:
            self.ids.fc_box.selected_nodes = []
            self.scroll_y = 1

    def send_queue(self, queue):
        """
        Send the updated queue back to the virtual sdcard
        Will fail in testing
        """
        sdcard = self.app.sdcard
        sdcard.clear_queue() # Clears everything except for the first entry
        self.app.queued_files = queue
        for path in self.queued_files[1:]:
            sdcard.add_printjob(path)

    def move_up(self):
        """Move the selected file up one step in the queue"""
        i = self.ids.fc_box.selected_nodes[0]
        queue = self.app.queued_files
        if len(queue) > i:
            to_move = queue.pop(i)
            queue.insert(i - 1, to_move)
            self.ids.fc_box.selected_nodes = [i - 1]
            self.send_queue(queue)

    def move_down(self):
        """Move the selected file down one step in the queue"""
        i = self.ids.fc_box.selected_nodes[0]
        queue = self.app.queued_files
        if len(queue) > i:
            to_move = queue.pop(i)
            queue.insert(i + 1, to_move)
            self.ids.fc_box.selected_nodes = [i + 1]
            self.send_queue(queue)

    def remove(self):
        """Remove the selcted file from the queue"""
        i = self.ids.fc_box.selected_nodes[0]
        queue = self.app.queued_files
        if i == 0:
            StopPopup().open()
        elif len(queue) > i:
            to_remove = queue.pop(i)
            self.ids.fc_box.selected_nodes = []
            self.send_queue(queue)

class FCBox(LayoutSelectionBehavior, RecycleBoxLayout):
    # Adds selection behaviour to the view
    pass

class FCItem(RecycleDataViewBehavior, Label):
    name = StringProperty()
    path = StringProperty()
    details = StringProperty()
    index = None
    selected = BooleanProperty(False)
    pressed = BooleanProperty(False)

    def refresh_view_attrs(self, rv, index, data):
        # Catch and handle the view changes
        self.index = index
        return super(FCItem, self).refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        # Add selection on touch down
        if super(FCItem, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            self.pressed = True
            self.parent.select_with_touch(self.index, touch)
            return True

    def on_touch_up(self, touch):
        was_pressed = self.pressed
        self.pressed = False
        if super(FCItem, self).on_touch_up(touch):
            return True
        if self.collide_point(*touch.pos) and was_pressed:
            return True
        return False

    def apply_selection(self, rv, index, is_selected):
        # Respond to the selection of items in the view
        self.selected = is_selected