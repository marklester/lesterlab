# pig-ebank image updates

The `pig-ebank-image-update` CronJob checks the private GHCR `main` tag every
five minutes using the existing `pig-ebank-ghcr-credentials` Secret. It compares
the registry manifest digest (including multi-platform indexes) with the last
observed digest on the Deployment's Pod template. A changed digest updates the
`pig-ebank.home/image-digest` annotation, which triggers a rollout. The existing
`imagePullPolicy: Always` makes each new Pod resolve and pull `main` again.

The first successful check also triggers a rollout to establish the marker.
Unchanged digests do nothing. Registry/authentication failures fail the Job
without changing the Deployment. Concurrent changes to the Deployment cause
the patch to fail and be retried by a later run. Job logs contain digests, never
credentials. The service account can only get/patch the pig-ebank Deployment;
the pull Secret is mounted as a file and requires no Kubernetes Secret API access.

ArgoCD ignores only this runtime annotation and preserves it during sync with
[`RespectIgnoreDifferences=true`](https://argo-cd.readthedocs.io/en/stable/user-guide/sync-options/#respect-ignore-differences-configs).
The image tag, application config, schedule,
script, and RBAC remain repo-managed. All resources are recreated by ArgoCD on
a fresh cluster. No initial digest or manually created registry secret is needed
beyond the existing ExternalSecret setup.

Merge the manifests and Application change into the default branch and let
ArgoCD sync to activate the updater. Check it with:

```sh
kubectl --context main-cluster -n pig-ebank get cronjob pig-ebank-image-update
kubectl --context main-cluster -n pig-ebank logs -l job-name=<job-name>
kubectl --context main-cluster -n pig-ebank rollout status deployment/pig-ebank
```

Set the CronJob's `spec.suspend: true` in Git to stop checks. It also skips
paused Deployments and images changed away from the exact floating `main` tag,
so a digest-pinned rollback is left alone. Suspending checks does not freeze
`main` for future Pod starts: pin the Deployment image to an immutable digest
for that. This polls the latest image; intermediate builds within five minutes
may be skipped. It requests the existing Deployment rollout strategy and does
not provide automatic rollback or guarantee a successful application startup.

Run the isolated rollout-decision tests with:

```sh
uv run --with pytest --with pyyaml pytest -q kubernetes/tests/test_pig_ebank_auto_update.py
```
