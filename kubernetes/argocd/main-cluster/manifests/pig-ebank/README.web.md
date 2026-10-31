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
out). The cookie-based UI requires the backend browser-auth endpoints from
Pig E-Bank PR #92. Web sign-in uses Spring session cookies, and Remember me
uses the backend's existing 14-day cookie. Authentication tokens are not stored
in JavaScript storage. Without Remember me, a reload still restores the current
browser session; returning after the session ends requires sign-in.

Deploy the backend changes before releasing the cookie-based web image. The
backend Deployment's forwarded-header and cookie settings support HTTPS
termination at Traefik/NGINX and issue Secure, HttpOnly session cookies with
SameSite=Lax. Access the UI over HTTPS, including local `.home` deployments.
Both UI replicas proxy to the same single backend replica; browser sessions are
held by that backend. Scaling the backend requires shared sessions or deliberate
session routing. A backend restart ends in-memory sessions, while a valid
Remember me cookie can reauthenticate the user.

The existing `/api/v1/` proxy forwards cookies, Set-Cookie and CSRF headers.
All browser calls stay on the UI hostname; no CORS configuration or shared
cookie domain is needed. Root and `app.*` hostnames have separate cookies.

Future releases build/push the web image as part of the Pig E-Bank release
workflow. Rollouts remain explicit: update the image tag here after publishing
and let Argo CD sync it. Version tags avoid unnoticed updates to running pods.

## Hostnames

- `app.pig-ebank.app` and `app.pig-ebank.home`: Flutter UI.
- `pig-ebank.app` and `pig-ebank.home`: additional ingress routes for the UI.
- `api.pig-ebank.app` and `api.pig-ebank.home`: backend.
- `pig-ebank.lester.network`: legacy backend route retained.

Root-domain `/api/v1/` continues to route to the backend so installed Android
clients work during migration. Invitation and NFC links keep `pig-ebank.app`,
including its existing exact `/.well-known/assetlinks.json` route. The backend
invitation base URL explicitly uses that root domain. Flutter normalizes legacy
`/createAccount` and `/app/` paths. Web API calls remain same-origin through
NGINX and the in-cluster backend Service.

Add public DNS for `api.pig-ebank.app` pointing to the same ingress as
`pig-ebank.app` before distributing Android builds with the new API default.
The existing Let's Encrypt issuer provisions `pig-ebank-api-tls`; check that
certificate is ready before releasing the client change. Add local DNS for
`api.pig-ebank.home` to `192.168.0.200`. All `.home` names still require local
certificate trust for secure browser use. This change does not modify DNS.
