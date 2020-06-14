* setup bridge networking
* setup gpu passthrough
```
virt-install --name ubuntu-master --features kvm_hidden=on --memory 16384 --vcpus 4 --disk /tank/vms/ubuntu-ff.qcow2,size=10 --cdrom /media/media/images/ubuntu-20.04-live-server-amd64.iso --os-variant ubuntu20.04 --graphics vnc,listen=0.0.0.0 --noautoconsole --network=br0
```
