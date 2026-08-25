#!/usr/bin/env python3

import sys
import time
import serial

PORT = "/dev/ttyACM0"

if len(sys.argv) < 2:
    print("Usage : python3 repl_run.py <file.py>")
    sys.exit(1)

with open(sys.argv[1]) as f:
    code = f.read()

s = serial.Serial(PORT, 115200, timeout=1)


def read_all():
    n = s.in_waiting
    if n == 0:
        n = 1
    return s.read(n)


s.write(b"\r\x03\x03")
time.sleep(0.3)
read_all()

s.write(b"\x05")
time.sleep(0.3)
read_all()

data = code.replace("\n", "\r\n").encode()
for i in range(0, len(data), 48):
    s.write(data[i:i + 48])
    s.flush()
    time.sleep(0.03)

time.sleep(0.3)
s.write(b"\x04")

print("[*] program started, output en direct (Ctrl-C to quit)")
try:
    while True:
        data = read_all()
        if data:
            sys.stdout.write(data.decode("utf-8", "replace"))
            sys.stdout.flush()
        else:
            time.sleep(0.1)
except KeyboardInterrupt:
    print("\n[*] detached, le programme tourne toujours sur la board")
finally:
    s.close()
