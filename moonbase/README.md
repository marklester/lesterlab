# Moonbase Cluster

This is where things the get moonbase going. Moon base is the 2nd cluster to provide utilties to the main cluster

## Operating System.

This is a tough one to figure out.

I want moonbase to never go down.

* bad installs <- immutable
* bad drives <- mirrored disks
* storage should be accessible without kubernetes in case one of the first 2 happen

## Candidates

### Ubuntu
I started with ubuntu. This is a great os easy to find docs and just works.
downside not immutable and require manual intervention for updates. Additionally the lts is several years 
behind so the zfs that you can install does allow for growing a zpool
`apt get update, apt get upgrade, apt get autoremove`
because of how bullet proof it is its still in the running

## Immutable OS.

### Talos Os

Very promisiing but very precriptive about how the os looks. would have to change my strategy to make it so the os drive is only used for reads and use their concept of ephermal volumes for data and logs. with data back ups to zfs or off prem. If they support btrfs or zfs as base. This would be the winner

### Ubuntu Core
 uses snap for everything. too bespoke for my tats

### MicroOs

Promising but it rolling and if installign zfs can break things

#### Leap Micro

### Fedora IOT

This is where updates to the os happen offline and on reboot updates take affect. If an issue arises then you rollback
zfs could break
### Universal Blue UCore

This is the next candidate that looks promising
* immutable
* supports raid1 btrfs os partition
* zfs builting

Downside no install need to use butane to come up with a config

Proxmox

Has zfs mirror in the installer
has zfs 2.3 so extending a z2 raid is possible

NixOs
full os from config.

## Mirror Root Partition.

This can be accomplished with:

zfs: brittle in linux
btrfs: should be stable
md: old way to do raids
hardware  raid: don't have one

Decision went with zfs because testing on a vm showed the best workflow for recovering from a failed drive.

## Hardware.

128GB ecc ram
low wattage D1521 xeon
2 nvme drives for mirrored root partition
8 base sata controller for storage

## Storage

### Ceph vs Zfs
Another tricky one. Ceph is rock solid and has tons of flexibility. 
Downside: needs kubernetes
zfs not as supported on linux. limited to 1 node.
Decision: Going with zfs because disaster recover will be easier. I can boot up another linux distro that supports zfs
and do whats needed

# Cluster
RKE2
os agnostic lots of managmeent tooling


## Utilities

* Metrics and Monitoring
* Secrets
* Backups

### Metics and Monitoring
Going to try and use the same approach as I did in the last version of lesterlabs which is to use the 
kube-prom-stack and victoria logs for log aggregation
Need to configure a metrics collector to push the metrics to moonbase.


### Secrets
need a place to store secrets need for main cluster and moonbase.
I would like to use External Secrets Operator for this.
Candidates

#### Vault
#### OpenBao

### Backups
Decision: Using restic for backups. There is a tool called backrest. This tools allows for:
* ui to see backups
* set up schedules

## App Management 

1. install metallb
1. install traefik
1. install argocd
1. install everything else with argocd apps
