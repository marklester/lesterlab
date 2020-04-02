# Gimli
# How to setup a router/nas appliance in ubuntu 18.04

## [Specs](docs/router-specs.md)

## 1. Install Ubuntu Server
## 2. Setup ZFS
1. lsblk to find all disks
1. `zpool create <name> raidz sd<>... cache /dev/sd<> log /dev/sd<>`
### Create Dataset

```bash
zfs create tank/appdata
zfs set mountpoint=/appdata tank/appdata
```

## 3. Setup GPU
```bash
#install common drivers
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update
sudo apt-get install ubuntu-drivers-common
sudo ubuntu-drivers autoinstall
```
### [Install Jupiter Hub](docs/notebooks.md)

## 4. Setup Interfaces
* ubuntu 18+ uses netplan to configure network interface. Using netplan is straight forward. create a yaml describing your network interfaces and then run netplan apply
* gimli configuration: [/etc/netplan/50-cloud-init.yaml](network/netplan.yaml)

`netplan apply`

## 5. setup DNS and DHCP
Dnsmasq can function both as dns and dhcp. It also works well for local dns. Configuration is also pretty straight forward
* install dnsmasq
  * configure dhcp and dns
`apt install dnsmasq`
  * configure dnsmasq: see [/etc/dnsmasq.d/dnsmasq.conf](network/dnsmasq.conf)

* turnoff systemd-resolved: `systemctl disable systemd-resolved`
* make sure it starts after network is on

    `systemctl edit dnsmasq`

    add:

    ```
    After=network-online.target
    Wants=network-online.target
    ```

* `systemctl enable dnsmasq`

[Setup Firewall](docs/setup-firewall.md)

# install microk8s
`snap install micro8s --classic`
* enable dns,gpu

    `microk8s.enable dns gpu`
* setup kubectl
    ```bash
    snap install kubectl
    microk8s.config > ~/.kube/config
    ```
    check for the following:
    ```
    kubectl get nodes
    NAME    STATUS   ROLES    AGE   VERSION
    gimli   Ready    <none>   8d    v1.18.0
    ```
* install local provisioning 
  * follow: https://github.com/rancher/local-path-provisioner

  `kubectl apply -f storage/localpath.config.yaml`