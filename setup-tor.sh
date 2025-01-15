#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "[!] Please run as root."
  exit 1
fi

echo "[*] Updating package list..."
apt update -y

echo "[*] Installing Tor..."
apt install -y tor obfs4proxy

TORRC_FILE="/etc/tor/torrc"
BACKUP_FILE="/etc/tor/torrc.bak"

echo "[*] Configuring $TORRC_FILE..."

if [[ ! -f "$BACKUP_FILE" ]]; then
    sudo cp "$TORRC_FILE" "$BACKUP_FILE"
    echo "[+] Backup created at $BACKUP_FILE"
else
    echo "[!] Backup already exists at $BACKUP_FILE"
fi

SETTINGS=(
    "RunAsDaemon 1"
    "SocksPort 9050"
    "Log notice file /var/log/tor/debug.log"
    "ControlPort 9051"
)

for setting in "${SETTINGS[@]}"; do
    key=$(echo "$setting" | cut -d' ' -f1)
    
    if [[ "$key" == "Log" && "$setting" == "Log notice file "* ]]; then
        if grep -qE "^#?\s*Log notice file " "$TORRC_FILE"; then
            sudo sed -i "s|^#\?\s*Log notice file .*|$setting|" "$TORRC_FILE"
            echo "[+] Updated: Log notice file"
        else
            echo "$setting" | sudo tee -a "$TORRC_FILE" > /dev/null
            echo "[+] Added new setting: Log notice file"
        fi
        continue
    fi

    if [[ "$key" == "SocksPort" ]]; then
        if grep -qE "^#\s*SocksPort\s+9050\s*.*" "$TORRC_FILE"; then
            sudo sed -i 's/^#\s*\(SocksPort\s\+9050.*\)/\1/' "$TORRC_FILE"
            echo "[+] Un-commented first SocksPort 9050 line"
        elif grep -qE "^SocksPort\s+9050\s*.*" "$TORRC_FILE"; then
            echo "[+] SocksPort 9050 is already active (no comment)"
        else
            echo "$setting" | sudo tee -a "$TORRC_FILE" > /dev/null
            echo "[+] Added new setting: SocksPort"
        fi
        continue
    fi

    if grep -qE "^#?\s*$key" "$TORRC_FILE"; then
        sudo sed -i "s|^#\?\s*$key.*|$setting|" "$TORRC_FILE"
        echo "[+] Updated: $key"
    else
        echo "$setting" | sudo tee -a "$TORRC_FILE" > /dev/null
        echo "[+] Added new setting: $key"
    fi
done

echo "[*] Restarting Tor service..."
sudo systemctl restart tor
sudo systemctl enable tor

echo "[*] Testing Tor connection..."
curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org || echo "[!] Tor test failed. Check Tor configuration."

echo "[*] Tor configuration complete. It is recommended to reboot the system now."