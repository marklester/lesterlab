# LesterLabs Ansible Playbooks  

These are the ansible playbooks to setup the nodes for the LesterLabs Clusters

[ ] - add docs on how to setup ansible

## Clusters

### Moonbase
moonbase is a single node cluster used for

* backups
* metrics and monitoring

#### Setup Moonbase
```
ansible-playbook moonbase.playbook.yaml --ask-vault-pass -K
```

### Main Cluster

This house everything else. rke2 cluster ceph as the main storage. 

#### Setup Main Cluster Nodes
This will
* setup nfs configs properly
* sysctl setup
* configure rke2 correctly

```
# setup rke2 for the main cluster
ansible-playbook main.playbook.yaml --ask-vault-pass -K

# create a kube config for the main cluster
ansible-playbook main-kubeconfig.playbook.yaml -K
#
```

#### NFS directory delegation workaround

The main-cluster playbook disables NFSv4 directory delegations to work around
[NFS-Ganesha issue #1385](https://github.com/nfs-ganesha/nfs-ganesha/issues/1385).
Newer Linux clients otherwise receive `Remote I/O error` when accessing media
directories. The tasks persist the module option, refresh initramfs when it
changes, and disable delegations immediately on loaded modules without remounting.
Kernels without the parameter skip the setting.

Apply just this fix to gimli, helium, and lithium, without restarting RKE2:

```sh
ansible-playbook -i inventory.yaml main.playbook.yaml --ask-vault-pass -K --tags nfs-directory-delegations
```

The earlier manual test on lithium was temporary; run this to persist the fix
across the main cluster. Revisit the workaround after deploying Ganesha with
the upstream fix.
