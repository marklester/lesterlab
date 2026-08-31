# AGENTS.md

Guidance for AI agents working in this repository.

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
