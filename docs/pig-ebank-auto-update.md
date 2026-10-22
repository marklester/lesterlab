# pig-ebank image updates

Argo CD Image Updater replaces the custom registry-polling CronJob. The
`argocd-image-updater` Application installs the pinned upstream Helm chart,
its CRD, and the configuration in `manifests/argocd-image-updater`.

The `pig-ebank` ImageUpdater resource watches only
`ghcr.io/marklester/pig-ebank:main` using the `digest` strategy, at a five-minute
interval. Registry access reuses the existing pull Secret in the `pig-ebank`
namespace through a Role granting access to that single Secret. The controller
otherwise uses namespace-scoped permissions in `argocd`.

## Git write-back configuration

The configuration writes the digest into pig-ebank's
`kustomization.yaml` and commits it to `master`. ArgoCD tracks that branch and
rolls out the resulting immutable image reference. All five existing pig-ebank
resources are listed in the Kustomization. There are no runtime image overrides
or ignored Deployment fields; Git contains the selected image digest.

Image Updater fetches the branch before making its commit. A concurrent remote
commit can cause the push to be rejected; it must retry against the updated
branch. It does not need to rewrite the branch history. Changes to other
application settings remain in Git. To hold a rollback digest, disable the
image's automatic updates first, or a subsequent check may advance it to the
latest digest behind `main` again.

Git write-back uses a dedicated SSH deploy key with write access to
`marklester/lesterlab` and permission to push to `master`. The ExternalSecret
maps `github/lesterlab/image-updater-ssh-private-key` (version `v1`) from the
existing `main-secret-store` to the controller's `sshPrivateKey` Secret.
Provision that secret-store entry and register the matching public key as a
write-enabled deploy key on `lesterlab` before activating the updater. This
credential has not been provisioned yet. The existing ArgoCD SSH credential
is for `moonbase-secrets` and is not reused. Keep the private key in the
existing private secret-store configuration, never in this repository.

After provisioning the credential, merge the branch
and let ArgoCD sync. The controller's CRD is installed before the ImageUpdater
resource (sync wave 1). No Helm CLI release installation is needed.

```sh
kubectl --context main-cluster -n argocd get imageupdater pig-ebank -o yaml
kubectl --context main-cluster -n argocd logs deployment/argocd-image-updater-controller
kubectl --context main-cluster -n pig-ebank rollout status deployment/pig-ebank
```

See the upstream [digest strategy and registry credentials](https://argocd-image-updater.readthedocs.io/en/stable/configuration/images/)
and [Git write-back](https://argocd-image-updater.readthedocs.io/en/stable/basics/update-methods/)
documentation.
