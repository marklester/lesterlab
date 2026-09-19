---
name: tunarr
description: Create and inspect Tunarr channels through the live Tunarr API, including selecting Plex libraries, searching programs, and building channel lineups.
---

# Tunarr channel workflows

Use `scripts/tunarr.py` for repeatable Tunarr API operations. The helper defaults
to `http://tunarr.home` and restricts media-source and library lookups to the
`Plex In Cluster` source. Keep that default unless the user explicitly asks for
another source or passes `--all-sources`.

## Discover the inputs

```bash
scripts/tunarr.py libraries list
scripts/tunarr.py transcode-configs list
scripts/tunarr.py channels list
```

Library arguments can be either a library ID or its name. With the default
source restriction, names such as `Movies` and `TV Shows` resolve only under
`Plex In Cluster`, even if another Plex source has a library with the same
name.

## Create a channel

For an empty channel:

```bash
  scripts/tunarr.py channels create \
  --name "Family Cartoons" --number 12 \
  --library "TV Shows" --query "Bluey" --limit 100
```

`channels create` creates the channel and, when `--query` is supplied, searches
the selected library and posts a manual content lineup. Search results are
paged through the API and parent records such as shows are excluded from the
lineup; playable movies, episodes, tracks, and music videos are retained.

Use `--dry-run` to inspect the exact create and programming payloads before a
write. Use `--append` when adding search results to an existing lineup.

For a channel that already exists:

```bash
  scripts/tunarr.py channels add-programs 12 \
  --library "TV Shows" --query "Paw Patrol" --append
```

Channel references may be UUIDs, channel numbers, or exact names.

## API details that affect decisions

- Channel creation is `POST /api/channels` with `{type: "new", channel: {...}}`.
- Program search is `POST /api/programs/search`; its pages are one-based and
  the server currently caps each response at 20 results, so the helper walks
  pages when `--limit` is greater than 20.
- Manual programming is `POST /api/channels/{id}/programming` with
  `{type: "manual", append, lineup: [{type: "content", id, duration}]}`.
- Transcode profiles come from `GET /api/transcode_configs`; the helper uses
  the API-marked default profile unless `--transcode-config` names an ID or
  profile.

Use `TUNARR_URL` or `--url` for a different instance. Use `--source-name` for
an explicit alternate media source; use `--all-sources` only when a workflow
intentionally spans sources.
