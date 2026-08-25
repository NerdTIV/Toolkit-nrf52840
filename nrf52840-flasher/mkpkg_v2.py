#!/usr/bin/env python3

import sys
import os
import json
import hashlib
import zipfile

try:
    from ecdsa import SigningKey, NIST256p
    from ecdsa.util import sigencode_string
except ImportError:
    print("Install ecdsa : pip install ecdsa")
    sys.exit(1)

try:
    from nordicsemi.dfu.init_packet_pb import InitPacketPB
    from nordicsemi.dfu.init_packet_pb import DFUType, HashTypes, SigningTypes
except ImportError:
    print("Install pc-nrfutil : pip install nrfutil")
    sys.exit(1)


HW_VERSION = 52
SD_REQ = [0x00]
FW_VERSION = 1


def read_firmware(path):
    if path.lower().endswith(".hex"):
        from nordicsemi.dfu.intelhex import IntelHex
        return IntelHex(path).tobinstr()
    return open(path, "rb").read()


def load_key(path):
    if os.path.exists(path):
        return SigningKey.from_pem(open(path, "rb").read())

    key = SigningKey.generate(curve=NIST256p)
    open(path, "wb").write(key.to_pem())
    print("[+] new signing key : %s" % path)
    return key


def build_init_packet(firmware, key):
    digest = hashlib.sha256(firmware).digest()[::-1]

    init = InitPacketPB(hash_bytes=digest,
                        hash_type=HashTypes.SHA256,
                        dfu_type=DFUType.APPLICATION,
                        fw_version=FW_VERSION,
                        hw_version=HW_VERSION,
                        sd_req=SD_REQ,
                        app_size=len(firmware))

    signature = key.sign(init.get_init_command_bytes(),
                         hashfunc=hashlib.sha256,
                         sigencode=sigencode_string)
    init.set_signature(signature, SigningTypes.ECDSA_P256_SHA256)
    return init.get_init_packet_pb_bytes()


def make_package(firmware_path, out_zip, key_path):
    firmware = read_firmware(firmware_path)
    if not firmware:
        print("[!] %s is empty" % firmware_path)
        sys.exit(1)

    key = load_key(key_path)
    init = build_init_packet(firmware, key)

    manifest = {"manifest": {"application": {"bin_file": "app.bin",
                                             "dat_file": "app.dat"}}}

    z = zipfile.ZipFile(out_zip, "w")
    z.writestr("manifest.json", json.dumps(manifest))
    z.writestr("app.dat", init)
    z.writestr("app.bin", firmware)
    z.close()

    print("[*] firmware    : %d bytes" % len(firmware))
    print("[*] init packet : %d bytes" % len(init))
    print("[*] sha256      : %s" % hashlib.sha256(firmware).hexdigest())
    print("[+] package     : %s" % out_zip)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python3 mkpkg_v2.py <app.hex|app.bin> [out.zip] [key.pem]")
        sys.exit(1)

    firmware_path = sys.argv[1]
    if not os.path.exists(firmware_path):
        print("File not found : %s" % firmware_path)
        sys.exit(1)

    out_zip = sys.argv[2] if len(sys.argv) > 2 else "firmware.zip"
    key_path = sys.argv[3] if len(sys.argv) > 3 else "dfu_key.pem"

    try:
        make_package(firmware_path, out_zip, key_path)
    except Exception as e:
        print("[!] Packaging failed : %s" % e)
        sys.exit(1)
