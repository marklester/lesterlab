## Speed up Start up
For ubuntu the system waits for every interface defined to start up which can slow things down
For every interface that isn't needed add the optional flag
example:

```yaml
network:
  ethernets:
    enp1s0f0:
      dhcp4: true
    enp1s0f1:
      dhcp4: true
      optional: true
```
Also good to lower timeout on shutdown