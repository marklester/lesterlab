# Node Setup for Ceph Notes

Jot down things needed to make ceph work well for the the home lab

## Main-cluster CephX rotation (September 2026)

The daemon and CSI rotation to generation 2 completed on September 14, 2026.
All three nodes were drained one at a time, all previous CephFS mounts were
fully removed, and every active mount was verified to use
`csi-cephfs-node.2`. The CephCluster now uses `aes256k` with
`keepPriorKeyCountMax: 0`.

The migration was validated as follows:

1. `status.cephx.csi` reported generation 2 and type `aes256k`:
   ```sh
   kubectl -n rook-ceph get cephcluster rook-ceph -o jsonpath='{.status.cephx.csi}{"\n"}'
   ```
2. A fresh CephFS PVC was provisioned, mounted, written, and read on each node.
3. Helium, gimli, and lithium were drained one at a time with temporary
   `noout`, `noscrub`, and `nodeep-scrub` flags. The cluster returned to all
   409 placement groups `active+clean` between nodes.
4. After all workloads recovered, every active CephFS mount used the
   generation-2 identity. No RBD PVs existed, and the prior CSI keys were
   removed by setting `keepPriorKeyCountMax` to `0`.

Keep AES authentication allowed until remaining NFS and other client identities
have been audited. Do not delete old-looking NFS identities without confirming
they are unused. NFS per-export keys are not automatically rotated by Rook.

Reference: https://rook.io/docs/rook/latest/Storage-Configuration/Advanced/cephx-key-rotation/



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
