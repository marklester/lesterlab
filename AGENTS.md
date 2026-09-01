# AGENTS.md

Guidance for AI agents working in this repository.

## Design goal: reproducible app deployments

One of the core goals of this repo is to make app deployments as reproducible
as possible. Prefer manifests that fully describe an app's desired state from
the repo alone, so a fresh cluster (or a re-sync) can be brought up without
relying on out-of-band state.

- Where an app's configuration is static and known ahead of time, encode it in
  the repo (e.g. a `ConfigMap` mounted into the pod) rather than depending on
  values that only exist in a live PVC or that were set interactively in a UI.
- Treat the repo as the source of truth for configuration. If a change is made
  in a running app's UI, reflect it back into the repo so the manifest matches
  reality.
- Be aware of the trade-off: a `ConfigMap` mounted as a file is read-only to
  the pod, so an app that writes its config back at runtime will not persist
  UI-driven changes. Choose this approach deliberately for apps whose config is
  meant to be static and repo-managed.

## Renovate config (`.renovaterc.json`) — validation method

The Renovate config in this repo has been validated using the following steps.
Repeat these when making changes to `.renovaterc.json` or to the manifests it covers.

### 1. JSON validity
- Confirm `.renovaterc.json` parses as valid JSON.
- A VS Code "schema not trusted / remote schema fetch blocked" warning on this file is
  pre-existing and harmless — it is not a JSON error.

### 2. End-to-end dry-run via Docker
Node.js is not installed on the dev host, so Renovate is run via Docker:
```powershell
$docker = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
& $docker run --rm -e LOG_LEVEL=debug -v "c:\Users\starf\Programming\lesterlab:/workspace" -w /workspace `
  renovate/renovate:latest --platform github --token "$env:GITHUB_TOKEN" --dry-run marklester/lesterlab
```
Notes:
- Use the `--token "$env:GITHUB_TOKEN"` CLI flag. Passing the token via
  `-e GITHUB_TOKEN=...` does not propagate into the container in this shell.
- There is no `config-validator` subcommand in Renovate 44.x — do not use it.
- **Important:** the dry-run clones the repo from GitHub, so it tests the
  *committed* config, not local uncommitted edits. Local changes only take
  effect in a dry-run after they are committed and pushed.
- With `LOG_LEVEL=debug`, the log contains lines like
  `DEBUG: Matched N file(s) for manager kubernetes: ...` — use these to confirm
  exactly which files each manager scanned.
