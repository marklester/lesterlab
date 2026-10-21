# Scheduled node OS maintenance

The repo configures system-upgrade-controller (SUC) to update installed OS
packages weekly. It does not change Ubuntu/Debian release repositories or run a
major distribution upgrade.

| Cluster | Nodes | Window (America/New_York) | Advance email |
| --- | --- | --- | --- |
| Main | gimli, helium, lithium; Ubuntu 24.04 | Sunday 03:00–06:00 | About Sunday 02:30 |
| Moonbase | moonbase; Debian 13 / Proxmox VE | Saturday 03:00–06:00 | About Saturday 02:30 |

Kubernetes CronJob time zones and SUC window time zones follow daylight saving
time. The window controls when SUC creates Jobs; a Job already started may run
past 06:00. Deploy these resources outside the maintenance window so the first
run has its full advance-notification period.

## How it works

Each cluster has an `os-maintenance` CronJob which advances its OS Plan's
`spec.version` to a weekly date identifier at 02:45, before the 03:00 start
window. The explicit image tags
are separate from that identifier. SUC runs a Plan only once per version/hash;
the CronJob is necessary for recurring package updates. The ArgoCD Application
ignores only this runtime version and uses `RespectIgnoreDifferences=true` so
sync does not revert it. Schedules, node selectors, scripts, and all other
configuration remain repo-managed.

Main uses a concurrency of one, checks node readiness and pressure, and checks
fresh Ceph health for two stable minutes before each drain. Existing insecure
auth-key warnings are allowed; all other Ceph warnings, including slow OSD
operations, block maintenance. It also waits for existing RKE2 upgrade Plans
to finish. The RKE2 Plan likewise checks for applying OS Jobs before it starts;
its channel and schedule are unchanged. If both Plans start simultaneously,
their preparation checks can wait on each other and eventually time out. This
fails safely instead of disrupting two etcd members; inspect both Plans and
retry a cycle once the other Plan has completed or been paused.

The main Plan drains workloads using the eviction API, respecting any PDBs;
it allows deletion of disposable `emptyDir` data. A failed drain stops the
upgrade. Moonbase is a single-node cluster, so its Plan cordons without
evicting workloads that have nowhere to move. Its script requires healthy ZFS
pools before updating packages. There were no Proxmox guests listed when this
configuration was prepared; any guests added later are stopped/restarted by
the host's existing Proxmox boot/shutdown configuration.

The script runs in the host namespaces. It keeps existing config files, waits
for apt locks, and refuses package removals. Ubuntu uses `apt-get upgrade
--with-new-pkgs`; Proxmox uses `apt-get dist-upgrade --no-remove`, matching the
[Proxmox update procedure](https://pve.proxmox.com/pve-docs/pve-admin-guide.html#system_software_updates)
while requiring review for dependency transitions that remove packages.

After installing packages, the script reboots the node to activate updated
services and kernels. If there are no updates and no reboot request, it skips
the reboot. A boot-ID checkpoint under `/var/lib/lesterlab-os-maintenance`
keeps the Job active until reboot and lets the replacement Pod acknowledge
the new boot without repeating updates. SUC then uncordons the node and waits
five minutes before selecting the next node. The next node's health check
also waits for Ceph recovery. Jobs have a two-hour deadline.

## Alerts

Grafana on Moonbase uses the existing `email` contact point. New provisioned
rules notify about the next maintenance window approximately 30 minutes ahead,
failed scheduler/upgrade Jobs, cycles incomplete for three hours, and missing
schedule metrics. The next schedule metric comes from kube-state-metrics and
respects the CronJob's time zone. The main cluster sends it through OTel's
existing remote-write path. The Plan completion metric persists after SUC
deletes its short-lived Jobs.

Moonbase's reboot temporarily stops Grafana, Prometheus, backups and the
Kubernetes API. Advance email is sent while those services are up; on-host
monitoring cannot send alerts while Moonbase is offline.

## Rollout and inspection

Commit/push the manifests and let ArgoCD sync the controller, plans,
kube-state-metrics, kube-prometheus-stack and grafana-alerting Applications.
Moonbase's new controller app has an earlier sync wave than its Plan app.
No Helm release upgrades are needed. Validate Grafana has loaded the
`os-maintenance` rule group and both upcoming-notice rules are healthy before
the first window.

```sh
kubectl --context main-cluster -n system-upgrade-controller get plans,cronjobs,jobs
kubectl --context moonbase-context -n system-upgrade-controller get plans,cronjobs,jobs
```

To pause future maintenance, set the CronJob's `spec.suspend: true` and Plan's
`spec.concurrency: 0` in the relevant cluster manifests. Suspending only the
CronJob does not stop an already armed Plan. Neither setting cancels a Job
already applying updates. The advance-notice rule respects CronJob suspension.

To retry a stopped cycle after investigating it, advance `spec.version` to a
new identifier. Check pending reboot checkpoints before doing so; the script
refuses to overwrite a reboot that has not been acknowledged.

## Validation

```sh
uv run --with pytest --with pyyaml pytest -q kubernetes/tests/test_os_maintenance.py
```

Tests run health checks and isolated reboot-checkpoint paths. They never run
apt, reboot a host, or change the cluster. Kubernetes server-side dry-run and
Helm rendering additionally validate resource schemas and monitoring values.
