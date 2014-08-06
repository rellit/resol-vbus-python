__author__ = 'Tim'
import json

spec_file = 'spec/DeltaSolBXPlus.json'

with open(spec_file) as json_data:
    data = json.load(json_data)
    print data
    try:

        spec = data['vbusSpecification']
    except:
        raise NameError('Cannot load Spec')

print spec

for device in spec['device']:
    print device

for packet in spec['packet']:
    print packet
    for field in packet['field']:
        print packet['source'] + str(field)
        try:
            print field['factor']
        except: continue

json_data.close()