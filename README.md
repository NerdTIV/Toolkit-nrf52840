# Toolkit-nrf52840

**Three tools** to work with a **nRF52840 dongle** (PCA10059): flash it, push
CircuitPython code on it, and build a Zephyr firmware for it.

- [`nrf52840-flasher`](nrf52840-flasher/): DFU flashing over USB, without `nrfutil`
- [`circuitpython-ble`](circuitpython-ble/): push and run code over the serial REPL, plus a BLE peripheral example
- [`zephyr-ble-peripheral`](zephyr-ble-peripheral/): the same BLE peripheral, but compiled

They chain together: flash the dongle, prototype fast in CircuitPython, then
move to Zephyr when you need to tune the BLE stack (MTU, intervals, SMP).

## Install

```bash
pip install pyusb pyserial
```

## Usage

Check what the dongle is currently running, then flash it:

```bash
bash nrf52840-flasher/check_dongle.sh
sudo python3 nrf52840-flasher/flash_nrf52840.py firmware.zip
```

Each folder has its own README.

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
