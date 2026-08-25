# Which firmware for what

The nRF52840 dongle does very different jobs depending on what is flashed on
it. Here are the firmwares I used, where to get them, and how to tell which one
is running.

**No binary is shipped in this repo**, see [why](#why-no-binaries-here).

## The table

| Firmware | Used for | VID:PID once flashed | Where to get it |
|---|---|---|---|
| **Nordic Open DFU bootloader** | receiving the other firmwares | `1915:521f` | [nRF Connect SDK](https://www.nordicsemi.com/Products/Development-software/nRF-Connect-SDK) |
| **CircuitPython** | scripting BLE in Python on the dongle | `239a:xxxx` | [circuitpython.org](https://circuitpython.org/board/nordic_nrf52840_dongle/) |
| **Zephyr `hci_usb`** | turning the dongle into a standard BT adapter (`hciN`) | `2fe3:000b` | [Zephyr sample](https://docs.zephyrproject.org/latest/samples/bluetooth/hci_usb/README.html) |
| **nRF Sniffer** | capturing BLE traffic in Wireshark | `1915:520f` | [Nordic nRF Sniffer for BLE](https://www.nordicsemi.com/Products/Development-tools/nRF-Sniffer-for-Bluetooth-LE) |
| **Your own firmware** | whatever you want | depends on the build | [`../zephyr-ble-peripheral/`](../zephyr-ble-peripheral/) |

To know which one is running: `bash check_dongle.sh`.

## How to choose

- Need a **Bluetooth adapter** seen by `bluetoothctl` or `bleak`, use `hci_usb`.
  The dongle becomes a regular `hciN`.
- Need to **prototype a peripheral quickly**, use CircuitPython. Edit, rerun, no
  build.
- Need to **tune the stack** (MTU, advertising intervals, SMP), build your own
  Zephyr firmware.
- Need to **see the packets**, use nRF Sniffer with the Wireshark plugin.

Note that `hci_usb` and your own firmware cannot coexist. One dongle, one
firmware. With two dongles you can run a peripheral on one and a central on the
other, which is handy.

## The bootloader trap

The PCA10059 has no onboard debugger. Everything goes through the DFU
bootloader, and **it must never be overwritten**. Without it, recovering the
dongle needs an SWD probe.

Application DFU packages (`--application`) do not touch the bootloader. Packages
containing a SoftDevice or a bootloader do. When unsure, check the
`manifest.json` inside the `.zip`: if the only key is `application`, it is safe.

## Check what you flash

A firmware is an opaque binary, and once flashed it owns the radio. So take it
**from its author**, and check the hash before sending it to the board:

```bash
sha256sum firmware.zip
```

Compare with what the project publishes. If the project publishes no hash, at
least download the file twice from the official source and check you get the
same one.

## Why no binaries here

1. **Git keeps everything, forever.** A `.uf2` is 1 MB. Three versions later the
   repo carries 3 MB that nobody can remove without rewriting history.
2. **Licenses do not follow.** The Nordic bootloader ships the S140 SoftDevice,
   whose license only allows binary redistribution when used with Nordic
   hardware. Rehosting it on GitHub is a grey area at best.
3. **A rehosted binary cannot be verified.** If someone downloads a firmware
   from my repo and flashes it, they trust me instead of Nordic or Adafruit.
   There is no good reason to sit in the middle there.
4. **They are already available upstream**, with the release notes and history
   that come with them.

What has value here is not the blob, it is knowing **which one to take and
why**. Hence this file.
