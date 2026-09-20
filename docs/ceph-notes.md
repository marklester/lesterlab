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

On September 16, the remaining NFS identities were audited against monitor
sessions and the live `.nfs` RADOS configuration. Six unused identities from
the previous `nfs-ganesha` deployment were backed up and removed. The only
remaining `AUTH_INSECURE_CLIENT_KEY_TYPE` identity is the active export key:

```text
client.nfs.nfs-cluster.1
```

Keep `aes` authentication allowed while this export exists. Do not remove this
identity or configure `auth_allowed_ciphers` to allow only `aes256k`.

Rook does not automatically rotate NFS per-export keys. An in-place migration
was tested by reapplying export 1 without its generated `user_id`. Ceph created
`client.nfs.nfs-cluster.cephfs.2ad1871a` with an `aes256k` key and capabilities
identical to the working identity, but NFS-Ganesha 5.9 from the Ceph 20.2.4
image could not mount CephFS with it and logged `Operation not permitted`. The
export was restored from backup, NFS-Ganesha was restarted, and Plex access was
verified. The failed replacement identity was removed.

The remaining warning must stay until upstream supports rotating this export
key or a later Ceph/NFS-Ganesha version is verified to accept the replacement.

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
NFS stores its current configuration in the `.nfs` RADOS pool. The old
`nfs-ganesha` pool contains legacy objects and is not the source for the live
export.

`rados -p .nfs ls --all`
`rados -p .nfs get -n nfs-cluster <objectname> <filetooutputto> --all`

### Update Placement

`ceph nfs cluster update <clusterid> <placementnumber>`

so
`ceph nfs cluster update nfs-cluster "3 gimli,helium,lithium"`


https://www.cloudraft.io/blog/rook-ceph-performance-tuning
