# Gimli
# How to setup a router/nas appliance in ubuntu 18.04

## specs for NAS
[specs](docs/router-specs.md)

## install ubuntu server
## setup zfs
1. lsblk to find all disks
1. `zpool create <name> raidz sd<>... cache /dev/sd<> log /dev/sd<>`
### create dataset

```bash
zfs create tank/appdata
zfs set mountpoint=/appdata tank/appdata
```

## setup gpu
```bash
#install common drivers
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update
sudo apt-get install ubuntu-drivers-common
sudo ubuntu-drivers autoinstall
```
## setup interfaces
* ubuntu 18+ uses netplan to configure network interface. Using netplan is straight forward. create a yaml describing your network interfaces and then run netplan apply
* gimli configuration: [/etc/netplan/50-cloud-init.yaml](network/netplan.yaml)

`netplan apply`

## setup dns and dhcp
Dnsmasq can function both as dns and dhcp. It also works well for local dns. Configuration is also pretty straight forward
* install dnsmasq
  * configure dhcp and dns
`apt install dnsmasq`
in [/etc/dnsmasq.d/dnsmasq.conf](network/dnsmasq.conf)

* turnoff systemd-resolved
`systemctl disable systemd-resolved`
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