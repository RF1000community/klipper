# Persistant Printjob History for virtual_sdcard
#
# Copyright (C) 2020  Gabriel Vogel
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging, time
from os.path import expanduser


class PrintjobHistory:
    """
    Manage print history file

    The history file is json-formatted as a list of lists each containing
    the elements
        [path, state, timestamp],
    whith path being the path of the gcode file,
    status being a string defining the outcome of the print, one of
        "done", "stopped",
    timestamp being the time of completion in seconds since epoch.
    """
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.history_path = expanduser("~/history.json")
        self.history = self.read()
        self.trim_history()
        self.printer.register_event_handler("virtual_sdcard:printjob_ended", self.add)

    def trim_history(self):
        """Remove all entries of deleted files, return number of removed entries"""
        history = self.history
        to_remove = []
        for e in history:
            if not exists(e[0]):
                to_remove.append(e)
        if to_remove != []:
            for e in to_remove:
                history.remove(e)
            self.write(history)
            self.history = history
            return len(to_remove)
        return 0

    def read(self):
        """Read the history file and return it as a list object"""
        try:
            with open(self.history_path, "r") as fp:
                history = json.load(fp)
        except (IOError, ValueError): # No file or incorrect JSON
            logging.info("History: Couldn't read file at {}".format(self.history_path))
            history = []
        if not self.verify_history(history):
            logging.warning("History: Malformed history file")
            history = []
        return history

    def verify_history(self, history):
        """Only return True when the entire history has a correct structure"""
        try:
            for e in history:
                if not (isinstance(e[0], (unicode, str))        # path
                and (e[1] == "done" or e[1] == "stopped")       # state
                and isinstance(e[2], (float, int))):            # timestamp
                    return False
        except:
            return False
        return True

    def write(self, history):
        """Write the object to the history file"""
        try:
            with open(self.history_path, "w") as fp:
                json.dump(history, fp, indent=True)
        except IOError:
            return

    def add(self, path, state):
        """Add a new entry to the history with the path and state string specified"""
        self.history.append([path, state, time.time()])
        self.write(self.history)

def load_config(config):
    return PrintjobHistory(config)
