#!/usr/bin/env python3
from __future__ import print_function
import sys
import os

from kconfiglib import Kconfig, \
                       Symbol, MENU, COMMENT, \
                       BOOL, TRISTATE, STRING, INT, HEX, UNKNOWN, \
                       expr_value, \
                       TRI_TO_STR, \
                       Choice, MenuNode, AND, OR, \
                       expr_str, split_expr, \
                       standard_sc_expr_str, TYPE_TO_STR, \
                       standard_kconfig, standard_config_filename
import logging
from os.path import dirname
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.properties import NumericProperty, BooleanProperty, StringProperty

import parameters as p
from settings import SetItem
from elements import *


class FlashScreen(Screen):
    def __init__(self, **kwargs):
        super(FlashScreen, self).__init__(**kwargs)
        klipper_dir = dirname(dirname(dirname(p.kgui_dir)))
        os.environ['srctree'] = klipper_dir
        self.kconf = Kconfig(os.path.join(klipper_dir, "src/Kconfig"))

        Clock.schedule_once(self.draw_nodes, 0)

    def draw_nodes(self, dt=None):
        self.ids.box.clear_widgets()

        for node in self.kconf.node_iter():
            divider = True
            if node.prompt:
                text = node.orig_prompt[0]
            else:
                text = ""

            # Determine wether to show node
            if not (node.prompt and expr_value(node.prompt[1]) and not (node.item == MENU and not expr_value(node.visibility))):
                continue

            if node.item is MENU:
                nod = CI_Text()
            elif node.item is COMMENT:
                nod = CI_Text()
            elif node.item.orig_type in (STRING, INT, HEX):
                nod = CI_Value()

            elif isinstance(node.item, Symbol) and node.item.choice and node.item.visibility == 2: #choice Element
                selected = node.item == node.item.choice.selection
                nod = CI_Radio(selected = selected)
                divider = False

            elif len(node.item.assignable) <= 1:
                #Pinned to single value
                if isinstance(node.item, Choice): #choice Title
                    nod = CI_Text()
                else:
                    nod = CI_Value(locked = True)
            elif node.item.type == BOOL:
                nod = CI_Tristate(state = False, states = 2)
            elif node.item.assignable == (1, 2):
                nod = CI_Tristate(False, states = 3)
            else:
                nod = CI_Tristate(False, states = 3)
    
            if divider: self.ids.box.add_widget(Divider())
            nod.text = text
            self.ids.box.add_widget(nod)



class CI_Tristate(Label):
    state = NumericProperty(0)
    def __init__(self, state, states=2, **kwargs):
        super(CI_Tristate, self).__init__(**kwargs)
        self.states = states
class CI_Radio(Label):
    selected = BooleanProperty(False)

class CI_Value(Label):
    locked = BooleanProperty(False)

class CI_Text(Label):
    value = StringProperty()