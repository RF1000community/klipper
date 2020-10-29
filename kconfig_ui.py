import os
from os.path import dirname

from .kconfiglib import (Kconfig,
    Symbol, MENU, COMMENT,
    BOOL, TRISTATE, STRING, INT, HEX, UNKNOWN,
    expr_value,
    TRI_TO_STR,
    Choice, MenuNode, AND, OR,
    expr_str, split_expr,
    standard_sc_expr_str, TYPE_TO_STR,
    standard_kconfig, standard_config_filename)
from kivy.clock import Clock
from kivy.properties import NumericProperty, BooleanProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label

from .elements import Divider
from . import parameters as p


class FlashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        os.environ['srctree'] = p.klipper_dir
        self.kconf = Kconfig(os.path.join(p.klipper_dir, "src/Kconfig"))

        Clock.schedule_once(self.draw_nodes, 0)

    def draw_nodes(self, dt=None):

        self.ids.box.clear_widgets()
        self.ids.box.add_widget(Divider(pos_hint = {'center_x':0.5}))
        self.ids.box.add_widget(CI_Text(None, text = "Configure Firmware to flash to your Printer Mainboard. This usually needs to be done once when installing the Klipper Firmware"))

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
                nod = CI_Text(node)
            elif node.item is COMMENT:
                nod = CI_Text(node)
            elif node.item.orig_type in (STRING, INT, HEX):
                nod = CI_Value(node)

            # Choice Element
            elif isinstance(node.item, Symbol) and node.item.choice and node.item.visibility == 2:
                selected = node.item == node.item.choice.selection
                nod = CI_Radio(node, selected = selected)
                divider = False

            #Pinned to single value
            elif len(node.item.assignable) <= 1:
                # Choice Title
                if isinstance(node.item, Choice): 
                    nod = CI_Text(node)
                else:
                    nod = CI_Value(node, locked = True)
            elif node.item.type == BOOL:
                nod = CI_Tristate(node, state = 0, states = 2)
            elif node.item.assignable == (1, 2):
                nod = CI_Tristate(node, state = 0, states = 3)
            else:
                nod = CI_Tristate(node, state = 0, states = 3)
    
            if divider: self.ids.box.add_widget(Divider(pos_hint = {'center_x': 0.5}))
            nod.text = text
            self.ids.box.add_widget(nod)
        self.ids.box.add_widget(Divider(pos_hint = {'center_x': 0.5}))         

class CI_Tristate(Label):
    state = NumericProperty(0)
    def __init__(self, node, state, states=2, **kwargs):
        super().__init__(**kwargs)
        self.states = states
        self.node = node
    def on_release(self):
        self.state = (self.state + 1) % self.states #cycle through states

class CI_Radio(Label):
    selected = BooleanProperty(False)
    def __init__(self, node, **kwargs):
        super().__init__(**kwargs)
        self.node = node

class CI_Value(Label):
    locked = BooleanProperty(False)
    value = StringProperty()
    def __init__(self, node, **kwargs):
        super().__init__(**kwargs)
        self.node = node

class CI_Text(Label):
    value = StringProperty()
    def __init__(self, node, **kwargs):
        super().__init__(**kwargs)
        self.node = node
