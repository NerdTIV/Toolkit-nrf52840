# When the flash does not go through

Stuff I hit on a PCA10059 with the Nordic Open DFU bootloader. None of it is
written down by Nordic, and each one cost me an hour or more.

## Wrong package format

Two different things are both called a DFU package :

- Adafruit nRF52 bootloader wants a **legacy** init packet, 14 bytes. That is
  what `adafruit-nrfutil dfu genpkg` makes.
- Nordic Open DFU wants a **protobuf** init packet, around 130 bytes, signed.
  That is what `nrfutil pkg generate` makes.

The dongle ships with the Nordic one. Give it a legacy package and the flash
dies on `OP_SELECT` without saying why : the bootloader just never answers,
it cannot parse what it got.

Check a zip before flashing it :

```bash
python3 -c "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); \
print(len(z.read([n for n in z.namelist() if n.endswith('.dat')][0])),'bytes')" fw.zip
```

14 bytes means legacy, it will not work here. ~130 means protobuf.

Careful with the tooling : `adafruit-nrfutil` and `pc-nrfutil` install into the
same `nordicsemi` directory and overwrite each other. If `nrfutil version`
answers `adafruit-nrfutil`, then the `nrfutil` on your PATH cannot build
packages for this bootloader, whatever the name says.

## The bootloader freezes after a USB session closes

Once a flashing tool exits, success or not, the next bulk write times out. It
answers nothing.

Things that do NOT bring it back :

- `dev.reset()` from libusb
- writing 0 then 1 to `/sys/bus/usb/devices/*/authorized`
- unbind / bind on the `usb` driver

Only cutting the power works. Unplug, wait a few seconds, plug back in. In a
VM the host usually grabs it on replug, so reattach it to the guest.

## nRF Connect Programmer : turn Auto read memory off

`Auto read memory` is on by default and it does a DFU read every time you
select the device, before you even press Write. That read freezes the
bootloader and your Write then fails with :

```
Internal sdfu error: Slip decoder error: ReadError(Custom { kind: TimedOut })
```

Look at the line just above in the log, it says `get firmware info for tasks
failed`. That is the auto read, not your write. Turn **Auto read memory** and
**Auto reset** off, power cycle the dongle, select it, Write straight away.

## USB shows up but your app never ran

The `nrf52840dongle` board starts USB CDC ACM **at boot**, before `main()`.
That is why the upstream `hci_usb` sample sets
`CONFIG_CDC_ACM_SERIAL_INITIALIZE_AT_BOOT=n`.

So a dongle in `2fe3:xxxx` with a `/dev/ttyACM0` only proves the board booted.
It says nothing about your application. To see what really happened, keep the
port open across a power cycle :

```bash
python3 - <<'PY'
import glob, time, serial
port = None
while port is None:
    ports = glob.glob("/dev/ttyACM*")
    port = ports[0] if ports else None
    time.sleep(0.05)
s = serial.Serial(port, 115200, timeout=0.2)
s.dtr = True
end = time.time() + 15
while time.time() < end:
    chunk = s.read(512)
    if chunk:
        print(chunk.decode("utf-8", "replace"), end="", flush=True)
PY
```

Replug while it runs. A Zephyr BLE app that works prints :

```
*** Booting Zephyr OS build v4.4.0-... ***
Bluetooth initialized
Advertising successfully started
```

Open the port after the boot and you get nothing at all, which looks exactly
like dead firmware. It is not, you just missed the banner.

## The CRC never comes back on the first firmware segment

The DFU transfer goes : select the object, create it, write it in small
chunks, ask for a CRC, execute. On this bootloader the init packet object
goes through every time. The first firmware segment does not : the writes
all go out, then `CALC_CRC` is never answered and the flash stops there.

What I tried, none of it changed anything :

- two different exchange implementations, one of them getting all the way
  through the init packet object
- write intervals of 4 ms and of 20 ms
- draining the pending answers before asking for the CRC

The difference between the two objects is the number of writes. The init
packet is 134 bytes, so 7 chunks of 20. A firmware segment is 4096 bytes, so
205. Somewhere past that the bootloader stops answering, and I have not
found what makes it stop.

The dongle itself is fine : the same firmware, the same package, goes
through **nRF Connect Programmer** without a hitch and the dongle comes back
in `hci_usb`. So if you hit this wall, do not spend your evening on it like I
did, use the Programmer.

## "Advertising successfully started" and nobody sees it

That line means the host stack accepted the request. It does not mean anything
left the antenna.

Move the receiver a meter away first, two radios almost touching can saturate
the front end. If two different receivers still see nothing, suspect the radio
side. Reception working proves nothing about transmission : a dongle in
`hci_usb` can capture adverts fine with a dead transmit path.
