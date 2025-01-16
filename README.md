# tor-iptables
> *This script anonymizes network traffic by routing all services and DNS through the Tor network using iptables.*

## Installation

```sh
$ cd ~
$ git clone https://github.com/hazedic/tor-iptables.git
$ cd tor-iptables
$ chmod +x setup-tor.sh
$ sudo ./setup-tor.sh
$ sudo python tor-iptables.py -s
```

**Note:** This script has been tested on Kali Linux 2024.3.