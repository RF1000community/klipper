# Klipper Cura connection

A Klipper module that enables a network connection with Cura.

## Important files to look at:

* cura/Machines/Models/DiscoveredPrintersModel.py
* cura/PrinterOutput/NetworkedPrinterOutputDevice.py

### Objects

* GlobalStack (Machine) and ContainerStack etc.
* OutputDevice(Manager)

## Good to know

Id, key, name are all synonymously used for the name property
set as name in the zeroconf property dictionary.

Device refers to detected, usable printers, Machine refers
to printers added in Cura.

## TODO

* Handle all possible requests in HTTP Server
* Aquire information
    * Materials
* Figure out which file type to send and if to compress.  
    Currently uncompressed GCode files are sent  
    Possibly use ufp.
* Figure out if it is really necessary to disguise as an Ultimaker3  
    Otherwise custom sizes will need to be set differently.
* Figure out a way to determine a unique printer name (hostname?)
* Receive IPv4 Address from network manager  
    (dbus implemented function exists: kgui/nm\_dbus.py)
* Implement testing mode to test the module without klipper
* Video stream?

## What's happening in Cura?

* The Output plugin detects networked printers via zeroconf
* They get checked for some values in the propertie dict
* When the user adds that device, a new machine (Stack) is created
* Further communication happens via the IP address on HTTP
* Every 2 seconds \_update() is called on all device objects.
    This continuously requests printers and print_jobs status data
* When clicking "Print over network" the file is sent in a multipart POST request.

## Setup

`python-libcharon` needed to be installed for me so that the
UFPWriter and UFPReader plugins of Cura can work. Otherwise
an exception is generated when trying to send a file.

### Port redirection

Root privileges are required to listen to port 80, the default HTTP port.
Because of that we redirect packets to 8080 and listen to that instead.
We then make these persistent with installing iptables-persistent.
With the configurations set first the installation is automatic and the
rules we just set are written to /etc/iptables/rule.v4.

```bash
sudo iptables -A PREROUTING -t nat -p tcp --dport 80 -j REDIRECT --to-ports 8080
echo iptables-persistent iptables-persistent/autosave_v4 boolean true | sudo debconf-set-selections
echo iptables-persistent iptables-persistent/autosave_v6 boolean false | sudo debconf-set-selections
sudo apt -y install iptables-persistent
```

## Info on possible requests

All come from `KlipperNetworkPrinting/src/Network/ClusterApiClient.py`

|Name                   |Type   |URL (/cluster-api/v1 + .)      |Data (sent or requested)       |Notes
|-----------------------|-------|-------------------------------|-------------------------------|-----------------------
|getSystem              |GET    |!/api/v1/system                |PrinterSystemStatus            |For manual connection
|getMaterials           |GET    |/materials                     |[ClusterMaterial]              |
|getPrinters            |GET    |/printers                      |[ClusterPrinterStatus]         |Periodically requested
|getPrintJobs           |GET    |/print\_jobs                   |[ClusterPrintJobStatus]        |Periodically requested
|setPrintJobState       |PUT    |/print\_jobs/UUID/action       |("pause", "print", "abort")    |
|movePrintJobToTop      |POST   |/print\_jobs/UUID/action/move  |json{"to\_position": 0, "list": "queued"}|
|forcePrintJob          |PUT    |/print\_jobs/UUID              |json{"force": True}            |
|deletePrintJob         |DELETE |/print\_jobs/UUID              |                               |
|getPrintJobPreviewImage|GET    |/print\_jobs/UUID/preview\_image|?                             |
