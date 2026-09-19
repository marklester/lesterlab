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
