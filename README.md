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

## 6. [Setup Firewall](docs/setup-firewall.md)

## 7. Install Microk8s
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

## Setup Unattended Updates
```sh
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
# Enter yes
```

## Setup gluster

### Install Gluster

```sh
add-apt-repository ppa:gluster/glusterfs-9
apt update
apt install glusterfs-server
```

### Create ZFS Datasets
`zfs create tank/gluster`
`mkdir /tank/gluster/brick1`

### Create Storage Pool
```
gluster peer probe <host>
```
### Create Volume
```sh
gluster volume create gv0 replica 3 lithium:/tank/gluster/brick1/ helium: tank/gluster/brick1/ gimli:/tank/gluster/brick1/ 

gluster volume start gv0
```
### Mount Volume on All Nodes
```sh
vi /etc/fstab`
#add to to end of fstab
localhost:/gv0 /mnt/gv0 glusterfs defaults,_netdev 0 0
```

### Speed up Start up
For ubuntu the system waits for every interface defined to start up which can slow things down
For every interface that isn't needed add the optional flag
example:

```yaml
network:
  ethernets:
    enp1s0f0:
      dhcp4: true
    enp1s0f1:
      dhcp4: true
      optional: true
```
