import itertools
from math import pi
import os
import re

class BaseParser:
    """Base class for all parsers

    A parser for a specific slicer should inherit this class.
    For adding metadata the appropriate methods should be overridden,
    however all methods are optional to implement. If unchanged,
    a default value will be set, usually None.

    Some values are specific to one extruder. The extruder is specified as an
    integer index, starting at zero.

    This class is used as fallback if no other matching parser was found.
    """

    """Used by detect() on all lines to figure out if this is the right parser"""
    PATTERN_DETECT = re.compile("(?!)")  # Matches nothing

    """Character that seperates keys from values"""
    DELIMITER = "="

    """Name of the slicer used to generate the G-Code file"""
    SLICER = "Unknown"

    """If part of the metadata is stored at the end of the file.
    Only used when parsing UFP files because reading the tail requires
    decompressing the entire file."""
    _needs_tail = False

    def __init__(self, head, tail, path, module):
        self._module = module
        self.path = path
        self.options, self.non_option_lines = self._parse_options(head, tail)

    @classmethod
    def _detect(cls, lines):
        """
        return True if this is the right parser for this file.
        This is implemented as a class method so the class doesn't have
        to be instantiated to detect if it's the right parser.
        """
        for l in lines:
            if re.search(cls.PATTERN_DETECT, l):
                return True
        return False

    def _parse_options(self, head=[], tail=[]):
        options = {}
        non_option_lines = []
        for l in itertools.chain(head, tail):
            if self.DELIMITER in l:
                key, value = l.split(self.DELIMITER, maxsplit=1)
                value = value.strip()
                try:
                    value = eval(value, {}, {})
                except (NameError, SyntaxError):
                    pass
                options[key.strip()] = value
            else:
                non_option_lines.append(l)
        return options, non_option_lines

    def get_gcode_stream(self):
        """Return a file object containing the G-Code data"""
        return open(self.path, "rb")

    def get_file_size(self):
        """The size of the gcode file in bytes"""
        return os.path.getsize(self.path)

    def get_slicer(self):
        """Name of the slicer used to generate the G-Code file"""
        return self.SLICER

    def get_filetype(self):
        return "gcode"

    def get_extruder_count(self):
        """Return the number of extruders the file was spliced for"""
        return 1

    def get_print_dimensions(self):
        """
        The dimensions of the object to print, all figures are in mm.
        Should be a dictionary including the keys:
        MinX, MinY, MinZ, MaxX, MaxY, MaxZ.
        """
        return {"MinX": None, "MinY": None, "MinZ": None,
                "MaxX": None, "MaxY": None, "MaxZ": None}

    def get_time(self):
        """Total print time in seconds"""
        return None

    def get_filament(self, extruder=None, measure=None):
        """
        Return the amount of filament used for the given extruder index
        (starting at 0). If extruder is None, the sum of all extruders is
        returned. The measure used is one of
        "length" in mm, "volume" in mm^3 and "weight" in g.
        measure selects which one to return. If not specified,
        a dictionary containing all values is returned.

        self.convert_filament() will help with this.
        """
        return self.convert_filament(measure=measure)

    def convert_filament(self, length=None, volume=None, weight=None, measure=None):
        """
        Given at least one measurement of length, volume or weight,
        return all other measurements, provided that get_diameter()
        and get_density() are implemented. The diameter set for this
        printer is prioritized, even if it differs from the diameter
        assumed by the slicer.
        measure can be specified to only return one value. By default
        all values are returned in a dictionary.

        Units:
        Length    mm
        Volume    mm^3
        Weight    g
        """
        # Use the actual diameter the printer wants, regardless of what it was sliced for
        diameter = self._module.config_diameter or self.get_diameter()
        if diameter is not None:
            area = pi * (diameter/2)**2  # mm^2
        else:
            area = None
        density = self.get_density()
        if density is not None:
            density /= 1000  # g/mm^3

        if volume:
            if not weight and density:
                weight = volume * density
            if not length and area:
                length = volume / area
        elif length:
            if not volume and area:
                volume = length * area
            if not weight and density:
                weight = volume * density
        elif weight:
            if not volume and density:
                volume = weight / density
            if not length and area:
                length = volume / area
        if measure == "length":
            return length
        elif measure == "volume":
            return volume
        elif measure == "weight":
            return weight
        else:
            return {"length": length, "volume": volume, "weight": weight}

    def get_material_guid(self, extruder=0):
        """
        The GUID of the material file, as recognized by filament_manager.
        This is probably only relevant for Cura files.
        """
        return None

    def get_material_type(self, extruder=0):
        """
        The material type the filament is made of
        """
        return None

    def get_material_brand(self, extruder=0):
        """
        The manufacturer name of the filament
        """
        return None

    def get_material_color(self, extruder=0):
        """
        The color code of the filament in hexadecimal RGB format, e.g: "#bb1e10"
        """
        return None

    def get_density(self, extruder=0):
        """Material density in g/cm^3"""
        return 1.24

    def get_diameter(self, extruder=0):
        """
        Filament diameter in mm according to the slicer.
        For material conversion the actual diameter used by this printer
        is used instead.
        """
        return 1.75

    def get_flavor(self):
        """The G-Code flavor used"""
        return None

    def get_thumbnail_path(self):
        """Full path to a thumbnail image of the object"""
        return None

    def parse_elapsed_time(self, line):
        """
        Return the printing time in seconds up to this line as predicted
        by the slicer. Requires the comment line describing the estimate.
        """
        return None
