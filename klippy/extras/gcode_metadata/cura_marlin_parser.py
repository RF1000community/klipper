import re

from .base_parser import BaseParser

class CuraMarlinParser(BaseParser):

    PATTERN_DETECT = re.compile("Generated with Cura_SteamEngine",
                                flags=re.IGNORECASE)
    DELIMITER = ":"
    SLICER = "Cura"

    @classmethod
    def _detect(cls, lines):
        """Slicer info is at end of head, so optimize for that"""
        return super()._detect(reversed(lines))

    def get_flavor(self):
        return self.options.get("FLAVOR")

    def get_extruder_count(self):
        """
        The number of extruders can be determined by the number of
        filament figures.
        """
        filament = self.options.get("Filament used")
        if filament is None:
            return None
        return filament.count(",") + 1

    def get_print_dimensions(self):
        return {"MinX": self.options.get("MINX"),
                "MinY": self.options.get("MINY"),
                "MinZ": self.options.get("MINZ"),
                "MaxX": self.options.get("MAXX"),
                "MaxY": self.options.get("MAXY"),
                "MaxZ": self.options.get("MAXZ")}

    def get_time(self):
        return self.options.get("TIME")

    def get_filament(self, extruder=None, measure=None):
        fil = self.options.get("Filament used")
        if fil is None:
            return None
        filament_per_extruder = fil.split(",", 1)
        if extruder is not None:
            filament_per_extruder = filament_per_extruder[extruder:extruder+1]
        if "volumetric" in self.get_flavor().lower():
            # Strip whitespaces and mm3
            volume = sum(iter(float(f.strip()[:-3])
                              for f in filament_per_extruder))
            return self.convert_filament(volume=volume, measure=measure)
        else:
            length_m = sum(iter(float(f.strip(" m"))
                                for f in filament_per_extruder))
            length = length_m * 1000  # Convert to mm
            return self.convert_filament(length=length, measure=measure)

    PATTERN_ELAPSED_TIME = re.compile(
            r";?TIME_ELAPSED\s*:\s*(?P<seconds>\d*\.?\d*)")

    def parse_elapsed_time(self, line):
        match = re.match(self.PATTERN_ELAPSED_TIME, line)
        if match:
            elapsed_time = match.group("seconds")
            try:
                elapsed_time = float(elapsed_time)
            except ValueError:
                return None
            return elapsed_time
