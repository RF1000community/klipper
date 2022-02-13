import os
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from .base_parser import BaseParser

_GCODE_PATH = "/3D/model.gcode"

def create_ufp_reader(path, module):
    """
    Find the right parser class and add it as a baseclass to _UFPReader.
    An instance of this new class is returned that follows the BaseParser API.
    """
    zip_obj = ZipFile(path)
    if _GCODE_PATH not in zip_obj.namelist():
        raise FileNotFoundError("Can't locate .gcode file in UFP package")
    fp = zip_obj.open(_GCODE_PATH)
    head = module._get_head_md(fp)
    ParserClass = module._find_parser(head)
    tail = []
    # Only read the tail if needed, because the entire file needs to be decompressed for that
    if ParserClass is BaseParser:  # Couldn't find a parser class
        tail = module._get_tail_md(fp)
        ParserClass = module._find_parser(tail)
    elif ParserClass._needs_tail:  # Parser needs to read the tail
        tail = module._get_tail_md(fp)
    fp.close()

    UFPParserClass = _UFPReader.add_baseclass(ParserClass)
    ufp_parser = UFPParserClass(path, module, zip_obj, head, tail)
    return ufp_parser


class _UFPMetaClass(type):
    """
    Add the ability to dynamically add different base classes to a class.
    """
    def __init__(self, clsname, bases, attrs):
        # Save class attributes and bases so we can create new ones in the future
        self._attrs = attrs
        self._bases = bases

    def add_baseclass(self, base):
        return super().__new__(__class__, "UFP" + base.__name__, (*self._bases, base), self._attrs)


class _UFPReader(metaclass=_UFPMetaClass):
    """
    This class acts as an additional level ontop of the Parser base class
    that takes care of opening the UFP file and adds additional functionality
    unique to that format.

    THIS CLASS CANNOT BE USED ON ITS OWN.
    A baseclass must be added that inherits BaseParser (or BaseParser) using
    _UFPReader.add_baseclass(BASE)
    This class-level function add_baseclass is added by the metaclass _UFPMetaClass.
    """

    _gcode_path = _GCODE_PATH
    _gcode_relationship_path = "/3D/_rels/model.gcode.rels"

    _thumbnail_relationship_type = "http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"
    _material_relationship_type = "http://schemas.ultimaker.org/package/2018/relationships/material"

    def __init__(self, path, module, zip_obj, head, tail):
        super(self.__class__, self).__init__(head, tail, path, module)
        self.path = path
        self._module = module
        self._zip_obj = zip_obj

        self.thumbnail_path = None
        self._material_guids = []
        self._relationships = self._get_relationships()
        self._extract_thumbnail()
        self._extract_materials()

    def get_gcode_stream(self):
        if self._gcode_path not in self._zip_obj.namelist():
            raise FileNotFoundError("Can't locate .gcode file in UFP package")
        return self._zip_obj.open(self._gcode_path)

    def get_file_size(self):
        if self._gcode_path not in self._zip_obj.namelist():
            raise FileNotFoundError("Can't locate .gcode file in UFP package")
        return self._zip_obj.getinfo(self._gcode_path).file_size

    def _get_relationships(self):
        """
        Return the file relationships from the gcode file in the UFP package.
        Each element is a dictionary containing the fields Target, Type and Id.
        """
        if self._gcode_relationship_path not in self._zip_obj.namelist():
            return []
        with self._zip_obj.open(self._gcode_relationship_path) as rel_fp:
            root = ET.parse(rel_fp).getroot()
        ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
        relationships = [e.attrib for e in root.findall("r:Relationship", ns)]
        # Make sure the list is sorted right
        relationships.sort(key = lambda e: e.get("Id"))
        return relationships

    def _extract_thumbnail(self):
        """Write the thumbnail into the .thumbnails directory"""
        virtual_path = next(iter(e["Target"] for e in self._relationships
                if e["Type"] == self._thumbnail_relationship_type), None)
        if virtual_path is None:
            return
        thumbnail_dir = os.path.dirname(self.path) + "/.thumbnails/"
        if not os.path.exists(thumbnail_dir):
            os.mkdir(thumbnail_dir)
        thumbnail_path = thumbnail_dir + os.path.basename(self.path) + ".png"
        with open(thumbnail_path, "wb") as thumbnail_target:
            thumbnail_target.write(self._zip_obj.read(virtual_path))
        self.thumbnail_path = thumbnail_path

    def _extract_materials(self):
        """ #TODO
        In case a material file isn't present yet on this system, it gets
        extracted and added to the filament manager.
        """
        return None
        # material_paths = [e["Target"] for e in self._relationships
        #                   if e["Type"] == self._material_relationship_type]

    @staticmethod
    def register_materials(e, printer, material_paths):
        for material in material_paths:
            material_file = self._zip_obj.open(material)
            guid = fm.get_info(material_file, "./m:metadata/m:GUID")
            material_file.seek(0)
            version = fm.get_info(material_file, "./m:metadata/m:version")
            if not (guid in fm.guid_to_path and
                    version == fm.get_info(guid, "./m:metadata/m:version")):
                # New material, needs to be extracted
                new_material_path = os.path.join(fm.material_dir, os.path.basename(material))
                material_file.seek(0)
                with open(new_material_path, "wb") as fp:
                    fp.write(material_file.read())
                fm.read_single_file(new_material_path)
            material_file.close()
            self._material_guids.append(guid)

    def get_filetype(self):
        return "ufp"

    def get_material_guid(self, extruder=0):
        if not self._material_guids:
            return None
        # If multiple extruders use the same material there are less
        # materials than extruders
        extruder = min(extruder, len(self._material_guids) - 1)
        guid = self._material_guids[extruder]
        return guid

    def get_material_info(self, xpath, extruder=0):
        guid = self.get_material_guid(extruder)
        if not guid:
            return None
        return self.reactor.cb(self.obtain_material_info, guid, xpath, wait=True)

    @staticmethod
    def obtain_material_info(e, printer, guid, xpath):
        return printer.objects['filament_manager'].get_info(guid, xpath)

    def get_material_type(self, extruder=0):
        return self.get_material_info("./m:metadata/m:name/m:material", extruder)

    def get_material_brand(self, extruder=0):
        return self.get_material_info("./m:metadata/m:name/m:brand", extruder)

    def get_material_color(self, extruder=0):
        return self.get_material_info("./m:metadata/m:color_code", extruder)

    def get_density(self, extruder=0):
        density = self.get_material_info("./m:properties/m:density", extruder)
        try:
            density = float(density)
        except (ValueError, TypeError):
            # self.__class__ may be different to __class__ here
            return super(self.__class__, self).get_density(extruder)
        return density

    def get_diameter(self, extruder=0):
        diameter = self.get_material_info("./m:properties/m:diameter", extruder)
        try:
            diameter = float(diameter)
        except (ValueError, TypeError):
            return super(self.__class__, self).get_diameter(extruder)
        return diameter

    def get_thumbnail_path(self):
        return self.thumbnail_path

    def __del__(self):
        self._zip_obj.close()
