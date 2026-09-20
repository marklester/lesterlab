"""Click-based CLI for the Tunarr REST API.

Global options (``--url``, ``--source-name``, ``--all-sources``) live on the
root group and are shared by every subcommand via ``ctx.obj``.
"""

from __future__ import annotations

import json
import sys
import time
import uuid as uuid_module
from typing import Any

import click

from tunarr_cli.client import TunarrClient, TunarrError
from tunarr_cli.models import STREAM_MODES, Program

DEFAULT_URL = "http://tunarr.home"
DEFAULT_SOURCE_NAME = "Plex In Cluster"


def print_json(value: Any) -> None:
    json.dump(value, sys.stdout, indent=2)
    sys.stdout.write("\n")


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise click.BadParameter(f"expected an integer, got {value!r}") from error
    if number < 1:
        raise click.BadParameter("must be a positive integer")
    return number


# --------------------------------------------------------------- resolution


def selected_sources(client: TunarrClient, source_name: str | None, all_sources: bool) -> list[dict[str, Any]]:
    """Return the media sources selected by the global source options."""
    sources = client.get("media-sources")
    if all_sources or not source_name:
        return sources
    matches = [s for s in sources if s.get("name") == source_name]
    if not matches:
        available = ", ".join(str(s.get("name")) for s in sources)
        raise TunarrError(
            f"media source {source_name!r} not found; available: {available}. "
            "Use --source-name or --all-sources."
        )
    if len(matches) > 1:
        raise TunarrError(f"media source {source_name!r} is not unique")
    return matches


def require_single_source(client: TunarrClient, source_name: str | None, all_sources: bool) -> str:
    sources = selected_sources(client, source_name, all_sources)
    if len(sources) != 1:
        raise TunarrError(
            f"expected exactly one media source, got {len(sources)}; "
            "use --source-name or --all-sources"
        )
    return str(sources[0]["id"])


def resolve_library_id(
    client: TunarrClient,
    source_name: str | None,
    all_sources: bool,
    reference: str,
) -> str:
    """Resolve a library by id or name across the selected source(s)."""
    matches: list[dict[str, Any]] = []
    for source in selected_sources(client, source_name, all_sources):
        for library in source.get("libraries", []):
            if str(library.get("id")) == reference or library.get("name") == reference:
                matches.append(library)
    if len(matches) != 1:
        raise TunarrError(f"library {reference!r} matched {len(matches)} libraries; expected exactly one")
    return str(matches[0]["id"])


def resolve_transcode_id(client: TunarrClient, reference: str | None) -> str:
    configs = client.get("transcode_configs")
    if reference is None:
        defaults = [c for c in configs if c.get("isDefault")]
        if len(defaults) != 1:
            raise TunarrError(f"expected exactly one default transcode config, got {len(defaults)}")
        return str(defaults[0]["id"])
    matches = [c for c in configs if str(c.get("id")) == reference or c.get("name") == reference]
    if len(matches) != 1:
        raise TunarrError(f"transcode config {reference!r} matched {len(matches)} configs; expected exactly one")
    return str(matches[0]["id"])


def resolve_channel_id(client: TunarrClient, reference: str) -> str:
    channels = client.get("channels")
    matches = [
        c
        for c in channels
        if str(c.get("id")) == reference
        or str(c.get("number")) == reference
        or c.get("name") == reference
    ]
    if len(matches) != 1:
        raise TunarrError(f"channel {reference!r} matched {len(matches)} channels; expected exactly one")
    return str(matches[0]["id"])


# ------------------------------------------------------------- search helpers


def is_playable(program: Program) -> bool:
    return program.is_playable


def search_programs(
    client: TunarrClient,
    query: str,
    source_name: str | None,
    all_sources: bool,
    library_id: str | None,
    limit: int,
    playable_only: bool = False,
) -> list[Program]:
    media_source_id = None
    if library_id is None and not all_sources and source_name:
        media_source_id = require_single_source(client, source_name, all_sources)
    programs = client.search_programs(
        query, library_id=library_id, media_source_id=media_source_id, limit=limit
    )
    if playable_only:
        programs = [p for p in programs if is_playable(p)]
    return programs


def programming_payload(
    client: TunarrClient,
    query: str,
    source_name: str | None,
    all_sources: bool,
    library_id: str | None,
    limit: int,
    append: bool,
) -> dict[str, Any]:
    programs = search_programs(
        client, query, source_name, all_sources, library_id, limit, playable_only=True
    )
    if not programs:
        raise TunarrError(f"no playable programs matched query {query!r}")
    return {
        "type": "manual",
        "append": append,
        "lineup": [
            {"type": "content", "duration": p.duration, "id": p.uuid} for p in programs
        ],
    }


def search_all(
    client: TunarrClient,
    source_name: str | None,
    all_sources: bool,
    library_id: str | None,
    limit: int = 20000,
) -> list[Program]:
    media_source_id = None
    if library_id is None and not all_sources and source_name:
        media_source_id = require_single_source(client, source_name, all_sources)
    return client.search_all(library_id=library_id, media_source_id=media_source_id, limit=limit)


# ---------------------------------------------------------- identifier mapping


def program_identifiers(program: Program) -> dict[str, str]:
    return program.identifiers_by_type()


def build_lookup_maps(programs: list[Program]) -> tuple[dict[str, dict[str, str]], dict[str, list[str]]]:
    """Build (by_identifier, by_title) lookup maps for cross-source matching.

    ``by_identifier`` maps identifier type -> {id -> uuid}; ``plex-guid`` and
    ``plex`` are skipped because they are source-specific. ``by_title`` maps
    lowercased title -> [uuids].
    """
    by_identifier: dict[str, dict[str, str]] = {}
    by_title: dict[str, list[str]] = {}
    for program in programs:
        for type_, id_ in program_identifiers(program).items():
            if type_ in ("plex-guid", "plex"):
                continue
            by_identifier.setdefault(type_, {})[id_] = program.uuid
        title = (program.sort_title or program.title).strip().lower()
        if title:
            by_title.setdefault(title, []).append(program.uuid)
    return by_identifier, by_title


def map_programs(
    old_programs: dict[str, Any],
    by_identifier: dict[str, dict[str, str]],
    by_title: dict[str, list[str]],
) -> tuple[dict[str, str], list[str]]:
    """Map old program ids to new ones via tmdb -> imdb -> tvdb, then title."""
    mapping: dict[str, str] = {}
    unmatched: list[str] = []
    for old_id, entry in old_programs.items():
        program = entry.get("program", {}) if isinstance(entry, dict) else {}
        identifiers = {
            str(i.get("type")): str(i.get("id"))
            for i in program.get("identifiers", [])
            if i.get("type") and i.get("id")
        }
        new_id: str | None = None
        for type_ in ("tmdb", "imdb", "tvdb"):
            id_ = identifiers.get(type_)
            if id_ and id_ in by_identifier.get(type_, {}):
                new_id = by_identifier[type_][id_]
                break
        if new_id is None:
            title = (program.get("sortTitle") or program.get("title") or "").strip().lower()
            candidates = by_title.get(title, [])
            if len(candidates) == 1:
                new_id = candidates[0]
        if new_id is None:
            unmatched.append(str(program.get("title", old_id)))
        else:
            mapping[old_id] = new_id
    return mapping, unmatched


# --------------------------------------------------------------- CLI plumbing


class Ctx:
    """Shared state for one CLI invocation."""

    def __init__(self, url: str, source_name: str | None, all_sources: bool) -> None:
        self.url = url
        self.source_name = source_name
        self.all_sources = all_sources
        self.client = TunarrClient(url)


@click.group()
@click.option("--url", default=DEFAULT_URL, show_default=True, help="Tunarr base URL.")
@click.option(
    "--source-name",
    default=DEFAULT_SOURCE_NAME,
    show_default=True,
    help="Media source name to scope library/search operations.",
)
@click.option(
    "--all-sources",
    "all_sources",
    is_flag=True,
    help="Do not scope operations to a single media source.",
)
@click.version_option("0.1.0", prog_name="tunarr")
@click.pass_context
def cli(ctx: click.Context, url: str, source_name: str | None, all_sources: bool) -> None:
    """Client for the Tunarr live-TV channel API."""
    ctx.obj = Ctx(url, source_name, all_sources)


def get_ctx(ctx: click.Context) -> Ctx:
    return ctx.obj


@cli.command("version")
@click.pass_context
def cmd_version(ctx: click.Context) -> None:
    """Print the Tunarr server version."""
    state = get_ctx(ctx)
    print_json(state.client.version())


@cli.group("media-sources")
def media_sources_group() -> None:
    """Inspect media sources."""


@media_sources_group.command("list")
@click.pass_context
def cmd_media_sources_list(ctx: click.Context) -> None:
    """List media sources."""
    state = get_ctx(ctx)
    print_json(state.client.get("media-sources"))


@cli.group("libraries")
def libraries_group() -> None:
    """Inspect libraries."""


@libraries_group.command("list")
@click.pass_context
def cmd_libraries_list(ctx: click.Context) -> None:
    """List libraries across media sources."""
    state = get_ctx(ctx)
    print_json([l.to_dict() for l in state.client.libraries()])


@cli.group("transcode-configs")
def transcode_configs_group() -> None:
    """Inspect transcode configs."""


@transcode_configs_group.command("list")
@click.pass_context
def cmd_transcode_configs_list(ctx: click.Context) -> None:
    """List transcode configs."""
    state = get_ctx(ctx)
    print_json(state.client.get("transcode_configs"))


@cli.group("programs")
def programs_group() -> None:
    """Search programs."""


@programs_group.command("search")
@click.argument("query")
@click.option("--library", help="Library id or name.")
@click.option("--limit", default=20, show_default=True, type=click.IntRange(min=1))
@click.pass_context
def cmd_programs_search(
    ctx: click.Context, query: str, library: str | None, limit: int
) -> None:
    """Search programs by QUERY text."""
    state = get_ctx(ctx)
    library_id = (
        resolve_library_id(state.client, state.source_name, state.all_sources, library)
        if library
        else None
    )
    programs = search_programs(
        state.client, query, state.source_name, state.all_sources, library_id, limit
    )
    print_json([p.to_dict() for p in programs])


@programs_group.command("search-by")
@click.option("--title", help="Exact (case-insensitive) title match.")
@click.option("--identifier", help="Match any identifier id (tmdb/imdb/tvdb/plex-guid/plex).")
@click.option("--library", help="Library id or name.")
@click.option("--limit", default=20000, show_default=True, type=click.IntRange(min=1))
@click.pass_context
def cmd_programs_search_by(
    ctx: click.Context,
    title: str | None,
    identifier: str | None,
    library: str | None,
    limit: int,
) -> None:
    """Search all programs, filtered by exact TITLE and/or IDENTIFIER id."""
    state = get_ctx(ctx)
    if not title and not identifier:
        raise TunarrError("search-by requires --title and/or --identifier")
    library_id = (
        resolve_library_id(state.client, state.source_name, state.all_sources, library)
        if library
        else None
    )
    programs = search_all(
        state.client, state.source_name, state.all_sources, library_id, limit=limit
    )
    matches = []
    for program in programs:
        if title and (program.sort_title or program.title).strip().lower() != title.strip().lower():
            continue
        if identifier and identifier not in program_identifiers(program).values():
            continue
        if title or identifier:
            matches.append(
                {
                    "uuid": program.uuid,
                    "title": program.title,
                    "type": program.type,
                    "identifiers": [i.to_dict() for i in program.identifiers],
                }
            )
    print_json(matches)


@cli.group("channels")
def channels_group() -> None:
    """Manage channels."""


@channels_group.command("list")
@click.pass_context
def cmd_channels_list(ctx: click.Context) -> None:
    """List channels."""
    state = get_ctx(ctx)
    print_json([c.to_dict() for c in state.client.channels()])


@channels_group.command("get")
@click.argument("channel")
@click.pass_context
def cmd_channels_get(ctx: click.Context, channel: str) -> None:
    """Show one channel by id, number, or name."""
    state = get_ctx(ctx)
    channel_id = resolve_channel_id(state.client, channel)
    print_json(next(c.to_dict() for c in state.client.channels() if c.id == channel_id))


@channels_group.command("programs")
@click.argument("channel")
@click.option("--limit", default=20, show_default=True, type=click.IntRange(min=1))
@click.option("--offset", default=0, show_default=True, type=click.IntRange(min=0))
@click.pass_context
def cmd_channels_programs(
    ctx: click.Context, channel: str, limit: int, offset: int
) -> None:
    """List programs referenced by a channel's programming."""
    state = get_ctx(ctx)
    channel_id = resolve_channel_id(state.client, channel)
    programming = state.client.channel_programming(channel_id)
    programs = list(programming.programs.values())
    print_json([p.to_dict() for p in programs[offset : offset + limit]])


@channels_group.command("create")
@click.option("--name", required=True)
@click.option("--number", required=True, type=positive_int)
@click.option("--library", help="Library id or name.")
@click.option("--query", help="Program search query for the initial lineup.")
@click.option("--limit", default=20, show_default=True, type=click.IntRange(min=1))
@click.option("--group-title", default="tunarr", show_default=True)
@click.option("--transcode-config", help="Transcode config id or name; default config if omitted.")
@click.option("--stream-mode", default="hls", show_default=True, type=click.Choice(STREAM_MODES))
@click.option("--subtitles", is_flag=True)
@click.option("--icon", default="")
@click.option("--start-time", type=int, help="Start time in ms; now if omitted.")
@click.option("--append", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def cmd_channels_create(
    ctx: click.Context,
    name: str,
    number: int,
    library: str | None,
    query: str | None,
    limit: int,
    group_title: str,
    transcode_config: str | None,
    stream_mode: str,
    subtitles: bool,
    icon: str,
    start_time: int | None,
    append: bool,
    dry_run: bool,
) -> None:
    """Create a channel and (optionally) seed it with a manual lineup."""
    state = get_ctx(ctx)
    client = state.client
    library_id = (
        resolve_library_id(client, state.source_name, state.all_sources, library)
        if library
        else None
    )
    transcode_id = resolve_transcode_id(client, transcode_config)
    payload: dict[str, Any] = {
        "type": "new",
        "channel": {
            "disableFillerOverlay": False,
            "duration": 0,
            "groupTitle": group_title,
            "guideMinimumDuration": 30000,
            "icon": {"path": icon, "width": 0, "duration": 0, "position": "bottom-right"},
            "id": str(uuid_module.uuid4()),
            "name": name,
            "number": number,
            "offline": {"picture": "", "soundtrack": "", "mode": "pic"},
            "startTime": start_time if start_time is not None else int(time.time() * 1000),
            "stealth": False,
            "streamMode": stream_mode,
            "transcodeConfigId": transcode_id,
            "subtitlesEnabled": subtitles,
        },
    }
    if dry_run:
        print_json({"summary": {"name": name, "number": number}, "payload": payload})
        return
    channel_response = client.post("channels", payload)
    channel_id = channel_response.get("id") or channel_response.get("channel", {}).get("id")
    result: dict[str, Any] = {"channel": channel_id}
    if query:
        programming = programming_payload(
            client, query, state.source_name, state.all_sources, library_id, limit, append
        )
        client.post(f"channels/{channel_id}/programming", programming)
        result["programming"] = programming
    print_json(result)


@channels_group.command("add-programs")
@click.argument("channel")
@click.option("--library", required=True)
@click.option("--query", required=True)
@click.option("--limit", default=20, show_default=True, type=click.IntRange(min=1))
@click.option("--append", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.pass_context
def cmd_channels_add_programs(
    ctx: click.Context,
    channel: str,
    library: str,
    query: str,
    limit: int,
    append: bool,
    dry_run: bool,
) -> None:
    """Add a manual lineup of programs matching QUERY to a channel."""
    state = get_ctx(ctx)
    client = state.client
    channel_id = resolve_channel_id(client, channel)
    library_id = resolve_library_id(client, state.source_name, state.all_sources, library)
    payload = programming_payload(
        client, query, state.source_name, state.all_sources, library_id, limit, append
    )
    if dry_run:
        print_json({"channel": channel_id, "payload": payload})
        return
    response = client.post(f"channels/{channel_id}/programming", payload)
    print_json({"channel": channel_id, "response": response})


@channels_group.command("verify")
@click.argument("channel")
@click.pass_context
def cmd_channels_verify(ctx: click.Context, channel: str) -> None:
    """Verify a channel's lineup all points at the selected source, state ok."""
    state = get_ctx(ctx)
    client = state.client
    channel_id = resolve_channel_id(client, channel)
    source_id = require_single_source(client, state.source_name, state.all_sources)
    programming = client.channel_programming(channel_id)
    content_ids = programming.content_ids()
    bad_source = [
        pid
        for pid in content_ids
        if programming.programs.get(pid)
        and programming.programs[pid].media_source_id != source_id
    ]
    bad_state = [
        pid
        for pid in content_ids
        if programming.programs.get(pid) and programming.programs[pid].state != "ok"
    ]
    print_json(
        {
            "channel": channel_id,
            "source": state.source_name,
            "lineupContent": len(content_ids),
            "uniquePrograms": len(programming.programs),
            "badSource": len(bad_source),
            "badState": len(bad_state),
            "badSourceIds": bad_source[:20],
            "badStateIds": bad_state[:20],
        }
    )


@channels_group.command("convert")
@click.argument("channel")
@click.option("--mode", required=True, type=click.Choice(["manual", "time"]))
@click.option("--limit", default=20000, show_default=True, type=click.IntRange(min=1))
@click.option("--dry-run", is_flag=True)
@click.pass_context
def cmd_channels_convert(
    ctx: click.Context, channel: str, mode: str, limit: int, dry_run: bool
) -> None:
    """Re-point a channel's programs at the selected source.

    Remaps every program in the channel (manual lineup or time schedule)
    from its current source to the selected source, matching by tmdb,
    imdb, tvdb identifier, then unique title.
    """
    state = get_ctx(ctx)
    client = state.client
    channel_id = resolve_channel_id(client, channel)
    source_id = require_single_source(client, state.source_name, state.all_sources)
    programming = client.channel_programming(channel_id)
    if not programming.programs:
        raise TunarrError("channel has no programs to convert")
    new_programs = search_all(client, state.source_name, state.all_sources, None, limit=limit)
    by_identifier, by_title = build_lookup_maps(new_programs)
    mapping, unmatched = map_programs(
        {pid: {"program": p.to_dict()} for pid, p in programming.programs.items()},
        by_identifier,
        by_title,
    )
    if mode == "manual":
        lineup = [
            {**entry.to_dict(), "id": mapping[entry.id]}
            if entry.type == "content" and entry.id in mapping
            else entry.to_dict()
            for entry in programming.lineup
        ]
        payload: dict[str, Any] = {"type": "manual", "lineup": lineup}
    else:
        if programming.schedule is None:
            raise TunarrError("channel is not time-programmed; use --mode manual")
        schedule = programming.schedule
        new_slots: list[dict[str, Any]] = []
        for slot in schedule.slots:
            slot_dict = slot.to_dict()
            if slot.type == "show" and slot.show_id:
                show = client.program(slot.show_id)
                identifiers = program_identifiers(show)
                new_show_id: str | None = None
                for type_ in ("tmdb", "imdb", "tvdb"):
                    id_ = identifiers.get(type_)
                    if id_ and id_ in by_identifier.get(type_, {}):
                        new_show_id = by_identifier[type_][id_]
                        break
                if new_show_id is None:
                    title = (show.sort_title or show.title).strip().lower()
                    candidates = by_title.get(title, [])
                    if len(candidates) == 1:
                        new_show_id = candidates[0]
                if new_show_id is None:
                    unmatched.append(show.title)
                    continue
                slot_dict["showId"] = new_show_id
            elif slot.type == "movie" and slot.id in mapping:
                slot_dict["id"] = mapping[slot.id]
            new_slots.append(slot_dict)
        payload = {
            "type": "time",
            "programs": [mapping[pid] for pid in programming.programs if pid in mapping],
            "schedule": {**schedule.to_dict(), "slots": new_slots},
        }
    summary = {
        "channel": channel_id,
        "mode": mode,
        "mapped": len(mapping),
        "unmatched": len(unmatched),
        "unmatchedTitles": unmatched[:50],
        "targetSource": state.source_name,
    }
    if dry_run:
        print_json({"summary": summary, "payload": payload})
        return
    response = client.post(f"channels/{channel_id}/programming", payload)
    print_json({**summary, "response": response})


def main(argv: list[str] | None = None) -> int:
    try:
        cli.main(args=argv, standalone_mode=False)
    except TunarrError as error:
        click.echo(f"tunarr: {error}", err=True)
        return 1
    except click.ClickException as error:
        error.show()
        return error.exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
