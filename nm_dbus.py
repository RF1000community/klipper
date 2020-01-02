# coding: utf-8

"""
Needs python-gobject or python-gi
and python-pydbus
"""

from gi.repository.GLib import MainLoop
from kivy.event import EventDispatcher
from pydbus import SystemBus

from threading import Thread


_NM = "org.freedesktop.NetworkManager"

class NetworkManager(EventDispatcher, Thread):

    def __init__(self, **kwargs):
        super(NetworkManager, self).__init__(**kwargs)

        self.loop = MainLoop()
        self.bus = SystemBus()

        # Get proxy objects
        self.nm = self.bus.get(_NM, "/org/freedesktop/NetworkManager")
        devices = self.nm.Devices # type: ao
        for dev in devices:
            dev_obj = self.bus.get(_NM, dev)
            if dev_obj.DeviceType == 1: # 1 := a wired ethernet device
                self.eth_dev = dev_obj
            elif dev_obj.DeviceType == 2: # 2 := an 802.11 Wi-Fi device
                self.wifi_dev = dev_obj

        self.connect_signals()

        self.register_event_type('on_access_points')
        self.access_point_buffer = self.wifi_dev.AccessPoints
        self.access_points = []
        self.handle_scan_complete(None, {'LastScan': 0}, None)

    def run(self):
        """Executed by Thread.start(). This thread stops when this method finishes."""
        self.loop.run()

    def connect_signals(self):
        """Connect DBus signals to their callbacks.  Called in __init__"""
        self.wifi_dev.AccessPointAdded.connect(self.handle_access_point_added)
        self.wifi_dev.AccessPointRemoved.connect(self.handle_access_point_removed)
        wifi_prop = self.wifi_dev['org.freedesktop.DBus.Properties']
        wifi_prop.PropertiesChanged.connect(self.handle_scan_complete)


    def handle_access_point_added(self, ap):
        """
        Add an access point to the buffer as soon as it gets into the
        view of the wifi device.
        """
        if ap not in self.access_point_buffer:
            self.access_point_buffer.append(ap)

    def handle_access_point_removed(self, ap):
        """
        Removes an access point from the buffer as soon as it falls out
        of view of the wifi device.
        """
        try:
            self.access_point_buffer.remove(ap)
        except ValueError:
            # In case ap is not in buffer
            pass

    def handle_scan_complete(self, iface, props, inval):
        """
        Only listens to changes on LastScan, which is changed whenever
        a scan completed.  Parses the access_point_buffer into dictionaries
        containing the relevant properties ssid (name of wifi), signal (in
        percent) and in-use (whether we are currently connected with the wifi)

        """
        # TODO: Reevaluate selection of properties
        if not "LastScan" in props:
            return

        access_points = []
        in_use_ap = None
        for ap in self.access_point_buffer:
            ap_obj = self.bus.get(_NM, ap)
            ssidl = ap_obj.Ssid # type: ay
            # convert to string
            #PYTHON3: ssid = str(bytes(ssid).decode('utf-8'))
            #PYTHON2:
            ssid = ""
            for c in ssidl:
                ssid += chr(c)
            signal = ap_obj.Strength # type: y
            in_use = (ap == self.wifi_dev.ActiveAccessPoint)
            entry = {'signal': signal, 'in-use': in_use, 'ssid': ssid}
            if in_use:
                in_use_ap = entry
            else:
                # Get the correct point to insert, so that the list stays sorted
                index = len(access_points)
                while index > 0 and signal > access_points[index-1]['signal']:
                    index -= 1
                access_points.insert(index, entry)
        if in_use_ap:
            access_points.insert(0, in_use_ap)
        self.access_points = access_points
        self.dispatch('on_access_points', self.access_points)



    def get_active_connection(self):
        """Return a proxy object to the primary connection, None if not connected"""
        con = self.nm.PrimaryConnection
        if con == "/":
            return None
        return self.bus.get(_NM, con)

    def get_ip4_address(self):
        """
        Return the IPv4 Address of the network device currently in use.
        Return None if there is no active connection.
        """
        active = self.get_active_connection()
        if active is None:
            return None
        config = self.bus.get(_NM, active.Ip4Config)
        return config.AddressData[0]['address'] # type: aa{sv}


    def on_access_points(self, aps):
        print(aps)
