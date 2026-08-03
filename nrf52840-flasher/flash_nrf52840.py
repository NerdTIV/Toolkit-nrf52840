#!/usr/bin/env python3
# Flash a nRF52840 dongle with a Nordic DFU package (.zip).
# Usage : sudo python3 flash_nrf52840.py firmware.zip
#
# J'ai commence avec pyserial et j'ai galere : quand on ferme le port, cdc_acm
# met DTR a 0 et le bootloader se fige au milieu du flash. Avec pyusb on parle
# direct aux endpoints bulk et on ne touche jamais DTR. Depuis ca marche.

import sys
import os
import time
import json
import struct
import zipfile
import binascii

try:
    import usb.core
    import usb.util
except ImportError:
    print("Install pyusb : pip install pyusb")
    sys.exit(1)


SLIP_END = 0xC0
SLIP_ESC = 0xDB
SLIP_ESC_END = 0xDC
SLIP_ESC_ESC = 0xDD

# opcodes du DFU Nordic v2
OP_CREATE = 0x01
OP_SET_PRN = 0x02
OP_CALC_CRC = 0x03
OP_EXECUTE = 0x04
OP_SELECT = 0x06
OP_WRITE = 0x08
OP_PING = 0x09
OP_RESPONSE = 0x60

OBJ_COMMAND = 0x01
OBJ_DATA = 0x02

VID = 0x1915        # le dongle quand il est en bootloader
PID = 0x521F

# taille des chunks. J'ai teste 64 et 32, ca sautait des paquets. 20 c'est lent
# mais je n'ai plus jamais eu de flash rate.
CHUNK = 20


def slip_encode(data):
    out = bytearray()
    out.append(SLIP_END)
    for b in data:
        if b == SLIP_END:
            out.append(SLIP_ESC)
            out.append(SLIP_ESC_END)
        elif b == SLIP_ESC:
            out.append(SLIP_ESC)
            out.append(SLIP_ESC_ESC)
        else:
            out.append(b)
    out.append(SLIP_END)
    return bytes(out)


def slip_decode(data):
    out = bytearray()
    i = 0
    while i < len(data):
        if data[i] == SLIP_END:
            i = i + 1
            continue
        if data[i] == SLIP_ESC:
            i = i + 1
            if i < len(data):
                if data[i] == SLIP_ESC_END:
                    out.append(SLIP_END)
                elif data[i] == SLIP_ESC_ESC:
                    out.append(SLIP_ESC)
        else:
            out.append(data[i])
        i = i + 1
    return bytes(out)


class Dongle:

    def __init__(self):
        self.dev = None
        self.ep_out = None
        self.ep_in = None
        self.buf = bytearray()   # data lue mais pas encore parsee

    def open(self):
        self.dev = usb.core.find(idVendor=VID, idProduct=PID)
        if self.dev is None:
            raise RuntimeError("DFU dongle (1915:521f) not found")

        # un reset pour repartir sur du propre, des fois il reste des trucs
        # dans les buffers d'un essai precedent
        try:
            self.dev.reset()
            time.sleep(1.5)
            self.dev = usb.core.find(idVendor=VID, idProduct=PID)
        except Exception:
            pass
        if self.dev is None:
            raise RuntimeError("dongle gone after reset")

        # faut detacher le driver kernel sinon il garde la main sur le device
        for i in (0, 1):
            try:
                if self.dev.is_kernel_driver_active(i):
                    self.dev.detach_kernel_driver(i)
            except Exception:
                pass

        self.dev.set_configuration()
        conf = self.dev.get_active_configuration()

        # en CDC-ACM l'interface 0 c'est le control et la 1 c'est la data.
        # Les endpoints bulk devraient etre sur la 1 mais j'ai vu des dongles
        # ou c'etait la 0, du coup je teste les deux.
        for num in (1, 0):
            try:
                intf = conf[(num, 0)]
            except Exception:
                continue

            ep_out = None
            ep_in = None
            for ep in intf:
                direction = usb.util.endpoint_direction(ep.bEndpointAddress)
                if direction == usb.util.ENDPOINT_OUT and ep_out is None:
                    ep_out = ep
                if direction == usb.util.ENDPOINT_IN and ep_in is None:
                    ep_in = ep

            if ep_out is not None and ep_in is not None:
                self.ep_out = ep_out
                self.ep_in = ep_in
                break

        if self.ep_out is None or self.ep_in is None:
            raise RuntimeError("bulk endpoints not found")

        # DTR a 1. Sur certains bootloaders sans ca on n'a aucune reponse.
        try:
            self.dev.ctrl_transfer(0x21, 0x22, 0x01, 0, None, timeout=1000)
        except Exception:
            pass
        time.sleep(0.5)

        self.flush()

    def flush(self):
        # Le bootloader ne vide sa queue que quand on lui envoie une commande.
        # Du coup on lui balance des PING jusqu'a ce qu'il ne reponde plus rien.
        # 15 essais c'est large, en pratique 2 ou 3 suffisent.
        count = 0
        while count < 15:
            try:
                self.ep_out.write(slip_encode(bytes([OP_PING, 0x01])), timeout=1000)
            except Exception:
                pass

            got_something = False
            end = time.time() + 0.5
            while time.time() < end:
                try:
                    if self.ep_in.read(512, timeout=100):
                        got_something = True
                except Exception:
                    pass

            if got_something == False:
                break
            count = count + 1

        self.buf = bytearray()

    def write(self, data):
        # 64 c'est le max d'un bulk transfer en full speed
        i = 0
        while i < len(data):
            self.ep_out.write(data[i:i + 64], timeout=5000)
            i = i + 64

    def read_some(self, duration=0.5):
        end = time.time() + duration
        while time.time() < end:
            try:
                chunk = self.ep_in.read(512, timeout=100)
                if chunk:
                    self.buf.extend(chunk)
            except Exception:
                pass

    def close(self):
        # surtout ne pas remettre DTR a 0 ici, c'est exactement ce qui freeze
        # le bootloader
        try:
            usb.util.dispose_resources(self.dev)
        except Exception:
            pass
        for i in (0, 1):
            try:
                self.dev.attach_kernel_driver(i)
            except Exception:
                pass


def get_frame(dongle):
    # sort une frame SLIP du buffer, None s'il n'y en a pas encore de complete
    frame = bytearray()
    i = 0
    while i < len(dongle.buf):
        b = dongle.buf[i]
        if b == SLIP_END:
            if len(frame) > 0:
                dongle.buf = dongle.buf[i:]   # on garde le 0xC0 pour la suivante
                return slip_decode(bytes(frame))
        else:
            frame.append(b)
        i = i + 1
    return None


def send(dongle, data):
    dongle.write(slip_encode(data))


def send_cmd(dongle, op, data, timeout=8.0):
    # Truc chelou du bootloader : il repond en decale. Quand on lui envoie une
    # commande, il renvoie la reponse de la commande d'avant. J'ai mis un bon
    # moment a comprendre pourquoi mes reponses etaient toujours en retard.
    # La solution : on envoie la commande, puis un PING bidon juste pour faire
    # sortir la vraie reponse.
    dongle.buf = bytearray()
    dongle.read_some(0.1)
    dongle.buf = bytearray()

    send(dongle, data)
    time.sleep(0.02)
    send(dongle, bytes([OP_PING, 0xFE]))
    time.sleep(0.05)

    end = time.time() + timeout
    while time.time() < end:
        dongle.read_some(0.3)
        frame = get_frame(dongle)
        while frame is not None:
            # une reponse fait au moins 3 bytes : 0x60, l'opcode, le result
            if len(frame) >= 3 and frame[0] == OP_RESPONSE and frame[1] == op:
                if frame[2] != 0x01:
                    raise RuntimeError("DFU error %#x on opcode %#x" % (frame[2], op))
                return frame[3:]
            frame = get_frame(dongle)

    raise TimeoutError("no response for opcode %#x" % op)


def crc32(data):
    return binascii.crc32(data) & 0xFFFFFFFF


def read_zip(path):
    # un package DFU c'est un manifest.json qui pointe vers un .dat et un .bin
    z = zipfile.ZipFile(path)
    manifest = json.loads(z.read("manifest.json"))["manifest"]

    infos = manifest.get("application", manifest)
    dat = infos.get("dat_file")
    bin_file = infos.get("bin_file")

    # si ce n'est pas une "application" (softdevice, bootloader...) on cherche
    # dans les autres cles
    if not dat or not bin_file:
        for val in manifest.values():
            if isinstance(val, dict) and val.get("dat_file"):
                dat = val["dat_file"]
                bin_file = val["bin_file"]
                break

    if not dat or not bin_file:
        z.close()
        raise ValueError("no .dat / .bin in the manifest")

    init_data = z.read(dat)
    fw_data = z.read(bin_file)
    z.close()
    return init_data, fw_data


def send_object(dongle, data, obj_type, name, already_sent=0, total=None):
    header = bytes([OP_CREATE, obj_type]) + struct.pack("<I", len(data))
    send_cmd(dongle, OP_CREATE, header)

    sent = 0
    while sent < len(data):
        part = data[sent:sent + CHUNK]
        dongle.write(slip_encode(bytes([OP_WRITE]) + part))
        time.sleep(0.005)
        sent = sent + len(part)
        if total:
            pct = int(100 * (already_sent + sent) / total)
            print("\r    %s : %d%%" % (name, pct), end="", flush=True)

    if total:
        print()

    # apres les writes le dongle ecrit en flash, il ne repond pas tout de suite.
    # TODO : 20 essais c'est au pif, ca serait mieux de calculer l'attente a
    # partir de la taille du segment.
    answer = None
    time.sleep(1.0)
    try_nb = 0
    while try_nb < 20:
        try:
            answer = send_cmd(dongle, OP_CALC_CRC, bytes([OP_CALC_CRC]), timeout=5.0)
            break
        except TimeoutError:
            print("\r    checking CRC... try %d" % (try_nb + 2), end="", flush=True)
            time.sleep(1.0)
        try_nb = try_nb + 1

    if answer is None:
        raise TimeoutError("no CRC returned")

    return struct.unpack("<II", answer[:8])


def do_flash(zip_path):
    init, firmware = read_zip(zip_path)
    print("[*] init packet : %d bytes" % len(init))
    print("[*] firmware    : %d bytes" % len(firmware))

    dongle = Dongle()
    print("[*] opening dongle...")
    dongle.open()
    print("[+] dongle open")

    # on ping d'abord pour verifier qu'il est vivant
    ok = False
    tries = 0
    while tries < 10:
        try:
            send_cmd(dongle, OP_PING, bytes([OP_PING, 0x01]), timeout=3.0)
            ok = True
            break
        except TimeoutError:
            time.sleep(0.5)
        tries = tries + 1

    if ok == False:
        raise TimeoutError("dongle does not answer the PING")
    print("[+] ping ok")

    # PRN a 0 : on ne veut pas de notif de progression, on gere nous memes
    send(dongle, bytes([OP_SET_PRN, 0x00, 0x00]))
    time.sleep(0.2)
    dongle.flush()

    # 1) l'init packet, c'est les metadata signees du firmware
    print("\n[*] sending init packet...")
    send_cmd(dongle, OP_SELECT, bytes([OP_SELECT, OBJ_COMMAND]))
    offset, crc_got = send_object(dongle, init, OBJ_COMMAND, "init")
    if crc_got != crc32(init):
        raise RuntimeError("bad init CRC (expected %#x, got %#x)"
                           % (crc32(init), crc_got))
    send_cmd(dongle, OP_EXECUTE, bytes([OP_EXECUTE]), timeout=5.0)
    print("[+] init packet ok")

    # 2) le firmware, decoupe en segments
    print("\n[*] sending firmware...")
    answer = send_cmd(dongle, OP_SELECT, bytes([OP_SELECT, OBJ_DATA]))
    max_size, start_at, crc_ignore = struct.unpack("<III", answer[:12])
    if max_size == 0:
        max_size = 4096

    start = start_at
    while start < len(firmware):
        end = min(start + max_size, len(firmware))
        segment = firmware[start:end]
        seg_nb = start // max_size + 1
        print("\n    segment %d (bytes %d to %d)" % (seg_nb, start, end))

        offset, crc_got = send_object(dongle, segment, OBJ_DATA, "firmware",
                                      already_sent=start, total=len(firmware))

        # si le CRC ne tombe pas juste on renvoie le meme segment
        if offset < end or crc_got != crc32(firmware[:end]):
            print("    bad CRC, sending the segment again")
            continue

        # EXECUTE c'est l'ecriture en flash. Des fois l'USB coupe pendant, ca
        # arrivait tout le temps dans ma VM. Ce n'est pas grave, le segment est
        # deja valide cote dongle, donc on ignore l'erreur.
        try:
            send_cmd(dongle, OP_EXECUTE, bytes([OP_EXECUTE]), timeout=10.0)
        except TimeoutError:
            pass
        except usb.core.USBError:
            pass

        print("    segment %d ok" % seg_nb)
        start = end

    dongle.close()
    print("\n[+] flash done")
    print("[*] replug the dongle and check with : lsusb")


if __name__ == "__main__":
    if os.getuid() != 0:
        print("Root needed to detach the kernel driver :")
        print("  sudo python3 flash_nrf52840.py firmware.zip")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage : sudo python3 flash_nrf52840.py <firmware.zip>")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print("File not found : %s" % path)
        sys.exit(1)

    try:
        do_flash(path)
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as e:
        print("\n[!] Flash failed : %s" % e)
        sys.exit(1)
