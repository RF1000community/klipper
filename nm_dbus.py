# coding: utf-8

"""
Needs python-gobject or python-gi
and python-pydbus

TODO:
    test and improve connect, up, down
    connection type change (wifi/eth)
    scan clock mgmt
    only strength of active connection
    .
    .
    .
"""

from gi.repository import GLib
from kivy.event import EventDispatcher
from pydbus import SystemBus

from threading import Thread


_NM = "org.freedesktop.NetworkManager"

class NetworkManager(EventDispatcher, Thread):

    def __init__(self, **kwargs):
        super(NetworkManager, self).__init__(**kwargs)

        self.loop = Glib.MainLoop()
        self.bus = SystemBus()

        # Get proxy objects
        self.nm = self.bus.get(_NM, "/org/freedesktop/NetworkManager")
        self.settings = self.bus.get(_NM, "/org/freedesktop/NetworkManager/Settings")
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
        wifi_prop = self.wifi_dev['org.freedesktop.DBus.Properties']
        wifi_prop.PropertiesChanged.connect(self.handle_scan_complete)

    def handle_scan_complete(self, iface, props, inval):
        """
        Only listens to changes on LastScan, which is changed whenever
        a scan completed.  Parses the access_point_buffer into dictionaries
        containing the relevant properties ssid (name of wifi), signal (in
        percent), in-use (whether we are currently connected with the wifi),
        saved (whether the connection is already known and saved) and path,
        the dbus object path of the access point.
        """
        if not "LastScan" in props:
            return

        access_points = []
        in_use_ap = None
        saved_ssids = self.get_saved_ssids()
        for path in self.wifi_dev.AccessPoints:
            ap_obj = self.bus.get(_NM, path)
            ssid_b = ap_obj.Ssid # type: ay
            # convert to string
            #PYTHON3: ssid = str(bytes(ssid).decode('utf-8'))
            #PYTHON2:
            ssid = ""
            for c in ssid_b:
                ssid += chr(c)
            signal = ap_obj.Strength # type: y
            saved = (ssid_b in saved_ssids)
            entry = {'signal': signal, 'ssid': ssid, 'in-use': False,
                     'saved': saved, 'path': path}
            if path == self.wifi_dev.ActiveAccessPoint:
                entry['in-use'] = True
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

    def handle_new_connection(self, state, reason):
        """
        Receives state changes from newly added connections.
        Required to ensure everything went OK and to dispatch events
        in case it didn't.  The most important case would be a wrong
        password which will be detected by the reason argument.

        The signal subscription will be canceled when the connection
        was successfully activated.
        """
        #TODO: improve maybe
        if state > 2: # DEACTIVATING or DEACTIVATED
            if reason == 9: # NO_SECRETS
                self.dispatch('on_wrong_password')
            elif reason > 1: # not UNKNOWN or NONE
                self.dispatch('on_connect_failed')
        if state in (2, 4): # ACTIVATED or DEACTIVATED
            # done, no need to listen further
            self.new_connection_subscription.disconnect()


    def wifi_connect(self, ssid, password):
        """
        From ssid and password (both as plaintext strings) get all the
        information needed to either create and connect or just connect
        the connection.  Relies on the data in self.access_points.

        This method is likely to raise a ValueError or Error in
        AddAndActivateConnection.  Exception catching is advised.

        Returns path to the new connection (in settings)
        """
        data = None
        for ap in self.access_points:
            if ssid == ap['ssid']:
                data = ap
                break
        if data is None or data['path'] not in self.wifi_dev.AccessPoints:
            # Network got out of view since previous scan
            raise ValueError("Network " + ssid + " is not in view.")
        if data['saved']:
            # You called the wrong method
            self.up(ssid)
            return
        password = GLib.Variant('s', password)
        connection_info = {'802-11-wireless-security': {'psk': password}} # type: a{sa{sv}}
        con, active = self.nm.AddAndActivateConnection(
            connection_info, self.wifi_dev.__dict__['_path'], data['path'])
        active = self.bus.get(_NM, active)
        self.new_connection_subscription = active.StateChanged.connect(self.handle_new_connection)
        return con

    def wifi_up(self, ssid):
        """Activate a connection that is already stored"""
        data = None
        for ap in self.access_points:
            if ssid == ap['ssid']:
                data = ap
                break
        if data is None or not(data['path'] in self.wifi_dev.AccessPoints and data['saved']):
            raise Exception("Can't activate connection " + ssid)
        active = self.nm.ActivateConnection("/", self.wifi_dev.__dict__['_path'], data['path'])
        active = self.bus.get(_NM, active)
        self.new_connection_subscription = active.StateChanged.connect(self.handle_new_connection)

    def wifi_down(self):
        """Deactivate the currently active wifi connection, if any"""
        active = self.wifi_dev.ActiveConnection
        if active == "/":
            return False
        self.nm.DeactivateConnection(active)
        return True

    def wifi_delete(self, ssid):
        """Delete a saved connection with the given ssid (string)"""
        ssid_b = [ord(c) for c in a]
        connection_paths = self.settings.Connections # type: ao
        for path in connection_paths:
            con = self.bus.get(_NM, path)
            settings = con.GetSettings() # type: a{sa{sv}}
            if '802-11-wireless' in settings: # Only check wifi connections
                if ssid_b == settings['802-11-wireless']['ssid']:
                    con.Delete()
                    return True
        return False

    def get_saved_ssids(self):
        """Return list of ssid bytearrays of all stored Wi-Fi connections"""
        connection_paths = self.settings.Connections # type: ao
        ssids = []
        for path in connection_paths:
            con = self.bus.get(_NM, path)
            settings = con.GetSettings() # type: a{sa{sv}}
            if '802-11-wireless' in settings: # Wired connections don't have ssids
                ssid_b = settings['802-11-wireless']['ssid']
                ssids.append(ssid_b)
        return ssids

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
