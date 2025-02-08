#!/usr/bin/env python3

import os
import sys
import subprocess
from argparse import ArgumentParser

class TorIptablesManager:
    def __init__(self):
        self.tor_uid = self.get_tor_uid()
        self.tor_trans_port = "9040"
        self.tor_dns_port = "5353"
        self.excluded_networks = ["192.168.0.0/16", "172.16.0.0/12", "10.0.0.0/8", "127.0.0.0/8"]

    @staticmethod
    def run_command(command):
        try:
            subprocess.run(command, check=True)
            print(f"[+] Command succeeded: {' '.join(command)}")
        except subprocess.CalledProcessError as e:
            sys.exit(f"[!] Command failed: {' '.join(e.cmd)}\nError: {e}")

    @staticmethod
    def get_tor_uid():
        try:
            return subprocess.getoutput("id -ur debian-tor").strip()
        except Exception as e:
            sys.exit(f"[!] Failed to get Tor UID: {e}")

    def flush_iptables(self):
        print("[*] Flushing iptables rules...")
        self.run_command(["iptables", "-F"])
        self.run_command(["iptables", "-t", "nat", "-F"])
        print("[+] iptables rules flushed.")

    def setup_iptables(self):
        print("[*] Setting up iptables rules...")
        self.flush_iptables()

        # Allow Tor process to communicate
        self.run_command(["iptables", "-t", "nat", "-A", "OUTPUT", "-m", "owner", "--uid-owner", self.tor_uid, "-j", "RETURN"])
        self.run_command(["iptables", "-A", "OUTPUT", "-m", "owner", "--uid-owner", self.tor_uid, "-j", "ACCEPT"])

        # Allow DNS and already established connections
        self.run_command(["iptables", "-A", "OUTPUT", "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT"])

        # Exclude local networks
        for network in self.excluded_networks:
            self.run_command(["iptables", "-t", "nat", "-A", "OUTPUT", "-d", network, "-j", "RETURN"])
            self.run_command(["iptables", "-A", "OUTPUT", "-d", network, "-j", "ACCEPT"])

        # Redirect DNS traffic to Tor
        self.run_command(["iptables", "-t", "nat", "-A", "OUTPUT", "-p", "udp", "--dport", "53", "-j", "REDIRECT", "--to-ports", self.tor_dns_port])

        # Redirect TCP traffic to Tor
        self.run_command(["iptables", "-t", "nat", "-A", "OUTPUT", "-p", "tcp", "-j", "REDIRECT", "--to-ports", self.tor_trans_port])

        # Reject all other traffic
        self.run_command(["iptables", "-A", "OUTPUT", "-j", "REJECT"])
        print("[+] iptables rules set up.")

    def restart_tor(self):
        print("[*] Restarting Tor service...")
        self.run_command(["service", "tor", "restart"])
        print("[+] Tor service restarted.")

    def update_torrc(self):
        torrc_path = "/etc/tor/torrc"
        backup_path = torrc_path + ".bak"

        if os.path.exists(torrc_path):
            os.rename(torrc_path, backup_path)
            print(f"[+] Backed up original torrc file to {backup_path}")

        existing_content = ""
        if os.path.exists(backup_path):
            with open(backup_path, "r") as backup_file:
                existing_content = backup_file.read()

        new_settings = (
            f"\n# Custom settings added for transparent proxying\n"
            f"DNSPort {self.tor_dns_port}\n"
            f"TransPort {self.tor_trans_port}\n"
            "AutomapHostsOnResolve 1\n"
            "VirtualAddrNetworkIPv4 10.192.0.0/10\n"
        )

        if "DNSPort" in existing_content or "TransPort" in existing_content:
            print("[*] Existing torrc already contains necessary settings. Skipping duplicate entries.")
            with open(torrc_path, "w") as torrc_file:
                torrc_file.write(existing_content)
        else:
            with open(torrc_path, "w") as torrc_file:
                torrc_file.write(existing_content + new_settings)
            print(f"[+] Appended new settings to torrc file at {torrc_path}")

def check_root():
    if os.geteuid() != 0:
        sys.exit("[!] This script must be run as root. Use sudo.")

if __name__ == '__main__':
    check_root()

    parser = ArgumentParser(description="Manage Tor-based transparent proxying with iptables")
    parser.add_argument('-s', '--setup', action='store_true', help="Set up iptables rules for Tor")
    parser.add_argument('-f', '--flush', action='store_true', help="Flush iptables rules")
    args = parser.parse_args()

    tor_manager = TorIptablesManager()

    if args.setup:
        tor_manager.update_torrc()
        tor_manager.restart_tor()
        tor_manager.setup_iptables()
    elif args.flush:
        tor_manager.flush_iptables()
    else:
        parser.print_help()
