# Example BLE peripheral for CircuitPython. A mettre en code.py sur la board.
#
# Ca expose un service NUS (Nordic UART Service), le "wireless serial port"
# du BLE. Il y a deux characteristics : TX que le central lit (ou sur laquelle
# il s'abonne en notify), et RX dans laquelle le central ecrit.
#
# Je m'en sers comme test target quand je dev un client BLE et que je veux
# controler exactement ce que le peripheral renvoie.
#
# Teste sur nRF52840 (PCA10059) avec CircuitPython 10.x.

import time
import _bleio

# les UUID standards du NUS
UUID_SERVICE = _bleio.UUID("6e400001-b5a3-f393-e0a9-e50e24dcca9e")
UUID_TX = _bleio.UUID("6e400003-b5a3-f393-e0a9-e50e24dcca9e")
UUID_RX = _bleio.UUID("6e400002-b5a3-f393-e0a9-e50e24dcca9e")

NAME = "TestPeriph"

# la value servie sur TX, a changer pour tester d'autres tailles
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

# L'advertising packet, construit a la main. Le format c'est juste une suite
# de blocs [length][type][data]. Ici 0x01 c'est les flags (0x06 = BLE only et
# discoverable) et 0x09 c'est le nom complet.
name_bytes = NAME.encode()
advertising = bytes([0x02, 0x01, 0x06])
advertising += bytes([len(name_bytes) + 1, 0x09]) + name_bytes

adapter = _bleio.adapter
adapter.name = NAME

print("[periph] start, %d bytes on TX, name '%s'" % (len(VALUE), NAME))

last_rx = b""

while True:
    # si l'advertising s'est arrete (par exemple apres une deco) on le relance
    if not adapter.advertising:
        try:
            adapter.start_advertising(advertising, connectable=True, interval=0.1)
            print("[periph] advertising restarted")
        except Exception as e:
            print("[periph] advertising error :", e)

    # est-ce que le central nous a ecrit quelque chose
    try:
        got = rx.value
        if got and got != last_rx:
            last_rx = got
            print("[periph] got %d bytes : %s" % (len(got), bytes(got)))
    except Exception:
        pass

    # reecrire TX envoie une notif aux clients abonnes
    try:
        tx.value = VALUE
    except Exception:
        pass

    time.sleep(0.5)
