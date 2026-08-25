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

Press **RESET** first : the red LED pulses and the dongle shows up as
`1915:521f` in `lsusb`.

The easy way is **nRF Connect Programmer**. It takes the `.hex` directly and
builds the DFU package itself, so there is nothing to prepare. Add the file,
Write, done. One thing to know : turn **Auto read memory** off before you
select the device, otherwise it freezes the bootloader before you ever press
Write. See [TROUBLESHOOTING.md](../nrf52840-flasher/TROUBLESHOOTING.md).

To do it from the command line you have to build the package yourself, and it
has to be a **DFU v2** package. Use Nordic's `nrfutil`, not
`adafruit-nrfutil` : the Adafruit one writes legacy packages for the Adafruit
bootloader, and this dongle has the Nordic Open DFU bootloader, which cannot
parse them. It answers nothing and the flash dies on `OP_SELECT`.

```bash
nrfutil keys generate priv.pem

nrfutil pkg generate --hw-version 52 --sd-req 0x00 \
    --application build/zephyr/zephyr.hex --application-version 1 \
    --key-file priv.pem fw.zip
```

The Open DFU bootloader does not check the signature against anything, so any
key you generate works. On the newer Rust `nrfutil` the same command lives
under `nrfutil nrf5sdk-tools pkg generate ...`, after
`nrfutil install nrf5sdk-tools`.

Then flash it, with the flasher from this repo which avoids the serial DTR
problem, see [`../nrf52840-flasher/`](../nrf52840-flasher/):

```bash
sudo python3 ../nrf52840-flasher/flash_nrf52840.py fw.zip
```

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
