# zephyr-ble-peripheral

**A minimal BLE peripheral** for the nRF52840 dongle (PCA10059), built with
**Zephyr**. Same NUS service as
[`../circuitpython-ble/`](../circuitpython-ble/), but compiled.

- `prj.conf`: where the whole BLE stack is configured
- `src/main.c`: the NUS service and the advertising
- `CMakeLists.txt`: the build

The two versions complement each other:

| | CircuitPython | Zephyr |
|---|---|---|
| Iteration | very fast (`repl_run.py`, no build) | needs a rebuild |
| Control over the stack | whatever `_bleio` exposes | everything, through `prj.conf` |
| Speed | interpreted Python | native |
| Good for | prototyping, quick tests | tuning MTU, intervals, SMP |

Prototype with CircuitPython, switch to Zephyr when you need to touch the stack
parameters.

## Build

Needs a Zephyr workspace, see the
[official guide](https://docs.zephyrproject.org/latest/develop/getting_started/index.html).

```bash
export ZEPHYR_BASE=~/zephyrproject/zephyr
export ZEPHYR_TOOLCHAIN_VARIANT=cross-compile
export CROSS_COMPILE=/usr/bin/arm-none-eabi-

cd ~/zephyrproject
west build -b nrf52840dongle/nrf52840 /path/to/zephyr-ble-peripheral -p always
```

Output lands in `build/zephyr/`: `zephyr.hex`, `zephyr.bin` and `zephyr.uf2`
(the `.uf2` because `CONFIG_BUILD_OUTPUT_UF2=y` is set).

Two things that break the build:

- If `west update` did not clone the Nordic HAL, it fails with odd errors about
  missing registers. Check with `ls ~/zephyrproject/modules/hal/nordic/nrfx`.
- Depending on the Zephyr version, `BT_LE_ADV_CONN_FAST_1` may not exist yet.
  Replace it with `BT_LE_ADV_CONN` in `src/main.c`.

## Flash

The PCA10059 has no onboard debugger, so `west flash` is not an option. It goes
through the Nordic Open DFU bootloader.

Press **RESET** (the red LED pulses, the dongle shows up as `1915:521f` in
`lsusb`), then package the `.hex` and flash it:

```bash
adafruit-nrfutil dfu genpkg --dev-type 0x0052 \
    --application build/zephyr/zephyr.hex fw.zip

adafruit-nrfutil dfu serial -pkg fw.zip -p /dev/ttyACM0 -b 115200
```

Or with the flasher from this repo, which avoids the serial DTR problem, see
[`../nrf52840-flasher/`](../nrf52840-flasher/):

```bash
sudo python3 ../nrf52840-flasher/flash_nrf52840.py fw.zip
```

`--dev-type 0x0052` is the nRF52840. Without it the bootloader rejects the
package.

## Logs

`LOG_INF()` goes to the debug port, not to USB. There is no J-Link on this
dongle, so reading logs needs RTT and an external probe.

In practice you can do without: look at what the central sees (`nRF Connect`,
`bluetoothctl`, any BLE scanner), that is enough to know the peripheral is up.

## What to change

- **name**: `CONFIG_BT_DEVICE_NAME` in `prj.conf` **and** the
  `BT_DATA(BT_DATA_NAME_COMPLETE, ...)` line in `main.c`, with the right length.
  Forgetting the second one is a classic mistake.
- **served value**: `tx_val[]` in `main.c`
- **MTU**: `CONFIG_BT_L2CAP_TX_MTU`, and adjust `CONFIG_BT_BUF_ACL_RX_SIZE` with it
- **pairing**: `CONFIG_BT_SMP=y` to test a bonding scenario

## License

Apache-2.0, the Zephyr license, like any Zephyr application.
