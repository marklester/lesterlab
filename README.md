# LesterLab Homelab 

This repo contains configuraiton and docs to setup my homelab.

What do I use my homelab for:

* media management
* home-automation
* self-hosted experiments

## [Specs](docs/node-specs.md)

## LesterLab History

### v1: truenas
pros;
*easy to get started
zfs is nice
*cons:
* can't scale maxed out by whas on the node
* no resilency. If its down its down.
### v2: ubuntu+rke
Pros: 
* easy to scale
Cons:
  * incomplete backup
  * no longer supported
### v3: ubuntu+rke2

node setup: ansible
kube node management: rke2

New: Have a Single Node Management Cluster
* use flatcar with butane for setup
* This will h

