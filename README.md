# HomeLab Cluster

## [Specs](docs/node-specs.md)

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

## 4. Setup Interfaces
* ubuntu 18+ uses netplan to configure network interface. Using netplan is straight forward. create a yaml describing your network interfaces and then run netplan apply
* gimli configuration: [/etc/netplan/50-cloud-init.yaml](network/netplan.yaml)

`netplan apply`


## Setup Unattended Updates
```sh
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
# Enter yes
```

## Speed up Start up
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
Also good to lower timeout on shutdown

## Setup space for ceph

```sh
zfs create tank/zblock0 -V 10tb
```

## Configure nfs default mount settings

1. Set up nfs with ceph
follow instructions here:
https://docs.ceph.com/en/latest/cephfs/fs-nfs-exports/#create-cephfs-export

1. All nodes need to be configured to use nfs 4.1
create file: `/etc/nfsmount.conf`
inside add:

```ini
[ NFSMount_Global_Options ]
Defaultvers=4.1
```

1. NFS has to be configured to convert ids to numbers
this can be done by creating a file with contents of:
```
NFSV4 {
    Allow_Numeric_Owners = true;
    Only_Numeric_Owners = true;
}
```
and then applying that file with:

https://docs.ceph.com/en/octopus/cephfs/fs-nfs-exports/#set-customized-nfs-ganesha-configuration

### Update Placement

`ceph nfs cluster update <clusterid> <placementnumber>`

so
`ceph nfs cluster update nfs-cluster "3 gimli,helium,lithium"`

## rke setup