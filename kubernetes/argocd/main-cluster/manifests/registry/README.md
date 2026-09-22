# In-cluster registry

This is a single-replica [Zot](https://zotregistry.dev/) OCI registry. Image
data is persisted on the retained CephFS storage class so it survives pod
recreation and application deletion. Traefik terminates the Let's Encrypt
certificate for `registry.lester.network`; traffic between Traefik and Zot
remains inside the cluster.

The registry is anonymous. Add an `htpasswd` secret before exposing it to
untrusted networks.

Examples:

```bash
docker tag alpine:3.22 registry.lester.network/library/alpine:3.22
docker push registry.lester.network/library/alpine:3.22
docker pull registry.lester.network/library/alpine:3.22
```

For in-cluster consumers, use `registry.registry.svc.cluster.local:5000`.
