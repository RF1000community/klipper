#!/usr/bin/env python3
"""
Usage:

./test.py PATH

Where PATH is the location of a gcode or ufp file to read.
"""

import sys
import os

path = os.path.dirname(os.path.realpath(__file__))
sys.path.remove(path)
sys.path.append(os.path.dirname(path))
from gcode_metadata import load_config

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("A path to parse must be provided")
    path = sys.argv[1]
    mm = load_config(None)
    md = mm.get_metadata(path)
    general_interface = [
        "get_gcode_stream",
        "get_file_size",
        "get_slicer",
        "get_filetype",
        "get_extruder_count",
        "get_print_dimensions",
        "get_time",
        "get_flavor",
        "get_thumbnail_path",
        ]
    extruder_interface = [
        "get_filament",
        "get_material_guid",
        "get_material_type",
        "get_material_brand",
        "get_material_color",
        "get_density",
        "get_diameter",
        ]
    max_len = max([len(e) for e in general_interface + extruder_interface])
    for fname in general_interface:
        print(fname[4:] + ":" + " " * (max_len - len(fname) + 1)
              + str(getattr(md, fname)()))
    for i in range(md.get_extruder_count()):
        print(f"\nExtruder {i}:")
        for fname in extruder_interface:
            print(fname[4:] + ":" + " " * (max_len - len(fname) + 1)
                  + str(getattr(md, fname)()))
