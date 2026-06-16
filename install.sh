#!/bin/bash
if [[ $EUID -ne 0 ]]; then echo "Must be run as root."; exit 1; fi
if command -v pacman &> /dev/null; then pacman -Sy --needed --noconfirm python sqlite
elif command -v dnf &> /dev/null; then dnf install -y python3 sqlite
else echo "Unsupported distro."; exit 1; fi
chmod +x way-stat *.py
ln -sf "$(pwd)/way-stat" "/usr/local/bin/way-stat"
echo "Installation complete. Run 'way-stat' to begin."
