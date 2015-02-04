#!/usr/bin/env python2

# 
# Talk with Resol VBUS over LAN
#

import socket
import time
import sys
import json

# Load settings
try:
    import config
except:
    sys.exit("config.py not found!")

# Load Message specification
try:
    import spec
except:
    sys.exit("Could not load Message Specification")


# Logs in onto the DeltaSol BS Plus over LAN. Also starts (and maintains) the
# actual stream of data.
def login():
    dat = recv()

    #Check if device answered
    if dat != "+HELLO\n":
        return False

    #Send Password
    send("PASS %s\n" % config.vbus_pass)

    dat = recv()

    return dat.startswith("+OK")


def load_data():
    #Request Data
    send("DATA\n")

    dat = recv()

    #Check if device is ready to send Data
    if not dat.startswith("+OK"):
        return

    while len(result) < config.expected_packets:
        buf = readstream()
        msgs = splitmsg(buf)
        for msg in msgs:
            if "PV1" == get_protocolversion(msg):
                if config.debug:
                    print format_message_pv1(msg)
                parse_payload(msg)
            elif "PV2" == get_protocolversion(msg):
                if config.debug:
                    print format_message_pv2(msg)


# Receive 1024 bytes from stream
def recv():
    dat = sock.recv(1024)
    return dat


# Sends given bytes over the stram. Adds debug
def send(dat):
    sock.send(dat)


# Read Data until minimum 1 message is received
def readstream():
    data = recv()
    while data.count(chr(0xAA)) < 4:
        data += recv()
    return data


#Split Messages on Sync Byte
def splitmsg(buf):
    return buf.split(chr(0xAA))[1:-1]


# Format 1 byte as String
def format_byte(byte):
    return hex(ord(byte))[0:2] + '0' + hex(ord(byte))[2:] if len(hex(ord(byte))) < 4 else hex(ord(byte))


# Extract protocol Version from msg
def get_protocolversion(msg):
    if hex(ord(msg[4])) == '0x10': return "PV1"
    if hex(ord(msg[4])) == '0x20': return "PV2"
    if hex(ord(msg[4])) == '0x30': return "PV3"
    return "UNKNOWN"


# Extract Destination from msg
def get_destination(msg):
    return format_byte(msg[1]) + format_byte(msg[0])[2:]


#Extract source from msg
def get_source(msg):
    return format_byte(msg[3]) + format_byte(msg[2])[2:]


# Extract command from msg
def get_command(msg):
    return format_byte(msg[6]) + format_byte(msg[5:6])[2:]


# Get count of frames in msg
def get_frame_count(msg):
    return gb(msg, 7, 8)


# Extract payload from msg
def get_payload(msg):
    payload = ''
    for i in range(get_frame_count(msg)):
        payload += integrate_septett(msg[9+(i*6):15+(i*6)])
    return payload


# parse payload and put result in result
def parse_payload(msg):
    payload = get_payload(msg)
    for packet in spec.spec['packet']:
        if packet['source'] == get_source(msg) and packet['destination'] == get_destination(msg) and packet['command'] == get_command(msg):
            #print packet

            result[get_source_name(msg)] = {}
            for field in packet['field']:
                result[get_source_name(msg)][field['name'][0]] = str(gb(payload, int(field['offset']), int(field['offset'])+((int(field['bitSize'])+1) / 8)) * (float(field['factor']) if field.has_key('factor') else 1)) + field['unit'] if 'unit' in field else ''


def format_message_pv1(msg):
    parsed = "PARSED: \n"
    parsed += "    ZIEL".ljust(15,'.')+": " + get_destination(msg) + "\n"
    parsed += "    QUELLE".ljust(15,'.')+": " + get_source(msg) + " " + get_source_name(msg) + "\n"
    parsed += "    PROTOKOLL".ljust(15,'.')+": " + get_protocolversion(msg) + "\n"
    parsed += "    BEFEHL".ljust(15,'.')+": " + get_command(msg) + "\n"
    parsed += "    ANZ_FRAMES".ljust(15,'.')+": " + str(get_frame_count(msg)) + "\n"
    parsed += "    CHECKSUM".ljust(15,'.')+": " + format_byte(msg[8]) + "\n"
    for i in range(get_frame_count(msg)):
        integrated = integrate_septett(msg[9+(i*6):15+(i*6)])
        parsed += ("    NB"+str(i*4+1)).ljust(15,'.')+": " + format_byte(msg[9+(i*6)]) + " - " + format_byte(integrated[0]) + "\n"
        parsed += ("    NB"+str(i*4+2)).ljust(15,'.')+": " + format_byte(msg[10+(i*6)]) + " - " + format_byte(integrated[1]) + "\n"
        parsed += ("    NB"+str(i*4+3)).ljust(15,'.')+": " + format_byte(msg[11+(i*6)]) + " - " + format_byte(integrated[2]) + "\n"
        parsed += ("    NB"+str(i*4+4)).ljust(15,'.')+": " + format_byte(msg[12+(i*6)]) + " - " + format_byte(integrated[3]) + "\n"
        parsed += ("    SEPTETT"+str(i+1)).ljust(15,'.')+": " + format_byte(msg[13+(i*6)]) + "\n"
        parsed += ("    CHECKSUM"+str(i+1)).ljust(15,'.')+": " + format_byte(msg[14+(i*6)]) + "\n"
    parsed += "    PAYLOAD".ljust(15,'.')+": " + (" ".join(format_byte(b) for b in get_payload(msg)))+"\n"

    return parsed


def format_message_pv2(msg):
    parsed = "PARSED: \n"
    parsed += "    ZIEL1".ljust(15,'.')+": " + format_byte(msg[0:1]) + "\n"
    parsed += "    ZIEL2".ljust(15,'.')+": " + format_byte(msg[1:2]) + "\n"
    parsed += "    QUELLE1".ljust(15,'.')+": " + format_byte(msg[2:3]) + "\n"
    parsed += "    QUELLE2".ljust(15,'.')+": " + format_byte(msg[3:4]) + "\n"
    parsed += "    PROTOKOLL".ljust(15,'.')+": " + format_byte(msg[4:5]) + "\n"
    parsed += "    BEFEHL1".ljust(15,'.')+": " + format_byte(msg[5:6]) + "\n"
    parsed += "    BEFEHL2".ljust(15,'.')+": " + format_byte(msg[6:7]) + "\n"
    parsed += "    ID1".ljust(15,'.')+": " + format_byte(msg[7:8]) + "\n"
    parsed += "    ID2".ljust(15,'.')+": " + format_byte(msg[8:9]) + "\n"
    parsed += "    WERT1".ljust(15,'.')+": " + format_byte(msg[9:10]) + "\n"
    parsed += "    WERT2".ljust(15,'.')+": " + format_byte(msg[10:11]) + "\n"
    parsed += "    WERT3".ljust(15,'.')+": " + format_byte(msg[11:12]) + "\n"
    parsed += "    WERT4".ljust(15,'.')+": " + format_byte(msg[12:13]) + "\n"
    parsed += "    SEPTETT".ljust(15,'.')+": " + format_byte(msg[13:14]) + "\n"
    parsed += "    CHECKSUM".ljust(15,'.')+": " + format_byte(msg[14:15]) + "\n"

    return parsed


def get_compare_length(mask):
    i = 1
    while i < 6 and mask[i] != '0':
        i += 1
    return i+1


def get_source_name(msg):
    src = format_byte(msg[3]) + format_byte(msg[2])[2:]
    for device in spec.spec['device']:
        if src[:get_compare_length(device['mask'])] == device['address'][:get_compare_length(device['mask'])]:
            return device['name'] if get_compare_length(device['mask']) == 7 else str(device['name']).replace('#',device['address'][get_compare_length(device['mask'])-1:],1)
    return ""


def integrate_septett(frame):
    data = ''
    septet = ord(frame[4])

    for j in range(4):
        if septet & (1 << j):
            data += chr(ord(frame[j]) | 0x80)
        else:
            data += frame[j]

    return data


# Gets the numerical value of a set of bytes
def gb(data, begin, end):  # GetBytes
    return sum([ord(b) << (i * 8) for i, b in enumerate(data[begin:end])])
    
    
# Gets the numerical value of a set of bytes (2s complement)
def gbc(data, begin, end):  # GetBytes
    wbg = sum([ord(0xff) << (i * 8) for i, b in enumerate(data[begin:end])])
    s = sum([ord(b) << (i * 8) for i, b in enumerate(data[begin:end])])
    
    
    if s >= wbg/2:
        s = wbg - s
        s *= -1
    return s
    

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.connect(config.address)

    result = dict()

    login()

    load_data()

    print json.dumps(result)

    try:
        sock.shutdown(0)
    except:
        pass
    sock.close()
    sock = None


