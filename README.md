# Gimli
# How to setup a router/nas appliance in ubuntu 18.04

## specs for nas
* 128GB DDR 4 ECC Ram
* ipmi
* dualg 10G nics
* 1030 low profile gpu
* 4 8TB HDD
* 2 256 SSD
* 1 512 NVME

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
* apply netplan:
```yaml
network:
  version: 2
  ethernets:
    eno1:
      dhcp4: no
    eno2:
      dhcp4: no
    eno3:
      addresses: [192.168.0.1/24]
      dhcp4: no
      nameservers:
        addresses:
          - 192.168.0.1
        search: [home]
    eno4:
      dhcp4: yes
```
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

# install firewall
* enable ip forward
in /etc/sysctl.conf uncomment

`net.ipv4.ip_forward=1`

* disable and remove ufw

`systemctl disable ufw`

`apt purge ufw`

`apt install firehol`
set firehol to start in /etc/defaults/firehol.conf

`START_FIREHOL=YES`

setup /etc/firehole/firehol.conf:
```bash
version 6
#for k8s
kcni="cni0 veth+ flannel+"
interface "${kcni}" k8s
  policy accept

interface eno3 LAN
  client all accept
  server all accept

interface eno4 WAN
  server ssh accept
  server http accept
  client all accept

router4 lan2wan inface eno3 outface eno4
  masquerade
  route all accept

router4 cni2wan inface cni0 outface eno4
  masquerade
  route all accept

router4 cni_tun inface "${kcni}" outface "${kcni}"
  masquerade
  route all accept

router4 cni2lan inface "${kcni}" outface eno3
  masquerade
  route all accept

router4 lan2cni inface eno3 outface "${kcni}"
  masquerade
  route all accept

router4 wan2lan inface eno4 outface eno3


# Accept all client traffic on any interface
#interface any world
#       client all accept
```

# install microk8s
`snap install micro8s --classic`
* enable dns,gpu
`microk8s.enable dns gpu`
## install local provisioning

