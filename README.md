resol-vbus-python
=================

Python Script to read RESOL VBUS Data over LAN
<<<<<<< HEAD
=======

I created this script to display data from my solar installation on an info display (see https://github.com/rellit/InfoMirror).

Usage
-----

The script prints data of received VBUS messages to console in JSON format.

To use this data just call by e.g. PHP

```PHP
$json = `python resol.py`
```

or just write JSON Data to file via:

```shell
!#/bin/sh
resol.py > solar.json
```  

Settings
--------

Some config is needed in order to run this script:

1. IP and port of DataLogger/VBUS_to_LAN Adapter in config.py
2. Number of unique messages to wait for in config.py
    we need this, cause VBUS sends data in an not predictable way. To receive a full output, it is neccessary to know, how     many different messages are expected. Don't choose a too high number, this will cause the script to run forever. Just      find out by try'n'error

3. The spec File to use in config.py  
    Spec files are the dictionary to parse VBUS Messages. They are provided in XML by RESOL as part of the RSC (Resol Service Center) download. Just download, install (on linux use wine, it will work) and get the required file for your installation from: {Install_dir}/eclipse/plugins/de.resol.servicecenter.vbus.resol_2.0.0/

    Provided specs are in XML format. to convert you can use http://www.utilities-online.info/xmltojson
    Also, if the "mask" entry (https://github.com/rellit/resol-vbus-python/blob/master/spec/DeltaSolBXPlus.json#L6) should be missing, you need to set that for your system.
    The correct mask setting can be found here: https://danielwippermann.github.io/resol-vbus/vbus-packets.html
    
    
Debug
-----

If anything wents wrong, xou can enable debug flag in config.py. This will print some basic information while executing the script, but will destroy the JSON output. 
>>>>>>> 39c6e6503515b5917fd1c89aaf42bfd6651f3848
