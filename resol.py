#!/usr/bin/env python3

#
# Talk with Resol VBUS over LAN or serial UART
#

import socket
import sys
import json
from decimal import *

# Load settings
try:
    import config
except:
    sys.exit("config.py not found!")

if config.connection == "serial":
    # import serial (pyserial) only if it's configured to not force installing it without needing
    import serial

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
    if dat.decode('ascii') != "+HELLO\n":
        return False

    #Send Password
    send(("PASS %s\n" % config.vbus_pass).encode('ascii'))

    dat = recv()

    return dat.startswith("+OK".encode('ascii'))


def load_data():
    if config.connection == "lan":
        #Request Data
        send("DATA\n".encode('ascii'))

        dat = recv()

        #Check if device is ready to send Data
        if not dat.startswith("+OK".encode('ascii')):
            return

    while len(result) < config.expected_packets:
        buf = readstream()

        msgs = splitmsg(buf)
        if config.debug:
            print(str(len(msgs))+" Messages, "+str(len(result))+" Resultlen")
        for msg in msgs:
            if config.debug: print(get_protocolversion(msg))
            if "PV1" == get_protocolversion(msg):
                if config.debug: print(format_message_pv1(msg))
                parse_payload(msg)
            elif "PV2" == get_protocolversion(msg):
                if config.debug: print(format_message_pv2(msg))

# Receive 1024 bytes from stream
def recv():
    if config.connection == "serial":
        # timeout needs to be set to 0 (see init), or it will
        # block until the requested number of bytes is read
        dat = sock.read(1024)
    elif config.connection == "lan":
        dat = sock.recv(1024)
    elif config.connection == "stdin":
        dat = sock.buffer.read(1024)
    else:
        sys.exit('Unknown connection type. Please check config.')
    return dat


# Sends given bytes over the stream. Adds debug
def send(dat):
    sock.send(dat)


# Read data until minimum 1 message is received
# We cyclic get:
# '0xaa' '0x00' '0x00' '0x21' '0x74' '0x20' ...
# '0xaa' '0x15' '0x00' '0x21' '0x74' '0x10' ...
# '0xaa' '0x10' '0x00' '0x21' '0x74' '0x10' ...
# Only the last one is needed, so we need 4 times '0xaa'!
def readstream():
    data = bytearray(b'')
    data.extend(recv())
    while data.count(0xAA) < 4:
        data.extend(recv())
    return data


#Split Messages on Sync Byte
def splitmsg(buf):
    return buf.split(b'\xAA')[1:-1]


# Format 1 byte as String Hex string
def format_byte(byte):
    return '0x' + ('0' if byte < 0x10 else '') + format(byte, 'x')


# Extract protocol Version from msg
def get_protocolversion(msg):
    if msg[4] == 0x10: return "PV1"
    if msg[4] == 0x20: return "PV2"
    if msg[4] == 0x30: return "PV3"
    return "UNKNOWN"


# Extract Destination from msg
def get_destination(msg):
    return format_byte(msg[1]) + format_byte(msg[0])[2:]


#Extract source from msg
def get_source(msg):
    return format_byte(msg[3]) + format_byte(msg[2])[2:]


# Extract command from msg
def get_command(msg):
    return format_byte(msg[6]) + format_byte(msg[5])[2:]


# Get count of frames in msg
def get_frame_count(msg):
    return gb(msg, 7, 8)


# Extract payload from msg
def get_payload(msg):
    payload = bytearray(b'')
    for i in range(get_frame_count(msg)):
        payload.extend(integrate_septett(msg[9+(i*6):15+(i*6)]))
    return payload


# parse payload and put result in result
def parse_payload(msg):
    payload = get_payload(msg)

    if config.debug:
         print('ParsePacket Payload '+str(len(payload)))

    for packet in spec.spec['packet']:
        if packet['source'].lower() == get_source(msg).lower() and \
                packet['destination'].lower() == get_destination(msg).lower() and \
                packet['command'].lower() == get_command(msg).lower():
            result[get_source_name(msg)] = {}
            for field in packet['field']:
                result[get_source_name(msg)][field['name']] = \
                    str(
                        gb(payload, field['offset'], int(field['offset'])+((int(field['bitSize'])+1) / 8)) *
                        (Decimal(field['factor']) if 'factor' in field else 1)
                    ) + \
                    (field['unit']
                        if config.use_units
                        and 'unit' in field
                        and isinstance(field['unit'], str)
                     else '')

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
    parsed += "    ZIEL1".ljust(15,'.')+": " + format_byte(msg[0]) + "\n"
    parsed += "    ZIEL2".ljust(15,'.')+": " + format_byte(msg[1]) + "\n"
    parsed += "    QUELLE1".ljust(15,'.')+": " + format_byte(msg[2]) + "\n"
    parsed += "    QUELLE2".ljust(15,'.')+": " + format_byte(msg[3]) + "\n"
    parsed += "    PROTOKOLL".ljust(15,'.')+": " + format_byte(msg[4]) + "\n"
    parsed += "    BEFEHL1".ljust(15,'.')+": " + format_byte(msg[5]) + "\n"
    parsed += "    BEFEHL2".ljust(15,'.')+": " + format_byte(msg[6]) + "\n"
    parsed += "    ID1".ljust(15,'.')+": " + format_byte(msg[7]) + "\n"
    parsed += "    ID2".ljust(15,'.')+": " + format_byte(msg[8]) + "\n"
    parsed += "    WERT1".ljust(15,'.')+": " + format_byte(msg[9]) + "\n"
    parsed += "    WERT2".ljust(15,'.')+": " + format_byte(msg[10]) + "\n"
    parsed += "    WERT3".ljust(15,'.')+": " + format_byte(msg[11]) + "\n"
    parsed += "    WERT4".ljust(15,'.')+": " + format_byte(msg[12]) + "\n"
    parsed += "    SEPTETT".ljust(15,'.')+": " + format_byte(msg[13]) + "\n"
    parsed += "    CHECKSUM".ljust(15,'.')+": " + format_byte(msg[14]) + "\n"
    return parsed


def get_compare_length(mask):
    i = 1
    while i < 6 and mask[i] != '0':
        i += 1
    return i+1


def get_source_name(msg):
    src = format_byte(msg[3]) + format_byte(msg[2])[2:]
    for device in spec.spec['device']:
        if src[:get_compare_length(device['mask'])].lower() == device['address'][:get_compare_length(device['mask'])].lower():
            return device['name'] if get_compare_length(device['mask']) == 7 else str(device['name']).replace('#',device['address'][get_compare_length(device['mask'])-1:],1)
    return ""


def integrate_septett(frame):
    data = bytearray(b'')
    septet = frame[4]

    for j in range(4):
        if septet & (1 << j):
            data.append(frame[j] | 0x80)
        else:
            data.append(frame[j])
    return data


# Gets the numerical value of a set of bytes (respect Two's complement by value Range)
def gb(data, begin, end):  # GetBytes
    # convert begin and end to int whatever was passed to make enumerate work
    begin = int(begin)
    end = int(end)
    wbg = sum([0xff << (i * 8) for i, b in enumerate(data[begin:end])])
    s = sum([b << (i * 8) for i, b in enumerate(data[begin:end])])
    if s >= wbg/2:
        s = -1 * (wbg - s)
    return s


if __name__ == '__main__':
    if config.connection == "serial":
        sock = serial.Serial(config.port, baudrate=config.baudrate, timeout=0)
    elif config.connection == "lan":
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(config.address)
        login()
    elif config.connection == "stdin":
        sock = sys.stdin
    else:
        sys.exit('Unknown connection type. Please check config.')

    result = dict()
    load_data()

    print(json.dumps(result).replace("\\u00b0C","°C"))

    if config.connection == "lan":
        try:
            sock.shutdown(0)
        except:
            pass
    sock.close()
    sock = None
