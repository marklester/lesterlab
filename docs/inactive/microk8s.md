## 7. Install Microk8s
`snap install micro8s --classic`
* enable dns,gpu

    `microk8s.enable dns gpu`
* setup kubectl
    ```bash
    snap install kubectl
    microk8s.config > ~/.kube/config
    ```
    check for the following:
    ```
    kubectl get nodes
    NAME    STATUS   ROLES    AGE   VERSION
    gimli   Ready    <none>   8d    v1.18.0
    ```
* install local provisioning 
  * follow: https://github.com/rancher/local-path-provisioner

  `kubectl apply -f storage/localpath.config.yaml`