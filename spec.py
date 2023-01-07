#!/usr/bin/env python3

__author__ = 'Tim'
import json
import sys
import config

# Load given specFile. Specfile was created from original
# RESOL Configuration File XML shippes with RSC (Resol Service Center)
# using XML to JSON converter at http://www.utilities-online.info/xmltojson
with open(config.spec_file) as json_data:
    data = json.load(json_data)
    try:
        spec = data['vbusSpecification']
    except:
        sys.exit('Cannot load Spec')

if config.debug:
    for device in spec['device']:
        print(device)

    for packet in spec['packet']:
        print(packet)
        for field in packet['field']:
            print("  " + str(field))

json_data.close()
