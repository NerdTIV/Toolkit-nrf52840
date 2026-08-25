# Toolkit-nrf52840

**Three tools** to work with a **nRF52840 dongle** (PCA10059): flash it, push
CircuitPython code on it, and build a Zephyr firmware for it.

- [`nrf52840-flasher`](nrf52840-flasher/): DFU flashing over USB, straight to the bulk endpoints
- [`circuitpython-ble`](circuitpython-ble/): push and run code over the serial REPL, plus a BLE peripheral example
- [`zephyr-ble-peripheral`](zephyr-ble-peripheral/): the same BLE peripheral, but compiled

They chain together: flash the dongle, prototype fast in CircuitPython, then
move to Zephyr when you need to tune the BLE stack (MTU, intervals, SMP).

## Install

```bash
pip install pyusb pyserial
```

## Usage

Check what the dongle is currently running:

```bash
bash nrf52840-flasher/check_dongle.sh
```

Then flash it. You need a `.zip` **DFU package**, not a `.hex`, and it has to
be a **v2** package : this dongle runs the Nordic Open DFU bootloader, which
cannot read the legacy packages `adafruit-nrfutil` writes. Build one with
Nordic's `nrfutil` :

```bash
nrfutil keys generate priv.pem
nrfutil pkg generate --hw-version 52 --sd-req 0x00 \
    --application app.hex --application-version 1 \
    --key-file priv.pem firmware.zip

sudo python3 nrf52840-flasher/flash_nrf52840.py firmware.zip
```

If you would rather not build a package at all, **nRF Connect Programmer**
takes the `.hex` directly and does it for you. Turn *Auto read memory* off
first, it freezes the bootloader before you get to press Write.

Flashing itself needs no `nrfutil`, only `pyusb`. It is the packaging step
that does.

Each folder has its own README. When something goes wrong, read
[TROUBLESHOOTING.md](nrf52840-flasher/TROUBLESHOOTING.md) before anything
else.

No firmware binary is shipped here. See
[FIRMWARES.md](nrf52840-flasher/FIRMWARES.md) for which one to use and where
to get it.

## Support

Tested on a nRF52840 dongle (PCA10059), on Kali and Debian.

## Credits

Written by [T.I.V](https://github.com/NerdTIV) while learning Bluetooth Low
Energy.

## License

MIT, see [LICENSE](LICENSE). One exception: `zephyr-ble-peripheral/` is
**Apache-2.0**, the Zephyr license, like any Zephyr application.
