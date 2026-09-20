#!/usr/bin/env python3
"""Small Python CLI for creating and inspecting Tunarr channels."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any


PLAYABLE_TYPES = {"movie", "episode", "track", "music_video", "other_video"}
STREAM_MODES = ("hls", "hls_slower", "mpegts", "hls_direct", "hls_direct_v2")


class TunarrError(RuntimeError):
    """An actionable Tunarr CLI error."""


class TunarrClient:
    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}/api/{path.lstrip('/')}"
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace").strip()
            raise TunarrError(f"Tunarr API returned HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise TunarrError(f"could not reach Tunarr at {url}: {error.reason}") from error

        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise TunarrError(f"Tunarr returned invalid JSON from {url}") from error

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("POST", path, payload)


def print_json(value: Any) -> None:
    json.dump(value, sys.stdout, indent=2)
    sys.stdout.write("\n")


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def source_data(client: TunarrClient, args: argparse.Namespace) -> list[dict[str, Any]]:
    sources = client.get("media-sources")
    if not args.source_filter:
        return sources
    selected = [source for source in sources if source.get("name") == args.source_name]
    if len(selected) == 1:
        return selected
    available = ", ".join(str(source.get("name", "")) for source in sources)
    if not selected:
        raise TunarrError(
            f"media source {args.source_name!r} was not found "
            f"(available: {available}); use --source-name or --all-sources"
        )
    raise TunarrError(f"media source {args.source_name!r} is not unique")


def source_id(client: TunarrClient, args: argparse.Namespace) -> str:
    sources = source_data(client, args)
    if len(sources) != 1:
        raise TunarrError("multiple media sources are available; use --source-name")
    return str(sources[0]["id"])


def resolve_library_id(client: TunarrClient, args: argparse.Namespace, reference: str) -> str:
    matches: list[dict[str, Any]] = []
    for source in source_data(client, args):
        for library in source.get("libraries", []):
            if library.get("id") == reference or library.get("name") == reference:
                matches.append(library)
    if len(matches) != 1:
        raise TunarrError(f"library {reference!r} was not found uniquely in the selected source(s)")
    return str(matches[0]["id"])


def resolve_transcode_id(client: TunarrClient, reference: str | None) -> str:
    profiles = client.get("transcode_configs")
    if reference is None:
        matches = [profile for profile in profiles if profile.get("isDefault") is True]
    else:
        matches = [
            profile
            for profile in profiles
            if profile.get("id") == reference or profile.get("name") == reference
        ]
    if len(matches) != 1:
        label = reference or "default"
        raise TunarrError(f"transcode profile {label!r} was not found uniquely")
    return str(matches[0]["id"])


def resolve_channel_id(client: TunarrClient, reference: str) -> str:
    channels = client.get("channels")
    matches = [
        channel
        for channel in channels
        if str(channel.get("id")) == reference
        or str(channel.get("number")) == reference
        or channel.get("name") == reference
    ]
    if len(matches) != 1:
        raise TunarrError(f"channel {reference!r} was not found uniquely")
    return str(matches[0]["id"])


def is_playable(program: dict[str, Any]) -> bool:
    return program.get("type") in PLAYABLE_TYPES and program.get("duration") is not None


def search_programs(
    client: TunarrClient,
    args: argparse.Namespace,
    query: str,
    library_id: str | None,
    limit: int,
    playable_only: bool = False,
) -> list[dict[str, Any]]:
    media_source_id = None
    if library_id is None and args.source_filter:
        media_source_id = source_id(client, args)

    results: list[dict[str, Any]] = []
    page = 1
    total_pages = 1
    while page <= total_pages and len(results) < limit:
        payload: dict[str, Any] = {
            "query": {
                "query": query,
                "sort": [{"field": "title", "direction": "asc"}],
            },
            "page": page,
            # Tunarr 1.3.15 caps this endpoint at 20 results per page.
            "limit": 20,
            "expandParents": True,
        }
        if library_id is not None:
            payload["libraryId"] = library_id
        if media_source_id is not None:
            payload["mediaSourceId"] = media_source_id
        response = client.post("programs/search", payload)
        total_pages = int(response.get("totalPages", 1))
        for program in response.get("results", []):
            if not playable_only or is_playable(program):
                results.append(program)
                if len(results) >= limit:
                    break
        page += 1
    return results[:limit]


def programming_payload(
    client: TunarrClient,
    args: argparse.Namespace,
    query: str,
    library_id: str,
    limit: int,
    append: bool,
) -> dict[str, Any]:
    programs = search_programs(client, args, query, library_id, limit, playable_only=True)
    if not programs:
        raise TunarrError(f"no playable programs matched {query!r}")
    return {
        "type": "manual",
        "append": append,
        "lineup": [
            {"type": "content", "duration": program["duration"], "id": program["uuid"]}
            for program in programs
        ],
    }


def search_all(
    client: TunarrClient,
    args: argparse.Namespace,
    library_id: str | None,
    limit: int = 20000,
) -> list[dict[str, Any]]:
    """Fetch every program in a library (or the whole default source)."""
    media_source_id = None
    if library_id is None and args.source_filter:
        media_source_id = source_id(client, args)

    def build(page: int, page_limit: int) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": {"query": None, "sort": [{"field": "title", "direction": "asc"}]},
            "page": page,
            "limit": page_limit,
            "expandParents": True,
        }
        if library_id is not None:
            payload["libraryId"] = library_id
        if media_source_id is not None:
            payload["mediaSourceId"] = media_source_id
        return payload

    try:
        response = client.post("programs/search", build(1, 20))
    except TunarrError:
        # Server rejected the page parameter; fall back to a single large request.
        response = client.post("programs/search", build(1, limit))
    results: list[dict[str, Any]] = list(response.get("results", []))
    total_pages = int(response.get("totalPages", 1))
    page = 2
    while page <= total_pages and len(results) < limit:
        results.extend(client.post("programs/search", build(page, 20)).get("results", []))
        page += 1
    return results[:limit]


def program_identifiers(program: dict[str, Any]) -> dict[str, str]:
    return {
        str(identifier.get("type")): str(identifier.get("id"))
        for identifier in program.get("identifiers", [])
        if identifier.get("type") and identifier.get("id")
    }


def build_lookup_maps(
    programs: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, str]], dict[str, list[str]]]:
    by_identifier: dict[str, dict[str, str]] = {}
    by_title: dict[str, list[str]] = {}
    for program in programs:
        uuid = str(program.get("uuid"))
        title = str(program.get("title", "")).strip().lower()
        if title:
            by_title.setdefault(title, []).append(uuid)
        for identifier_type, identifier_id in program_identifiers(program).items():
            if identifier_type in ("plex-guid", "plex"):
                continue
            by_identifier.setdefault(identifier_type, {})[identifier_id] = uuid
    return by_identifier, by_title


def map_programs(
    old_programs: dict[str, Any],
    by_identifier: dict[str, dict[str, str]],
    by_title: dict[str, list[str]],
) -> tuple[dict[str, str], list[str]]:
    mapping: dict[str, str] = {}
    unmatched: list[str] = []
    for old_id, entry in old_programs.items():
        program = entry.get("program", {}) if isinstance(entry, dict) else {}
        new_id: str | None = None
        for identifier_type in ("tmdb", "imdb", "tvdb"):
            identifier_id = program_identifiers(program).get(identifier_type)
            if identifier_id and identifier_id in by_identifier.get(identifier_type, {}):
                new_id = by_identifier[identifier_type][identifier_id]
                break
        if new_id is None:
            title = str(program.get("sortTitle") or program.get("title") or "").strip().lower()
            candidates = by_title.get(title, [])
            if len(candidates) == 1:
                new_id = candidates[0]
        if new_id is None:
            unmatched.append(str(program.get("title") or program.get("sortTitle") or old_id))
        else:
            mapping[old_id] = new_id
    return mapping, unmatched


def cmd_channels_verify(client: TunarrClient, args: argparse.Namespace) -> None:
    channel_id = resolve_channel_id(client, args.channel)
    source = source_data(client, args)
    if len(source) != 1:
        raise TunarrError("verify requires exactly one media source; use --source-name")
    source_id_value = str(source[0]["id"])
    programming = client.get(f"channels/{channel_id}/programming")
    lineup = programming.get("lineup", [])
    programs = programming.get("programs", {})
    content_ids = [entry.get("id") for entry in lineup if entry.get("type") == "content"]
    bad_source = [pid for pid in content_ids if programs.get(pid, {}).get("program", {}).get("mediaSourceId") != source_id_value]
    bad_state = [pid for pid in content_ids if programs.get(pid, {}).get("program", {}).get("state") != "ok"]
    print_json(
        {
            "channel": channel_id,
            "source": source[0].get("name"),
            "lineupContent": len(content_ids),
            "uniquePrograms": len(set(content_ids)),
            "badSource": len(bad_source),
            "badState": len(bad_state),
            "badSourceIds": bad_source[:20],
            "badStateIds": bad_state[:20],
        }
    )


def cmd_channels_convert(client: TunarrClient, args: argparse.Namespace) -> None:
    channel_id = resolve_channel_id(client, args.channel)
    programming = client.get(f"channels/{channel_id}/programming")
    old_programs = programming.get("programs", {})
    if not old_programs:
        raise TunarrError("channel has no programs to convert")

    new_sources = source_data(client, args)
    if len(new_sources) != 1:
        raise TunarrError("convert requires exactly one target source; use --source-name")
    new_source = new_sources[0]

    new_programs = search_all(client, args, None, limit=args.limit)
    by_identifier, by_title = build_lookup_maps(new_programs)
    mapping, unmatched = map_programs(old_programs, by_identifier, by_title)

    if args.mode == "manual":
        lineup = [entry for entry in programming.get("lineup", []) if entry.get("type") == "content"]
        new_lineup = [
            {"type": "content", "duration": entry.get("duration"), "id": mapping[entry["id"]]}
            for entry in lineup
            if entry.get("id") in mapping
        ]
        payload = {"type": "manual", "lineup": new_lineup}
    else:
        schedule = programming.get("schedule")
        if not isinstance(schedule, dict):
            raise TunarrError("channel is not time-programmed; use --mode manual")
        slots = schedule.get("slots", [])
        new_slots = []
        for slot in slots:
            slot_type = slot.get("type")
            if slot_type == "show":
                details = client.get(f"programs/{slot['showId']}")
                new_id: str | None = None
                for identifier_type in ("tmdb", "imdb", "tvdb"):
                    identifier_id = program_identifiers(details).get(identifier_type)
                    if identifier_id and identifier_id in by_identifier.get(identifier_type, {}):
                        new_id = by_identifier[identifier_type][identifier_id]
                        break
                if new_id is None:
                    title = str(details.get("title", "")).strip().lower()
                    candidates = by_title.get(title, [])
                    new_id = candidates[0] if len(candidates) == 1 else None
                if new_id is None:
                    unmatched.append(str(details.get("title") or slot["showId"]))
                    continue
                new_slot = dict(slot)
                new_slot["showId"] = new_id
                new_slots.append(new_slot)
            elif slot_type == "movie":
                if slot.get("id") in mapping:
                    new_slot = dict(slot)
                    new_slot["id"] = mapping[slot["id"]]
                    new_slots.append(new_slot)
                else:
                    unmatched.append(str(slot.get("id")))
            else:
                new_slots.append(slot)
        payload = {
            "type": "time",
            "programs": [mapping[pid] for pid in programming.get("programs", {}) if pid in mapping],
            "schedule": {**schedule, "slots": new_slots},
        }

    summary = {
        "channel": channel_id,
        "mode": args.mode,
        "mapped": len(mapping),
        "unmatched": len(unmatched),
        "unmatchedTitles": unmatched[:50],
        "targetSource": new_source.get("name"),
    }
    if args.dry_run:
        print_json({"summary": summary, "payload": payload})
        return
    response = client.post(f"channels/{channel_id}/programming", payload)
    print_json({"summary": summary, "response": response})


def cmd_programs_search_by(
    client: TunarrClient,
    args: argparse.Namespace,
) -> None:
    if not args.title and not args.identifier:
        raise TunarrError("search-by requires --title and/or --identifier")
    library_id = resolve_library_id(client, args, args.library) if args.library else None
    programs = search_all(client, args, library_id, limit=args.limit)
    if args.identifier:
        wanted = args.identifier
        matches = [p for p in programs if any(i.get("id") == wanted for i in p.get("identifiers", []))]
    else:
        needle = args.title.strip().lower()
        matches = [p for p in programs if str(p.get("title", "")).strip().lower() == needle]
    print_json(
        [
            {
                "uuid": p.get("uuid"),
                "title": p.get("title"),
                "type": p.get("type"),
                "identifiers": p.get("identifiers"),
            }
            for p in matches
        ]
    )


def create_payload(args: argparse.Namespace, transcode_id: str) -> dict[str, Any]:
    start_time = args.start_time if args.start_time is not None else int(time.time() * 1000)
    return {
        "type": "new",
        "channel": {
            "disableFillerOverlay": False,
            "duration": 0,
            "groupTitle": args.group_title,
            "guideMinimumDuration": 30000,
            "icon": {"path": args.icon, "width": 0, "duration": 0, "position": "bottom-right"},
            "id": str(uuid.uuid4()),
            "name": args.name,
            "number": args.number,
            "offline": {"picture": "", "soundtrack": "", "mode": "pic"},
            "startTime": start_time,
            "stealth": False,
            "streamMode": args.stream_mode,
            "transcodeConfigId": transcode_id,
            "subtitlesEnabled": args.subtitles,
        },
    }


def cmd_version(client: TunarrClient, args: argparse.Namespace) -> None:
    print_json(client.get("version"))


def cmd_media_sources(client: TunarrClient, args: argparse.Namespace) -> None:
    if args.action != "list":
        raise TunarrError("usage: media-sources list")
    print_json(source_data(client, args))


def cmd_libraries(client: TunarrClient, args: argparse.Namespace) -> None:
    if args.action != "list":
        raise TunarrError("usage: libraries list")
    libraries = []
    for source in source_data(client, args):
        for library in source.get("libraries", []):
            libraries.append(
                {
                    "id": library.get("id"),
                    "name": library.get("name"),
                    "mediaType": library.get("mediaType"),
                    "enabled": library.get("enabled"),
                    "type": library.get("type"),
                    "externalKey": library.get("externalKey"),
                    "sourceId": source.get("id"),
                    "sourceName": source.get("name"),
                }
            )
    print_json(libraries)


def cmd_transcode_configs(client: TunarrClient, args: argparse.Namespace) -> None:
    if args.action != "list":
        raise TunarrError("usage: transcode-configs list")
    print_json(client.get("transcode_configs"))


def cmd_programs_search(client: TunarrClient, args: argparse.Namespace) -> None:
    library_id = resolve_library_id(client, args, args.library) if args.library else None
    print_json(search_programs(client, args, args.query, library_id, args.limit))


def cmd_channels_list(client: TunarrClient, args: argparse.Namespace) -> None:
    print_json(client.get("channels"))


def cmd_channels_get(client: TunarrClient, args: argparse.Namespace) -> None:
    print_json(client.get(f"channels/{resolve_channel_id(client, args.channel)}"))


def cmd_channels_programs(client: TunarrClient, args: argparse.Namespace) -> None:
    channel_id = resolve_channel_id(client, args.channel)
    query = urllib.parse.urlencode({"limit": args.limit, "offset": args.offset})
    print_json(client.get(f"channels/{channel_id}/programs?{query}"))


def cmd_channels_create(client: TunarrClient, args: argparse.Namespace) -> None:
    if args.query and not args.library:
        raise TunarrError("--library is required when --query is used")
    transcode_id = resolve_transcode_id(client, args.transcode_config)
    channel = create_payload(args, transcode_id)
    programming = None
    if args.query:
        library_id = resolve_library_id(client, args, args.library)
        programming = programming_payload(
            client, args, args.query, library_id, args.limit, args.append
        )
    if args.dry_run:
        output: dict[str, Any] = {"channel": channel}
        if programming is not None:
            output["programming"] = programming
        print_json(output)
        return

    channel_response = client.post("channels", channel)
    if programming is None:
        print_json(channel_response)
        return
    channel_id = channel_response.get("id") or channel_response.get("channel", {}).get("id")
    if not channel_id:
        raise TunarrError("channel creation succeeded but the API response did not contain an id")
    programming_response = client.post(f"channels/{channel_id}/programming", programming)
    print_json({"channel": channel_response, "programming": programming_response})


def cmd_channels_add_programs(client: TunarrClient, args: argparse.Namespace) -> None:
    if not args.library:
        raise TunarrError("--library is required")
    channel_id = resolve_channel_id(client, args.channel)
    library_id = resolve_library_id(client, args, args.library)
    programming = programming_payload(
        client, args, args.query, library_id, args.limit, args.append
    )
    if args.dry_run:
        print_json(programming)
        return
    print_json(client.post(f"channels/{channel_id}/programming", programming))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create and inspect Tunarr channels through its HTTP API."
    )
    parser.add_argument(
        "--url", default="http://tunarr.home", help="Tunarr base URL (default: http://tunarr.home)"
    )
    parser.add_argument(
        "--source-name",
        default="Plex In Cluster",
        help="default media source (default: Plex In Cluster)",
    )
    parser.add_argument(
        "--all-sources",
        dest="source_filter",
        action="store_false",
        default=True,
        help="disable the default media-source restriction",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    version = subparsers.add_parser("version")
    version.set_defaults(handler=cmd_version)

    media_sources = subparsers.add_parser("media-sources")
    media_sources_sub = media_sources.add_subparsers(dest="action", required=True)
    media_sources_sub.add_parser("list").set_defaults(handler=cmd_media_sources)

    libraries = subparsers.add_parser("libraries")
    libraries_sub = libraries.add_subparsers(dest="action", required=True)
    libraries_sub.add_parser("list").set_defaults(handler=cmd_libraries)

    transcodes = subparsers.add_parser("transcode-configs")
    transcodes_sub = transcodes.add_subparsers(dest="action", required=True)
    transcodes_sub.add_parser("list").set_defaults(handler=cmd_transcode_configs)

    programs = subparsers.add_parser("programs")
    programs_sub = programs.add_subparsers(dest="action", required=True)
    search = programs_sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--library")
    search.add_argument("--limit", type=positive_int, default=20)
    search.set_defaults(handler=cmd_programs_search)

    channels = subparsers.add_parser("channels")
    channels_sub = channels.add_subparsers(dest="action", required=True)
    channels_sub.add_parser("list").set_defaults(handler=cmd_channels_list)

    get_channel = channels_sub.add_parser("get")
    get_channel.add_argument("channel")
    get_channel.set_defaults(handler=cmd_channels_get)

    channel_programs = channels_sub.add_parser("programs")
    channel_programs.add_argument("channel")
    channel_programs.add_argument("--limit", type=positive_int, default=20)
    channel_programs.add_argument("--offset", type=int, default=0)
    channel_programs.set_defaults(handler=cmd_channels_programs)

    create = channels_sub.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--number", required=True, type=positive_int)
    create.add_argument("--library")
    create.add_argument("--query")
    create.add_argument("--limit", type=positive_int, default=20)
    create.add_argument("--group-title", default="tunarr")
    create.add_argument("--transcode-config")
    create.add_argument("--stream-mode", choices=STREAM_MODES, default="hls")
    create.add_argument("--subtitles", action="store_true")
    create.add_argument("--icon", default="")
    create.add_argument("--start-time", type=int)
    create.add_argument("--append", action="store_true")
    create.add_argument("--dry-run", action="store_true")
    create.set_defaults(handler=cmd_channels_create)

    add_programs = channels_sub.add_parser("add-programs")
    add_programs.add_argument("channel")
    add_programs.add_argument("--library", required=True)
    add_programs.add_argument("--query", required=True)
    add_programs.add_argument("--limit", type=positive_int, default=20)
    add_programs.add_argument("--append", action="store_true")
    add_programs.add_argument("--dry-run", action="store_true")
    add_programs.set_defaults(handler=cmd_channels_add_programs)

    verify = channels_sub.add_parser("verify")
    verify.add_argument("channel")
    verify.set_defaults(handler=cmd_channels_verify)

    convert = channels_sub.add_parser("convert")
    convert.add_argument("channel")
    convert.add_argument("--mode", choices=["manual", "time"], required=True)
    convert.add_argument("--limit", type=positive_int, default=20000)
    convert.add_argument("--dry-run", action="store_true")
    convert.set_defaults(handler=cmd_channels_convert)

    search_by = programs_sub.add_parser("search-by")
    search_by.add_argument("--title")
    search_by.add_argument("--identifier")
    search_by.add_argument("--library")
    search_by.add_argument("--limit", type=positive_int, default=20000)
    search_by.set_defaults(handler=cmd_programs_search_by)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    client = TunarrClient(args.url)
    try:
        args.handler(client, args)
    except TunarrError as error:
        print(f"tunarr: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
