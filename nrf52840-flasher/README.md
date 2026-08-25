# nrf52840-flasher

**Flash a nRF52840 dongle** with a Nordic DFU package (`.zip`), talking
directly to the bootloader over USB.

- No `nrfutil` needed
- Avoids the `cdc_acm` DTR freeze that kills a flash halfway through
- `check_dongle.sh` tells you which mode the dongle is in

## Why not nrfutil to send it

Use `nrfutil` to *build* the package, see below. It is the *sending* it does
that is the problem : it goes through a serial port (`/dev/ttyACM0`). When that
port closes, the kernel `cdc_acm` driver drops **DTR to 0**, and the DFU
bootloader freezes. The flash stops halfway and you start over. It is worse in
a VM, where USB drops on its own during flash writes.

This script uses `pyusb` instead: detach the kernel driver, write straight to
the bulk endpoints, never touch DTR.

## Install

```bash
pip install pyusb
```

## Usage

```bash
bash check_dongle.sh
sudo python3 flash_nrf52840.py firmware.zip
```

Root is required to detach the kernel driver. To put the dongle in bootloader
mode, press **RESET**: the LED starts pulsing red.

## Building the .zip

This bootloader wants a **DFU v2** package, protobuf init packet, signed.
Build it with Nordic's `nrfutil` :

```bash
nrfutil keys generate priv.pem

nrfutil pkg generate --hw-version 52 --sd-req 0x00 \
    --application app.hex --application-version 1 \
    --key-file priv.pem firmware.zip
```

Any key works, the Open DFU bootloader does not check the signature against
anything. On the newer Rust `nrfutil` it is
`nrfutil nrf5sdk-tools pkg generate ...` after
`nrfutil install nrf5sdk-tools`.

**Do not use `adafruit-nrfutil dfu genpkg`.** It writes legacy packages for
the Adafruit bootloader. This one cannot parse them, answers nothing, and the
flash dies on `OP_SELECT` with no error worth reading. See
[TROUBLESHOOTING.md](TROUBLESHOOTING.md) for how to tell the two apart.

## How it works

Nordic DFU protocol, version 2:

1. Packets are **SLIP** encoded (`0xC0` delimits frames).
2. A **PING** checks that the bootloader answers.
3. The **init packet** (signed firmware metadata) goes first, then the
   **firmware** itself, split into segments.
4. Each object goes through `CREATE`, many `WRITE`, `CALC_CRC`, then `EXECUTE`.
   The CRC check confirms everything arrived before validating.

One catch that took a while to find: the bootloader answers with a **one
command delay**. Sending a command returns the response of the *previous* one.
So every command is followed by a dummy PING, just to flush the real answer out.

Three more things that are easy to get wrong:

- The bulk endpoints are on interface 1 on most dongles, but I have seen 0.
  The script tries both.
- DTR has to be set to 1 first. Some bootloaders answer nothing without it.
- Never put DTR back to 0 when closing. That is exactly what freezes the
  bootloader, and it is why closing a serial port kills a flash.

## Limitations

Only tested against the Nordic Open DFU bootloader on a PCA10059. Data is sent
20 bytes at a time, which is slow but reliable. Larger chunks dropped packets
here.

## Files

- `flash_nrf52840.py`: the flasher
- `check_dongle.sh`: shows the dongle state (bootloader, sniffer, HCI, CircuitPython)

## When it does not work

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md): package formats the bootloader
refuses, the wedge that only a power cycle clears, and why a dongle can
enumerate on USB while its application never ran.

## Firmwares

Not shipped in this repo, see [FIRMWARES.md](FIRMWARES.md).
