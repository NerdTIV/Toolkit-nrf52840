# circuitpython-ble

**Push and run code** on a CircuitPython board over the **serial REPL**, plus a
BLE peripheral example.

- `push_repl.py`: write a file to the board without using the USB drive
- `repl_run.py`: run a program in RAM, output streamed live
- `ble_peripheral.py`: a NUS (Nordic UART Service) peripheral example

## Why the REPL

Normally you put code on a CircuitPython board by copying a file to the
`CIRCUITPY` drive. Two problems with that:

- the board sometimes mounts read-only on the PC side, which happens as soon as
  the running program asked for write access;
- copying a file on every iteration is slow when debugging.

Both scripts go through the serial REPL instead.

## Install

```bash
pip install pyserial
```

## Usage

Send a file to the board:

```bash
python3 push_repl.py ble_peripheral.py code.py
```

The file is base64 encoded, pushed into the REPL, and the **board** writes it
itself. That works around the read-only mount.

Run a program without installing it:

```bash
python3 repl_run.py ble_peripheral.py
```

The code is pasted into the REPL and runs **in RAM**. Nothing is written to the
board, and the program output shows live in the terminal.

## The BLE example

`ble_peripheral.py` exposes a **NUS** (Nordic UART Service), the standard
"wireless serial port" of BLE:

- **TX**: the central reads it, or subscribes to notifications
- **RX**: the central writes into it

It is useful as a test target when developing a BLE client and you want full
control over what the peripheral returns (value size, advertised name).

The advertising packet is built by hand, it is just a list of
`[length][type][data]` blocks:

```python
advertising = bytes([0x02, 0x01, 0x06])                          # flags: BLE only
advertising += bytes([len(name_bytes) + 1, 0x09]) + name_bytes   # full name
```

## Limitations

Paste mode has no flow control. Sending everything at once loses the end of the
file, so the scripts send 48 byte chunks with a short pause between them.

The serial port is hardcoded to `/dev/ttyACM0` at the top of both scripts.

## Support

Tested on a nRF52840 (PCA10059) with CircuitPython 10.x.
