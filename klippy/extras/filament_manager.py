from xml.etree import cElementTree #just ElementTree for py3
from os import walk
from os.path import expanduser
import os
import logging
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
            self.extrude_speed = self.filament_manager_config.get_float('extrude_speed', 5)
            self.max_path_len = self.filament_manager_config.getfloat('max_path_length')
            self.min_path_len = self.filament_manager_config.getfloat('min_path_length')
            self.printer.register_event_handler("klippy:connect", self.handle_connect)

        self.materials_path = expanduser('~/materials')
        
        self.materials = []
        self.loaded_materials = []
        self.my_materials = []
        self.tmc_to_guid = {} # Type -> Manufacturer -> Color
        self.guid_to_path = {}

        self.parse_xml()

    def handle_connect(self):
        #get Extruders from Printer
        self.extruders = []
        for i in range(0,10):
		    ext = self.printer.lookup_object('extruder{}'.format('' if i==0 else i), None)
		    if ext: self.extruders.append(ext)

    def parse_xml(self):
        t = TicToc()
        t.tic()
        self.guid_to_path = {}
        self.tmc_to_guid = {}
        root, dirs, files = next(walk(self.materials_path))
        for f in files:
            f_path = os.path.join(self.materials_path, f)
            # iterparse implementaion is actually slower, so parse whole file in C
            try:
                f_root = cElementTree.parse(os.path.join(self.materials_path, f)).getroot()
            except: 
                print("fail {}".format(f))
                continue
            f_metadata = f_root.find('{http://www.ultimaker.com/material}metadata')
            f_name = f_metadata.find('{http://www.ultimaker.com/material}name')

            f_type = f_name.find('{http://www.ultimaker.com/material}material').text
            f_brand = f_name.find('{http://www.ultimaker.com/material}brand').text
            f_guid = f_metadata.find('{http://www.ultimaker.com/material}GUID').text
            f_color = f_metadata.find('{http://www.ultimaker.com/material}color_code').text

            # generate Data 
            self.guid_to_path[f_guid] = f_path

            if self.tmc_to_guid.get(f_type):
                if self.tmc_to_guid[f_type].get(f_brand):
                    self.tmc_to_guid[f_type][f_brand][f_color] = f_guid #type dict and brand dict already there, add color entry
                else: self.tmc_to_guid[f_type][f_brand] = {f_color: f_guid} #type dict already there, add dict for this brand with color entry
            else: self.tmc_to_guid[f_type] = {f_brand: {f_color: f_guid}} #add dict for this type ..
        t.toc()
        logging.info("time to parse: {}".format(t.elapsed))

    def get_text(self, path, tags):
        try:
            current_tag = cElementTree.parse(path).getroot()
        except: 
            logging.info("Failed to parse {}".format(path))
            return ""
        for tag in tags:
            current_tag = current_tag.find('{http://www.ultimaker.com/material}'+tag)
        return current_tag.text

    def get_status(self):
        pass

    def load(self, tool_id):
        pass
        
    def unload(self, tool_id):
        pass
        
    def stop(self, tool_id):
        pass
        
def load_config(config):
    return FilamentManager(config)

if __name__ == '__main__':
    load_config(None)