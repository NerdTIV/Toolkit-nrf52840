
import time
import _bleio

UUID_SERVICE = _bleio.UUID("6e400001-b5a3-f393-e0a9-e50e24dcca9e")
UUID_TX = _bleio.UUID("6e400003-b5a3-f393-e0a9-e50e24dcca9e")
UUID_RX = _bleio.UUID("6e400002-b5a3-f393-e0a9-e50e24dcca9e")

NAME = "TestPeriph"

VALUE = b"hello from circuitpython" * 4

service = _bleio.Service(UUID_SERVICE)

tx = _bleio.Characteristic.add_to_service(
    service, UUID_TX,
    properties=_bleio.Characteristic.READ | _bleio.Characteristic.NOTIFY,
    read_perm=_bleio.Attribute.OPEN,
    write_perm=_bleio.Attribute.NO_ACCESS,
    max_length=len(VALUE), fixed_length=False,
    initial_value=VALUE)

rx = _bleio.Characteristic.add_to_service(
    service, UUID_RX,
    properties=_bleio.Characteristic.WRITE | _bleio.Characteristic.WRITE_NO_RESPONSE,
    read_perm=_bleio.Attribute.NO_ACCESS,
    write_perm=_bleio.Attribute.OPEN,
    max_length=244, fixed_length=False)

name_bytes = NAME.encode()
advertising = bytes([0x02, 0x01, 0x06])
advertising += bytes([len(name_bytes) + 1, 0x09]) + name_bytes

adapter = _bleio.adapter
adapter.name = NAME

print("[periph] start, %d bytes on TX, name '%s'" % (len(VALUE), NAME))

last_rx = b""

while True:
    if not adapter.advertising:
        try:
            adapter.start_advertising(advertising, connectable=True, interval=0.1)
            print("[periph] advertising restarted")
        except Exception as e:
            print("[periph] advertising error :", e)

    try:
        got = rx.value
        if got and got != last_rx:
            last_rx = got
            print("[periph] got %d bytes : %s" % (len(got), bytes(got)))
    except Exception:
        pass

    try:
        tx.value = VALUE
    except Exception:
        pass

    time.sleep(0.5)
