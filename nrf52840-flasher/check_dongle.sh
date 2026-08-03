#!/usr/bin/env bash
# Tells in which mode the plugged nRF52840 dongle is.
# Il lit le VID:PID dans lsusb et dit quoi faire apres.
#
# Usage : bash check_dongle.sh

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[-]${NC} $*"; }

echo ""
echo "=== nRF52840 dongle status ==="
echo ""

LSUSB=$(lsusb 2>/dev/null)

if echo "$LSUSB" | grep -qi "1915:521f"; then
    warn "Dongle in DFU bootloader mode (1915:521f)"
    echo "    pret a etre flashe :"
    echo "    sudo python3 flash_nrf52840.py firmware.zip"

elif echo "$LSUSB" | grep -qi "1915:520f"; then
    warn "Dongle running the nRF Sniffer firmware (1915:520f)"
    echo "    appuie sur RESET pour revenir en bootloader, puis reflash"

elif echo "$LSUSB" | grep -qi "2fe3:0001"; then
    ok "Dongle in Zephyr HCI USB mode (2fe3:0001)"
    echo "    il doit apparaitre comme un adaptateur Bluetooth normal"

elif echo "$LSUSB" | grep -qi "239a:"; then
    ok "Dongle running CircuitPython (239a:xxxx)"
    echo "    accessible en serie sur /dev/ttyACM0"

else
    err "No nRF52840 dongle found in lsusb"
    echo ""
    echo "Current USB devices :"
    lsusb
    echo ""
    warn "Si le dongle est branche mais pas liste :"
    echo "    appuie sur le bouton RESET (bootloader mode)"
    echo "    dans une VM, pense au USB passthrough"
    echo "    regarde les logs : sudo dmesg | tail -20"
    exit 1
fi

# si le dongle expose un adaptateur Bluetooth, on l'affiche
echo ""
echo "=== Bluetooth adapters ==="
if command -v hciconfig >/dev/null 2>&1; then
    hciconfig
else
    warn "hciconfig not found (paquet bluez pas installe)"
fi
