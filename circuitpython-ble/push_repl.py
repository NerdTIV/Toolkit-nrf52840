#!/usr/bin/env python3
# Send a file to a CircuitPython board through the serial REPL.
# Usage : python3 push_repl.py file.py [remote_name]
#
# Utile quand CIRCUITPY est monte en read-only cote PC. Au lieu de copier le
# fichier, on demande a la board de l'ecrire elle-meme.

import base64
import sys
import time
import serial

PORT = "/dev/ttyACM0"

if len(sys.argv) < 2:
    print("Usage : python3 push_repl.py <file> [remote_name]")
    sys.exit(1)

path = sys.argv[1]
remote_name = sys.argv[2] if len(sys.argv) > 2 else "code.py"

with open(path, "rb") as f:
    content = f.read()

# base64 pour faire passer du binaire en texte dans le REPL
encoded = base64.b64encode(content).decode()

s = serial.Serial(PORT, 115200, timeout=2)


def read():
    time.sleep(0.2)
    n = s.in_waiting
    if n == 0:
        n = 1
    return s.read(n)


# Ctrl-C x2 : stop le programme en cours
s.write(b"\r\x03\x03")
read()

# Ctrl-A : raw REPL, pas d'echo, plus simple a piloter
s.write(b"\r\x01")
time.sleep(0.3)
read()

# le petit programme qui recree le fichier cote board
prog = (
    "import binascii\n"
    "d = binascii.a2b_base64('%s')\n"
    "f = open('%s', 'wb')\n"
    "f.write(d)\n"
    "f.close()\n"
    "print('wrote', len(d), 'bytes')\n"
) % (encoded, remote_name)

# par petits bouts sinon le buffer de la board deborde
step = 64
for i in range(0, len(prog), step):
    s.write(prog[i:i + step].encode())
    s.flush()
    time.sleep(0.02)

# Ctrl-D : run
s.write(b"\x04")
time.sleep(1.0)
print(read().decode("utf-8", "replace"))

# Ctrl-B : retour au REPL normal
s.write(b"\r\x02")
s.close()
print("[*] push ok :", remote_name)
