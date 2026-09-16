# Samba

This application exposes the existing CephFS directories directly over SMB:

| Windows share | CephFS directory |
| --- | --- |
| `backups` | `/backups` |
| `home-share` | `/home` |
| `media` | `/media` |

The Samba pod mounts CephFS through a static Ceph CSI volume. NFS and Ceph's
SMB manager are not in the data path.

Samba's local state, including its server identity and account database, is
stored on the 1 GiB `samba-state` PVC. The claim uses the dynamically
provisioned `rook-cephfs` StorageClass. Runtime sockets and PID files under
`/run/samba` remain ephemeral.

## Windows 11

The server requires authentication, SMB 2.1 or newer, and SMB signing. The
`family` account password comes from the `family-user-password` key in the
`main-secret-store` ClusterSecretStore, which is managed by the private
`moonbase-secrets` repo.

Retrieve the username and password:

```bash
kubectl -n samba get secret samba-credentials -o jsonpath='{.data.username}' | base64 -d; echo
kubectl -n samba get secret samba-credentials -o jsonpath='{.data.password}' | base64 -d; echo
```

Map a share from a Windows command prompt. The `*` makes Windows prompt for the
password rather than saving it in command history:

```bat
net use M: \\192.168.0.217\media /user:family *
net use M: \\samba.home\media /user:family *
```
