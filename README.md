# LesterLab Homelab 

This repo contains configuraiton and docs to setup my homelab.

What do I use my homelab for:

* media management
* home-automation
* self-hosted experiments

## [Inventory](docs/inventory.md)

## Agent skills

Reusable, agent-agnostic skills for this repository live in
[`.agents/skills`](.agents/skills). The directory can be fetched on its own
with Git sparse checkout when a full working tree is not needed.

The Tunarr skill includes a small API helper for creating channels from the
Plex In Cluster libraries: `.agents/skills/tunarr/scripts/tunarr.py --help`.

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
