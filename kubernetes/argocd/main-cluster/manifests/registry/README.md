# In-cluster registry

This is a single-replica [Zot](https://zotregistry.dev/) OCI registry. Image
data is persisted on the retained CephFS storage class so it survives pod
recreation and application deletion. It is available only on the internal
`registry.home` endpoint.

The registry is anonymous and uses plaintext HTTP. Configure Docker or RKE2
clients that use this endpoint as an insecure registry. Add an `htpasswd`
secret before exposing it to untrusted networks.

Examples:

```bash
docker tag alpine:3.22 registry.home/library/alpine:3.22
docker push registry.home/library/alpine:3.22
docker pull registry.home/library/alpine:3.22
```

For in-cluster consumers, use `registry.registry.svc.cluster.local:5000`.
