# Filament manager compatible with Cura material files, tracking loaded
# material and the amount left
#
# Copyright (C) 2020  Konstantin Vogel <konstantin.vogel@gmx.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import os
import json
import logging

from xml.etree import ElementTree
from os.path import expanduser, join
from math import pi


class FilamentManager:
    def __init__(self, config):
        extruder_count = 1
        if config:
            self.filament_manager_config = config
            self.printer = self.filament_manager_config.get_printer()
            self.reactor = self.printer.get_reactor()
            klipper_config_manager = self.printer.objects['configfile']
            klipper_config = klipper_config_manager.read_main_config()
            filament_diameter = klipper_config.getsection("extruder").getfloat("filament_diameter", 1.75)
            for i in range(1, 10):
                try: klipper_config.getsection(f"extruder{i}")
                except: extruder_count = i; break
            self.filament_area = pi * (filament_diameter/2.)**2
            self.extruders = {}
            self.printer.register_event_handler("klippy:ready", self.handle_ready)
            self.printer.register_event_handler("klippy:shutdown", self.handle_shutdown)
        # xml files for each material
        self.material_dir = expanduser('~/materials')
        if not os.path.exists(self.material_dir):
            os.mkdir(self.material_dir)
        self.tmc_to_guid = {} # [Type][Manufacturer][Color] = guid, a dict tree for choosing filaments
        self.guid_to_path = {}
        self.read_material_library_xml()
        # json list of loaded and unloaded material
        self.loaded_material_path = join(self.material_dir, "loaded_material.json")
        # {'loaded': [{'guid': None if nothing is loaded,
        #           'amount': amount in kg,
        #           'state': loading | loaded | unloading | no material,
        #           'all_time_extruded_length': mm}, ...],
        # 'unloaded': [{'guid': None if nothing is loaded,
        #           'amount': amount in kg}, ...]}
        self.material = {
            'loaded':[{'guid':None,
                    'state':"no material",
                    'amount':0,
                    'all_time_extruded_length':0}] * extruder_count,
            'unloaded':[]}
        self.read_loaded_material_json()
        # set state for all materials to loaded in case power was lost during loading or unloading
        for material in self.material['loaded']:
            if material['guid']: material['state'] = 'loaded'

    def handle_ready(self):
        self.heater_manager = self.printer.lookup_object('heaters')
        self.toolhead = self.printer.lookup_object('toolhead')
        self.gcode = self.printer.lookup_object('gcode')
        for i in range(10):
            extruder_id = f"extruder{'' if i==0 else i}"
            extruder = self.printer.lookup_object(extruder_id, None)
            if extruder: self.extruders[extruder_id] = extruder

    def handle_shutdown(self):
        self.update_loaded_material_amount()
        self.write_loaded_material_json()

######################################################################
# manage cura-material xml files
######################################################################

    def read_material_library_xml(self):
        self.guid_to_path = {}
        self.tmc_to_guid = {}
        files = os.listdir(self.material_dir)
        for f in files:
            if f.endswith(".xml.fdm_material"):
                self.read_single_file(os.path.join(self.material_dir, f))            

    def read_single_file(self, f_path):
        try:
            f_root = ElementTree.parse(f_path).getroot()
        except: 
            logging.info(f"failed to parse xml-material-file {f_path}")
            return
        ns = {'m': 'http://www.ultimaker.com/material'}
        f_type  = f_root.find('./m:metadata/m:name/m:material', ns).text
        f_brand = f_root.find('./m:metadata/m:name/m:brand', ns).text
        f_guid  = f_root.find('./m:metadata/m:GUID', ns).text
        f_color = f_root.find('./m:metadata/m:color_code', ns).text

        # generate path lookup 
        self.guid_to_path[f_guid] = f_path
        # generate tmc dict
        if self.tmc_to_guid.get(f_type):
            if self.tmc_to_guid[f_type].get(f_brand):#type and brand already there, add color entry
                self.tmc_to_guid[f_type][f_brand][f_color] = f_guid
            else: #type already there, add dict for this brand with color entry
                self.tmc_to_guid[f_type][f_brand] = {f_color: f_guid}
        else: #add dict for this type ..
            self.tmc_to_guid[f_type] = {f_brand: {f_color: f_guid}}

    def get_info(self, material, xpath, default=None):
        """material can be either GUID or filepath"""
        fpath = self.guid_to_path.get(material) or material
        try:
            root = ElementTree.parse(fpath).getroot()
        except: 
            logging.warning(f"Failed to parse {fpath}")
        else:
            ns = {'m': 'http://www.ultimaker.com/material'}
            node = root.find(xpath, ns)
            if node is not None:
                return node.text
        logging.warning(f"Filament Manager returned default value for material {material}, xpath {xpath}")
        return default

######################################################################
# loading and unloading api (only execute in klippy thread)
######################################################################

    def get_status(self):
        self.update_loaded_material_amount()
        return self.material

    def load(self, extruder_id, temp=None, amount=None, unloaded_idx=None, guid=None):
        """
        physically load a material, either from unloaded material list or a new one from a guid
        """
        self.extruders[extruder_id].untracked_extruded_length = 0
        idx = self.idx(extruder_id)
        if unloaded_idx is not None:
            unloaded = self.material['unloaded'].pop(unloaded_idx)
            guid = guid or unloaded['guid']
            amount = amount or unloaded['amount']
        amount = amount or 1
        temp = temp or self.get_info(guid, "./m:settings/m:setting[@key='print temperature']", 200)
        self.material['loaded'][idx].update(
            {'guid': guid,
            'amount': amount,
            'state': 'loading'})
        self.write_loaded_material_json()

        self.gcode.run_script_from_command(f"LOAD_FILAMENT TEMPERATURE={temp}")

        self.material['loaded'][idx]['state'] = 'loaded'
        self.write_loaded_material_json()

    def unload(self, extruder_id):
        self.update_loaded_material_amount()
        temp = 200 # Default value
        idx = self.idx(extruder_id)
        if self.material['loaded'][idx]['guid']:
            self.material['loaded'][idx]['state'] = 'unloading'
            self.write_loaded_material_json()
            temp = self.get_info(self.material['loaded'][idx]['guid'],
                   "./m:settings/m:setting[@key='print temperature']", temp)

        self.gcode.run_script_from_command(f"UNLOAD_FILAMENT TEMPERATURE={temp}")

        self.material['unloaded'].insert(0, 
            {'guid':self.material['loaded'][idx]['guid'],
            'amount':self.material['loaded'][idx]['amount']})
        self.material['loaded'][idx].update(
            {'guid': None,
            'amount': 0,
            'state': 'no material'})
        self.material['unloaded'] = self.material['unloaded'][:15] # only store recent materials
        self.write_loaded_material_json()

    def idx(self, extruder_id):
        return 0 if extruder_id == 'extruder' else int(extruder_id[-1])

######################################################################
# store json with loaded and recently unloaded materials and their amount
######################################################################

    def read_loaded_material_json(self):
        """Read the material file and return it as a list object"""
        try:
            with open(self.loaded_material_path, "r") as f:
                material = json.load(f)
                if not self.verify_loaded_material_json(material):
                    logging.info("Filament-Manager: Malformed material file at " + self.loaded_material_path)
                else:
                    self.material['unloaded'] = material['unloaded']
                    for i, new in enumerate(material['loaded']): self.material['loaded'][i] = new
        except (IOError, ValueError): # No file or incorrect JSON
            logging.info("Filament-Manager: Couldn't read loaded-material-file at " + self.loaded_material_path)

    def verify_loaded_material_json(self, material):
        """Only return True when the entire file has a correct structure"""
        try:
            for mat in material['loaded']:
                if not (
                    isinstance(mat['state'], str) and
                    isinstance(mat['guid'], (str, type(None))) and
                    isinstance(mat['amount'], (float, int)) and
                    isinstance(mat['all_time_extruded_length'], (float, int))):
                    return False
            for mat in material['unloaded']:
                if not (
                    isinstance(mat['guid'], str) and
                    isinstance(mat['amount'], (float, int))):
                    return False
            return True
        except:
            return False

    def write_loaded_material_json(self):
        """Write the object to the material file"""
        try:
            with open(self.loaded_material_path, "w") as f:
                json.dump(self.material, f, indent=True)
        except IOError:
            logging.warning("Filament-Manager: Couldn't write loaded-material-file at "
                    + self.loaded_material_path)
        self.printer.send_event("filament_manager:material_changed")

    # only call in klipper thread else extruded_length += x can cause additional extruded_length
    def update_loaded_material_amount(self):
        for extruder_id in self.extruders:
            idx = self.idx(extruder_id)
            extruded_length = self.extruders[extruder_id].untracked_extruded_length
            self.extruders[extruder_id].untracked_extruded_length = 0
            density = 1.24 # TODO use density from xml
            extruded_weight = extruded_length*self.filament_area*density/1000000. # convert from mm^2 to m^2
            self.material['loaded'][idx]['amount'] -= extruded_weight
            self.material['loaded'][idx]['all_time_extruded_length'] += extruded_length


def load_config(config):
    return FilamentManager(config)
