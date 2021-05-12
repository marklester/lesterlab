# Gimli GPU Notebooks
This guide will go through installing jupyterhub on microk8s. jhub will be configured to create notebooks that can use gpus.

* helm3, gpu, and metallb must be enabled on microk8s

```bash
cd charts/
microk8s.helm3 upgrade --install jhub jupyterhub/jupyterhub   --namespace jhub --version=0.8.2 --values jhub.values.yaml --timeout 15m
# This will take a long time the gpu image is 7GB
```

The chart is configured to use rancher local provisioning of storage and configure the base notebook image to be one that is gpu enabled.

To test if function go the jhub page, login, and create a python3 notebook
run a cell with the following:
```python
import torch
torch.cuda.is_available()
```
It should return true

Note:
sometimes the chart doesn't install correctly to remove it do:

```bash
microk8s.helm3 uninstall jhub --namespace jhub
```
for more information go to:

https://zero-to-jupyterhub.readthedocs.io/en/latest/setup-jupyterhub/setup-jupyterhub.html