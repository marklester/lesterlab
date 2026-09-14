# Node Setup for Ceph Notes

Jot down things needed to make ceph work well for the the home lab

## Main-cluster CephX rotation (September 2026)

The CephCluster manifest keeps daemon and CSI rotation at generation 2.
CSI uses `aes256k` with `keepPriorKeyCountMax: 1`, so existing mounts can
continue using their previous credentials while new mounts adopt the new keys.
This requires Ceph-CSI 3.17.1+ and Linux 7.0+ (7.2+ if FIPS is enabled).

After ArgoCD syncs the manifest:

1. Check that `status.cephx.csi` reports generation 2, type `aes256k`, and
   one prior key generation retained:
   ```sh
   kubectl -n rook-ceph get cephcluster rook-ceph -o jsonpath='{.status.cephx.csi}{"\n"}'
   ```
2. Verify a fresh CephFS PVC can be provisioned, mounted, written, and read
   on each node.
3. Investigate the existing BlueStore slow-operation warnings before node
   maintenance. Migrate existing mounts one node at a time, waiting for Ceph
   and workloads to recover between nodes. All old CSI mounts must be fully
   unmounted/remounted; restarting CSI pods alone does not accomplish this.
4. Only after all existing mounts have migrated, change
   `keepPriorKeyCountMax` to `0` in the manifest and sync it.

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
