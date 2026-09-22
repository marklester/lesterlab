# In-cluster registry

This is a single-replica [Zot](https://zotregistry.dev/) OCI registry. Image
data is persisted on the retained CephFS storage class so it survives pod
recreation and application deletion.

The initial deployment is intentionally limited to the local `registry.home`
endpoint and does not configure registry authentication or TLS. Configure
containerd/Docker clients that use this endpoint as an insecure registry until
TLS and an `htpasswd` secret are added.

Examples:

```bash
docker tag alpine:3.22 registry.home/library/alpine:3.22
docker push registry.home/library/alpine:3.22
docker pull registry.home/library/alpine:3.22
```

For in-cluster consumers, use `registry.registry.svc.cluster.local:5000`.
