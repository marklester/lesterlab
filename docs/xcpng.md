## Set up XCPNG
What is it XCP-NG

### strategy
xcp can be clustered
zfs will be used for local storage of vm disks
nfs will be used for remote storage

### import zfs
* install zfs

```
yum install zfs
modprobe zfs
```

### install nfs
* firewall
* permissions
* how to mount

#### set up nfs shares for zfs
```bash
zfs set sharenfs="rw=@192.168.0.0/24,no_subtree_check,no_root_squash" tank/appdata" tank/media
```

### create zfs reposity for vms
the sr being created has to be empty and have the write permissions
* retrieve host uuid
`xe host-list`

```bash
xe sr-create host-uuid=fd3d883d-4448-4f0e-a929-75115851edb8 name-label=gimli-zfs-vms type=file other-config:o_direct=false device-config:location=/tank/vms
```

### create iso repository

# create vm for docker
* download ubuntu iso and put it in iso folder
* use new vm feature to configure ubuntu

```
sudo apt install docker.io docker-compose
```

### mount nfs

### snapshot

### setup xoa from source via docker
