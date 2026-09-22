# Restic REST server

The `rest-server` ArgoCD Application runs on Moonbase. The separate `volsync`
Application installs the controller on main. These apps provide infrastructure;
they do not create backup policies or modify existing Backrest backups.

The REST server stores repositories on a `local-path-retain` PVC and exposes them
at `http://restic.moonbase.home` through Moonbase's Traefik ingress. This is
intentionally HTTP-only for the internal network; the backend Service also uses
HTTP inside Moonbase's cluster.

## Before syncing

1. Sync the existing `local-path-provisioner` app and ensure `/tank` is mounted
   as ZFS. `local-path-retain` provisions the repository directory under
   `/tank/local-path-provisioner` on the pod's node. The server runs as UID/GID
   1000 and refuses to start if its `/data` mount is not ZFS. The claim requests
   100 GiB, but local-path does **not enforce a quota or reserve this space**;
   monitor actual ZFS free space. No custom PV or host directory setup is needed.

   Backrest's own configuration PVC uses `local-path`; its existing repositories
   use a separate `/tank/backups` hostPath. Neither is changed by this app.

2. Add a DNS record for `restic.moonbase.home` pointing to `192.168.0.251`, the
   Moonbase Traefik address.

3. The server currently runs with `--no-auth`. Anyone who can reach this HTTP
   endpoint can read, create, modify, or delete repositories. Restrict access to
   the private network and do not publish this ingress externally. Add network
   or IP controls before allowing less-trusted clients onto that network.

4. Sync the `rest-server` app after the local-path provisioner. Main only needs
   its VolSync app at this stage. The root Applications already discover both new
   app files.

For a future Jackett repository Secret in main, the required values are:

| Key | Value |
| --- | --- |
| `RESTIC_REPOSITORY` | `rest:http://restic.moonbase.home/jackett-config/` |
| `RESTIC_PASSWORD` | A separate repository encryption password |

The example repository is stored at `/data/jackett-config` inside the pod's
repository PVC. Give each source PVC its own repository. The shared repository
encryption password is retained in Moonbase's private secret store as
`restic/main-backups/password` for disaster recovery. VolSync also needs the
same value in a source-cluster Secret; it is independent of REST-server access
control.

Append-only mode is intentionally not enabled: the proposed VolSync policies own
retention and need to forget/prune. Configure ZFS snapshots with retention managed
on Moonbase, and keep those administrative credentials away from backup clients.

## Verification and operation

```bash
kubectl --context moonbase-context -n rest-server get pvc,pods
kubectl --context main-cluster -n volsync-system get deployment
```

Verify the HTTP endpoint from main. A request for a repository that has not been
initialized can return 404; the first Restic backup initializes it. Then perform
a disposable backup/restore before enabling production schedules.

The provisioned PV uses `Retain`; the PVC has ArgoCD `Prune=false,Delete=false`.
Removing the Application must not be treated as authorization to delete backups.
If recovering a retained PV after deleting its claim, explicitly rebind it to a
replacement claim after checking the old claim UID. Do not reinitialize existing
repositories.

To find the directory for host-level disaster recovery, inspect the bound PV's
`spec.hostPath.path` (or `spec.local.path`, depending on provisioner configuration).
Preserve that mapping and the repository credentials outside the cluster.
Include the provisioner directory in Moonbase's ZFS snapshot policy.

Backrest can connect to the new repositories through their REST URLs. Its existing
`/repos` mount does not expose the new PVC's files. Let only VolSync own
retention/pruning for those repositories. Do not remove Backrest's NFS source
mount until shared-directory coverage has been migrated and tested.

Upstream references: [VolSync](https://volsync.readthedocs.io/en/stable/usage/restic/index.html),
[REST server](https://github.com/restic/rest-server).
