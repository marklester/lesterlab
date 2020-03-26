# Gimli
# How to setup a router/nas appliance in ubuntu 18.04

## specs for NAS
[specs](docs/router-specs.md)

## install ubuntu server
## setup zfs
1. lsblk to find all disks
1. `zpool create <name> raidz sd<>... cache /dev/sd<> log /dev/sd<>`
### create dataset

```
zfs create tank/appdata
zfs set mountpoint=/appdata tank/appdata
```

## setup gpu
```
#install common drivers
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update
sudo apt-get install ubuntu-drivers-common
sudo ubuntu-drivers autoinstall
```
## setup interfaces
* ubuntu 18+ uses netplan to configure network interface. Using netplan is straight forward. create a yaml describing your network interfaces and then run netplan apply
* gimli configuration: [/etc/netplan/50-cloud-init.yaml](network/netplan.conf)

`netplan apply`

## setup dns and dhcp
dnsmasq can do both and the config is easy
* install dnsmasq
  * configure dhcp and dns
in /etc/dnsmasq.d/dnsmasq.conf
```
port=53

domain-needed
bogus-priv
strict-order

expand-hosts
domain=home

# DHCP configuration
dhcp-authoritative
dhcp-range=192.168.0.100,192.168.0.245,24h
dhcp-option=option:router,192.168.0.1
dhcp-option=option:dns-server,192.168.0.1
dhcp-option=option:netmask,255.255.255.0

server=9.9.9.9
server=1.1.1.1
log-facility=/var/log/dnsmasq.log   # logfile path.
log-async
log-queries # log queries.
log-dhcp
#dhcp-host=00:0C:29:A5:BD:4A,192.168.10.51
```

* turnoff systemd-resolved

* make sure it starts after network is on
`systemctl edit dnsmasq`

add:

```
After=network-online.target
Wants=network-online.target
```

`systemctl enable dnsmasq`

[Setup Firewall](docs/setup-firewall.md)

# install microk8s
`snap install micro8s --classic`
* enable dns,gpu
`microk8s.enable dns gpu`
## install local provisioning