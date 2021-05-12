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