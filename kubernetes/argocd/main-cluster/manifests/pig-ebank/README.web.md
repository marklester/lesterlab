# Flutter web UI

The `pig-ebank-ui.<type>.yaml` manifests are picked up by the existing `pig-ebank` Argo CD application.
It runs the versioned `ghcr.io/marklester/pig-ebank-ui` image from the Pig E-Bank
repository, using the existing GHCR pull secret in the `pig-ebank` namespace.
The secret's GHCR token must have read access to the new UI package as well.

The container serves Flutter at `/` and proxies `/api/v1/` to the existing
`pig-ebank` Service. The UI and Android use the same backend and database.
The container accepts uploads up to 6 MiB including multipart overhead.

Before syncing:

1. Build and push the app release's image using
   `python3 pig-ebank-ui/tool/web_image.py --push` in the Pig E-Bank repository.
   Update the Deployment image tag to match its Flutter version name (`X.Y.Z`).
   The full Flutter `X.Y.Z+N` version is recorded in the image's OCI label.
2. Point public `app.pig-ebank.app` DNS and port 80/443 forwarding at the main
   cluster Traefik ingress. Let's Encrypt uses HTTP-01 on port 80 to issue
   `pig-ebank-ui-tls`. `.app` browsers require HTTPS.
3. Point local `app.pig-ebank.home` DNS at the main cluster ingress. For browser
   secure storage, serve it over HTTPS using a locally trusted certificate;
   Let's Encrypt cannot issue `.home` certificates. The supplied Ingress routes
   this hostname but does not provision its private certificate. Prefer the
   public HTTPS hostname until local certificate trust is configured.

After sync, check Deployment readiness, the `pig-ebank-ui-tls` Certificate,
`/healthz`, a direct `/family` page load, and `/api/v1/auth/me` (401 while signed
out). The UI uses memory-only browser sessions, so reloading requires sign-in.

Future releases build/push the web image as part of the Pig E-Bank release
workflow. Rollouts remain explicit: update the image tag here after publishing
and let Argo CD sync it. Version tags avoid unnoticed updates to running pods.
