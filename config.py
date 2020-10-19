import os

# configure kind of connection "lan", "serial" or "stdin"
connection = "lan"
#connection = "serial"
#connection = "stdin"

# only used for "lan"
address = ("192.168.1.253", 7053)
vbus_pass = "vbus"

# only used for "serial"
port = "/dev/ttyAMA0"
baudrate = 9600

spec_file = os.path.dirname(__file__) + '/spec/DeltaSolBS2009.json'
# expected amount of different source packets (see spec_file)
expected_packets = 1

debug = False
