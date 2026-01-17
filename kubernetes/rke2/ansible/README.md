# LesterLabs Ansible Playbooks  

These are the ansible playbooks to setup the nodes for the LesterLabs Clusters

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
ansible-playbook main.playbook.yaml --ask-vault-pass -K
```