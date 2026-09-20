---
name: tunarr
description: Create and inspect Tunarr channels through the live Tunarr API, including selecting Plex libraries, searching programs, and building channel lineups.
---

# Tunarr channel workflows

Use `scripts/tunarr.py` for repeatable Tunarr API operations. The helper defaults
to `http://tunarr.home` and restricts media-source and library lookups to the
`Plex In Cluster` source. Keep that default unless the user explicitly asks for
another source or passes `--all-sources`.

## Running the CLI

The CLI is a uv project in the `scripts/` directory. Set up the venv once:

```bash
cd scripts
uv sync --all-extras
```

Then run it from the `scripts/` directory:

```bash
.venv/bin/tunarr --help
```

The implementation lives in the `tunarr_cli/` package (`models.py` typed
dataclasses, `client.py` HTTP client, `cli.py` click commands).
`scripts/README.md` documents the design choices.

Integration tests run against a fake Tunarr HTTP server (no live instance
needed):

```bash
.venv/bin/python -m pytest tests/ -q
```

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

## Search programs

```bash
scripts/tunarr.py programs search "Bluey" --limit 50
scripts/tunarr.py programs search-by --title "Bluey"
scripts/tunarr.py programs search-by --identifier tmdb-2194162
```

`search` is a title substring search; `search-by` fetches the full program
catalog for the selected source and matches on exact title or identifier
(`tmdb-<id>`, `imdb-<id>`, `tvdb-<id>`, or a raw value). Note: searching by a
show's title returns its episodes, not the show record — use `search-by`
when you need the parent show.

## Schedule a channel by time

```bash
scripts/tunarr.py channels schedule 12 --show "Phineas and Ferb"
scripts/tunarr.py channels schedule 12 --show "Bluey" --show "Paw Patrol" \
  --order shuffle --period day --max-days 365 --tz-offset 240 --dry-run
```

Posts a time-based schedule (`POST /api/channels/{id}/programming` with
`{type: "time", programs, schedule}`) that plays the named shows in show
slots. Each `--show` is resolved by exact title against the selected source
(must match exactly one show). With a single show the slot starts at midnight;
with several shows the slots are spaced evenly across the period. `--order`
sets the slot's play order (`shuffle` is the default; also `next`,
`ordered_shuffle`, `alphanumeric`, `chronological`). `--period` is `day` or
`week`; `--max-days` is how many days of schedule to pregenerate; `--tz-offset`
is the timezone offset in minutes (240 = UTC-4). The `programs` list is the
union of each show's descendant episodes (fetched from
`GET /api/programs/{showId}/descendants`). Use `--dry-run` to inspect the
payload before writing.

## Verify a channel

```bash
scripts/tunarr.py channels verify 1
```

Checks the channel's materialized lineup against the selected source:
`badSource` counts lineup programs whose `mediaSourceId` is not the target
source, `badState` counts programs whose state is not `ok`. A clean channel
reports `badSource: 0, badState: 0`.

## Convert a channel to a new source

```bash
scripts/tunarr.py channels convert 1 --mode time --dry-run
scripts/tunarr.py channels convert 1 --mode manual
```

Re-points a channel's programs at the selected source by matching each old
program's identifiers (tmdb, then imdb, then tvdb, then unique title) against
the full catalog of the target source. `--mode manual` remaps the lineup's
content entries; `--mode time` additionally remaps show slots (by show
identifier) and movie slots (the movie slot's `id` field is the movie's
program UUID). Always `--dry-run` first to inspect the payload and the
unmatched list.

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
