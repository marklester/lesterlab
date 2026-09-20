# tunarr — CLI for the Tunarr live-TV API

A single-file-runnable CLI for managing [Tunarr](https://github.com/.../tunarr)
channels: inspect media sources/libraries, search programs, create channels,
add programs, verify channel health, and convert channels between media
sources.

## Quick start

```bash
# One-time setup (creates .venv/ and installs the project + dev extras):
uv sync --all-extras

# Run the CLI (either entry point works):
.venv/bin/tunarr --help
.venv/bin/python tunarr.py --help

# Common operations (defaults to http://tunarr.home, source "Plex In Cluster"):
.venv/bin/tunarr channels list
.venv/bin/tunarr channels verify 1
.venv/bin/tunarr programs search "Bluey" --limit 10
.venv/bin/tunarr channels convert 1 --mode time --dry-run
```

`uv sync` reads `pyproject.toml`, creates `.venv/`, and installs the project
(itself, editable, with the `tunarr` console script) plus `click` and the
dev extras (`pytest`). `.venv/` is gitignored; re-run `uv sync` after pulling
changes to dependencies.

## Layout

```
scripts/
├── pyproject.toml       # project metadata, deps, console script, uv config
├── tunarr.py            # thin entry point — just imports main()
├── tunarr_cli/
│   ├── __init__.py      # public exports
│   ├── models.py        # typed dataclasses for API objects
│   ├── client.py        # TunarrClient — thin HTTP layer over urllib
│   └── cli.py           # click CLI (commands, resolution, payload building)
└── tests/
    ├── conftest.py      # fake Tunarr HTTP server + fixtures
    ├── test_models.py   # model round-trip tests (no HTTP)
    ├── test_client.py   # client integration tests (fake server)
    └── test_cli.py      # end-to-end CLI tests through main(argv)
```

Run the tests:

```bash
.venv/bin/python -m pytest tests/ -q
```

## Design choices

### 1. uv-managed venv project

The CLI is a small uv project: `pyproject.toml` declares the dependencies
(`click`), a `tunarr` console script, and a `dev` extra (`pytest`).
`uv sync --all-extras` creates `.venv/` and installs the project itself
(`tool.uv.package = true`) plus the dev extras. Trade-offs considered:

- **Persistent venv over ephemeral `uv run`.** Dependencies are installed once
  into `.venv/` (gitignored) instead of resolved on every invocation. The
  console script (`.venv/bin/tunarr`) is a stable entry point, and the same
  environment serves the CLI and the test suite.
- **`pyproject.toml` as the single source of truth.** One file describes the
  runtime dependency, the dev dependency, and the entry point; `uv.lock`
  pins exact versions for reproducible environments.
- **Stdlib HTTP only.** `urllib.request` is enough for a small JSON API;
  pulling in `requests`/`httpx` would add a dependency for no benefit (no
  connection pooling needed, no streaming).
- The cost: a one-time `uv sync` step, and `.venv/` must be recreated on a
  fresh checkout. Acceptable for an interactive CLI.

### 2. click for the CLI

- **Grouped subcommands** mirror the API's resource hierarchy:
  `channels list|get|programs|create|add-programs|verify|schedule|convert`,
  `programs search|search-by`, `media-sources list`, `libraries list`,
  `transcode-configs list`.
- **Typed options for free**: `click.Choice` for stream modes and convert
  modes, a `positive_int` callback for channel numbers, flags for
  `--dry-run`/`--append`/`--all-sources`.
- **`standalone_mode=False`** in `main()` so the CLI can be driven
  programmatically (tests call `main(argv)` and assert on return codes and
  captured stdout/stderr) while still behaving like a normal CLI when run
  directly.
- Errors are two-tier: `TunarrError` (API/operational failures) → exit 1 with
  `tunarr: <message>` on stderr; `click.ClickException` (bad arguments) →
  click's standard usage error.

### 3. Typed dataclasses with a `raw` escape hatch

Every API object (`Program`, `Channel`, `MediaSource`, `Library`, `Slot`,
`Schedule`, `Programming`, `LineupEntry`, `Identifier`, `TranscodeConfig`) is a
dataclass with:

- **Explicit typed fields** for the properties the CLI actually uses
  (`program.media_source_id`, `slot.show_id`, …) — so the interesting parts of
  the API are discoverable and typo-checked.
- **`raw: dict`** — the untouched JSON, kept on every object. `to_dict()`
  returns `raw` when present, so **unknown fields survive a round trip
  losslessly**. This matters because Tunarr's payloads (channel objects,
  schedule slots) contain fields the CLI doesn't model (`offline`,
  `guideMinimumDuration`, `flexPreference`, …); when `convert` rewrites a
  schedule it must not drop fields it doesn't understand.
- `from_dict` is deliberately permissive: missing keys become `None`, unknown
  keys are ignored (they live in `raw`).

The alternative — full schema validation (pydantic) — was rejected: the API is
our own, stable, and the `raw` round-trip already guarantees we never corrupt
data we don't model.

### 4. Source/library resolution by name, not id

Users think in names ("Plex In Cluster", "Movies"), not UUIDs. The CLI
resolves names → ids at the command boundary (`require_single_source`,
`resolve_library_id`) and the client layer only ever deals in ids.
`--all-sources` exists for searches that must span both Plex instances.

### 5. Search pagination lives in the client

Tunarr caps `POST /api/programs/search` at **20 results per page** (one-based
`page`). `client.search_programs` walks pages until `limit` is satisfied or
`totalPages` is exhausted, so callers can ask for 20000 results in one call.
`search_all` is the `query=None` variant used by `convert` to build
identifier→program maps for an entire source.

### 6. Cross-source identifier matching order

`convert` maps old-source programs to new-source programs by:

1. **tmdb** id, then **imdb**, then **tvdb** — stable external ids that
   survive re-scans. (Plex GUIDs are *not* comparable across instances.)
2. **Unique lowercased title** as a fallback — only when exactly one
   candidate matches, to avoid silent mis-mapping.

Unmatched programs are reported (`unmatched`, `unmatchedTitles`) rather than
silently dropped, and `--dry-run` prints the full payload before any POST.

### 7. Verification from the materialized lineup

`channels verify` reads `GET /api/channels/{id}/programming` and checks the
**`lineup`** (the fully materialized schedule), not the `programs` map:

- `badSource` — lineup content entries whose program's `mediaSourceId` is not
  the target source.
- `badState` — programs whose `state != "ok"`.

The `programs` map can contain programs that are no longer in the lineup, so
it overstates problems; the lineup is what actually plays.

### 8. Test strategy: fake server, no live instance

`tests/conftest.py` spins up a `ThreadingHTTPServer` on `127.0.0.1:0` that
implements just enough of the Tunarr API (version, media-sources,
transcode-configs, channels, channel programming, program detail, and
search with real pagination). This gives:

- **Deterministic integration tests** — the client's pagination loop, error
  paths (HTTP 404 → `TunarrError`, unreachable host → `TunarrError`), and the
  full CLI (arg parsing → resolution → payload → POST) are exercised without
  touching the real instance.
- **No network flakiness** — the server is in-process; tests run in ~16s.
- The fake server records every POST (`state["posts"]`), so tests can assert
  on the exact payloads the CLI would have sent — including asserting that
  `--dry-run` sends *nothing*.

Model tests (`test_models.py`) are pure unit tests: round-tripping through
`from_dict`/`to_dict` must preserve unknown fields.

## Known API facts baked into this code

- Channel creation payload is `{"type": "new", "channel": {...}}` (the
  channel object carries `id`, `startTime`, `streamMode`,
  `transcodeConfigId`, `offline`, `stealth`, …).
- Programming POST variants: `{"type": "manual", "lineup": [...]}` and
  `{"type": "time", "programs": [...], "schedule": {...}}`.
- In a time schedule, a **movie slot's `id` field is the movie's program
  uuid**; show slots carry the show uuid in `showId`; flex slots have neither.
- `GET /api/programs/{id}` works for episodes and movies but **404s for
  shows** — a show record is not directly fetchable. `channels schedule`
  therefore resolves shows by exact title via `search_all` (filtering
  `type == "show"`), not via `client.program()`.
- A show's episode list comes from `GET /api/programs/{showId}/descendants`
  (each entry is a content entry whose `id` is the episode uuid); that is the
  source of the `programs` field in a time-schedule POST.
- A title search for a *show* name returns its episodes/movies, not the show
  itself; exact-title matching on a show name can legitimately return `[]`.
