# Node Setup for Ceph Notes

Jot down things needed to make ceph work well for the the home lab



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
`vi nfs.config`
```
NFSV4 {
    Allow_Numeric_Owners = true;
    Only_Numeric_Owners = true;
}
```

and then applying that file with:

https://docs.ceph.com/en/octopus/cephfs/fs-nfs-exports/#set-customized-nfs-ganesha-configuration

`ceph nfs cluster config set nfs-cluster -i nfs.config`

### Create Export
`ceph nfs export create cephfs cephfs nfs-cluster /cephfs`

## Debugging Configuration
nfs puts config in rados in it's own pull here are some common commands

`rados -p nfs-ganesha ls --all`
`rados -p nfs-ganesha get -n nfs-cluster <objectname> <filetooutputto> --all`

### Update Placement

`ceph nfs cluster update <clusterid> <placementnumber>`

so
`ceph nfs cluster update nfs-cluster "3 gimli,helium,lithium"`


https://www.cloudraft.io/blog/rook-ceph-performance-tuning
