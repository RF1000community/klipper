# Filament manager compatible with Cura material files, tracking loaded
# material and their use
#
# Copyright (C) 2020  Konstantin Vogel <konstantin.vogel@gmx.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import os
import json
import logging

from xml.etree import cElementTree #just ElementTree for py3
from os.path import expanduser, join

from pytictoc import TicToc


class FilamentManager:
    def __init__(self, config):
        if config:
            self.filament_manager_config = config
            self.printer = self.filament_manager_config.get_printer()
            self.reactor = self.printer.get_reactor()
            self.grab_time = self.filament_manager_config.getfloat('grab_time', 4)
            self.grab_speed = self.filament_manager_config.getfloat('grab_speed', 5)
            self.load_speed = self.filament_manager_config.getfloat('load_speed', 60)
            self.extrude_speed = self.filament_manager_config.getfloat('extrude_speed', 5)
            self.max_path_len = self.filament_manager_config.getfloat('max_path_length')
            self.min_path_len = self.filament_manager_config.getfloat('min_path_length')
            self.printer.register_event_handler("klippy:connect", self.handle_connect)

        # xml files for each material
        self.material_dir = expanduser('~/materials')
        self.tmc_to_guid = {} # Type -> Manufacturer -> Color
        self.guid_to_path = {}
        self.read_material_library_xml() 

        # json list of loaded and unloaded material
        self.loaded_material_path = join(self.material_dir, "loaded_material.json")
        # loaded and unloaded: [(guid, amount in kg), ...]
        self.loaded_materials = []
        self.unloaded_materials = []
        self.read_loaded_material_json() 

    def handle_connect(self):
        self.heater_manager = self.printer.lookup_object('heater', None)
        self.toolhead = self.printer.lookup_object('toolhead')
        self.extruders = {}
        for i in range(10):
            extruder_id = 'extruder{}'.format('' if i==0 else i)
            self.extruders[extruder_id] = self.printer.lookup_object(extruder_id, None)

    ######## manage cura-material xml files
    def read_material_library_xml(self):
        t = TicToc()
        t.tic()
        self.guid_to_path = {}
        self.tmc_to_guid = {}
        if os.path.exists(self.material_dir):
            files = os.listdir(self.material_dir)
            for f in files:
                if not f.endswith(".xml.fdm_material"):
                    continue
                f_path = os.path.join(self.material_dir, f)
                self.read_single_file(f_path)
        t.toc()
        logging.info("time to parse: {}".format(t.elapsed))

    def read_single_file(self, f_path):
        try:
            f_root = cElementTree.parse(f_path).getroot()
        except: 
            logging.info("failed to parse xml-material-file {}".format(f_path))
            return
        ns = {'m': 'http://www.ultimaker.com/material'}
        f_metadata = f_root.find('m:metadata', ns)
        f_name = f_metadata.find('m:name', ns)

        f_type = f_name.find('m:material', ns).text
        f_brand = f_name.find('m:brand', ns).text
        f_guid = f_metadata.find('m:GUID', ns).text
        f_color = f_metadata.find('m:color_code', ns).text

        # generate Data 
        self.guid_to_path[f_guid] = f_path

        if self.tmc_to_guid.get(f_type):
            if self.tmc_to_guid[f_type].get(f_brand):#type dict and brand dict already there, add color entry
                self.tmc_to_guid[f_type][f_brand][f_color] = f_guid
            else: #type dict already there, add dict for this brand with color entry
                self.tmc_to_guid[f_type][f_brand] = {f_color: f_guid}
        else: #add dict for this type ..
            self.tmc_to_guid[f_type] = {f_brand: {f_color: f_guid}}

    def get_material_info(self, material, xpath):
        """material can be either GUID or filepath"""
        fpath = self.guid_to_path.get(material) or material
        try:
            root = cElementTree.parse(fpath).getroot()
        except: 
            logging.info("Failed to parse {}".format(fpath))
        else:
            ns = {'m': 'http://www.ultimaker.com/material'}
            node = root.find(xpath, ns)
            if node is not None:
                return node.text


    ######## loading and unloading api ONLY EXECUTE IN KLIPPER THREAD
    def get_status(self):
        return self.loaded_materials

    def load(self, extruder_id, temp=None, amount=1, unloaded_idx=None, guid=None):
        if unloaded_idx is not None:
            material = self.unloaded_materials[unloaded_idx]
            self.unloaded_materials.remove(material)
            guid, amount = material
        # make sure list is long enough
        to_short_by = max(self.idx(extruder_id) + 1 - len(self.loaded_materials), 0)
        self.loaded_materials.extend([None]*to_short_by)
        self.loaded_materials[self.idx(extruder_id)] = (guid, amount)
        self.write_loaded_material_json()
        if not temp:
            temp = self.get_material_info(guid,
                    "./m:settings/m:setting[@key='print temperature']")

        self.heater_manager.heaters[extruder_id].set_temp(float(temp))
        self.wait_for_temperature(self.heater_manager.heaters[extruder_id])

        # move slowly to grab the material for grab_time in seconds
        grab_length = self.grab_speed * self.grab_time
        self.send_extrude(grab_length, self.grab_speed, extruder_id)
        # move fast for as long as the hotend isn't reached for sure
        load_length = self.min_path_len - grab_length
        self.send_extrude(load_length, self.load_speed, extruder_id)
        # move at max extrusion speed so that the maximum path length is covered even without grab_lenght
        self.wait_for_temperature(self.heater_manager.heaters[extruder_id])
        extrude_length = self.max_path_len - load_length
        self.send_extrude(extrude_length, self.extrude_speed, extruder_id)

    def unload(self, extruder_id):
        temp = 200

        if len(self.loaded_materials) > self.idx(extruder_id)\
        and self.loaded_materials[self.idx(extruder_id)]:
            unloaded = self.loaded_materials[self.idx(extruder_id)]
            self.unloaded_materials = [unloaded] + self.unloaded_materials[:9]
            self.loaded_materials[self.idx(extruder_id)] = None
            temp = self.get_material_info(unloaded[0],
                   "./m:settings/m:setting[@key='print temperature']") or temp
            self.write_loaded_material_json()

        self.heater_manager.heaters[extruder_id].set_temp(float(temp))
        self.wait_for_temperature(self.heater_manager.heaters[extruder_id])

        self.send_extrude(self.max_path_len - self.min_path_len, self.extrude_speed, extruder_id)
        self.heater_manager.heaters[extruder_id].set_temp(0)
        self.send_extrude(self.min_path_len, self.load_speed, extruder_id)

    def idx(self, extruder_id):
        return 0 if extruder_id == 'extruder' else int(extruder_id[-1])

    def send_extrude(self, e, speed, extruder_id):
        # select current extruder if necessary
        current_extruder = self.toolhead.get_extruder()
        if current_extruder != self.extruders[extruder_id]:
            self.toolhead.set_extruder(self.extruders[extruder_id], current_extruder.stepper.get_commanded_position())
        cur_pos = self.toolhead.get_position()
        cur_pos[3] += e
        self.toolhead.move(cur_pos, speed, force=True)

    def wait_for_temperature(self, heater):
        eventtime = self.reactor.monotonic()
        while heater.check_busy(eventtime):
            eventtime = self.reactor.pause(eventtime + 1.)

    ######## store json for loaded and recently unloaded material and their amount
    def read_loaded_material_json(self):
        """Read the material file and return it as a list object"""
        try:
            with open(self.loaded_material_path, "r") as f:
                materials = json.load(f)
                self.loaded_materials = materials["loaded"]
                self.unloaded_materials = materials["unloaded"]
        except (IOError, ValueError): # No file or incorrect JSON
            logging.info("Filament-Manager: Couldn't read loaded-material-file at " + self.loaded_material_path)

    def verify_loaded_material_json(self, material):
        """Only return True when the entire file has a correct structure"""
        pass

    def write_loaded_material_json(self):
        """Write the object to the material file"""
        materials = {"loaded": self.loaded_materials, "unloaded": self.unloaded_materials}
        try:
            with open(self.loaded_material_path, "w") as f:
                json.dump(materials, f, indent=True)
        except IOError:
            logging.warning("Filament-Manager: Couldn't write loaded-material-file at "
                    + self.loaded_material_path)
        self.printer.send_event("filament_manager:material_changed")

def load_config(config):
    return FilamentManager(config)

if __name__ == '__main__':
    load_config(None)
