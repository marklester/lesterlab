## Setup ZFS
1. `lsblk` to find all disks
1. `zpool create <name> raidz sd<>... cache /dev/sd<> log /dev/sd<>`

### Create Dataset
```bash
zfs create tank/appdata
zfs set mountpoint=/appdata tank/appdata
```