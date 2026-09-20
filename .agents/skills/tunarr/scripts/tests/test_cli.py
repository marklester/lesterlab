"""Integration tests for the click CLI, driven through ``main(argv)``.

These exercise the real entry point end-to-end against the fake Tunarr
server: argument parsing, source/library/channel resolution, payload
construction, and exit codes. Output is captured with ``capsys`` because
``main`` prints JSON to ``sys.stdout`` and errors to ``sys.stderr``.
"""

from __future__ import annotations

import json

from tunarr_cli.cli import main

from conftest import (
    CHANNEL_ID,
    MOVIE_LIBRARY_ID,
    NEW_SOURCE_ID,
    OLD_SOURCE_ID,
    TV_LIBRARY_ID,
    make_programs,
)


def run_cli(capsys, *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def parse(out: str) -> object:
    return json.loads(out)


# ------------------------------------------------------------------ read-only


def test_version(fake_tunarr, capsys) -> None:
    code, out, _ = run_cli(capsys, "--url", fake_tunarr.url, "version")
    assert code == 0
    assert parse(out) == {"version": "1.3.15"}


def test_media_sources_list(fake_tunarr, capsys) -> None:
    code, out, _ = run_cli(capsys, "--url", fake_tunarr.url, "media-sources", "list")
    assert code == 0
    assert [s["name"] for s in parse(out)] == ["Plex", "Plex In Cluster"]


def test_libraries_list_includes_source_name(fake_tunarr, capsys) -> None:
    code, out, _ = run_cli(capsys, "--url", fake_tunarr.url, "libraries", "list")
    assert code == 0
    libs = parse(out)
    tv = next(l for l in libs if l["name"] == "TV Shows")
    assert tv["sourceName"] == "Plex In Cluster"
    assert tv["sourceId"] == NEW_SOURCE_ID


def test_transcode_configs_list(fake_tunarr, capsys) -> None:
    code, out, _ = run_cli(capsys, "--url", fake_tunarr.url, "transcode-configs", "list")
    assert code == 0
    assert parse(out)[0]["isDefault"] is True


def test_channels_list(fake_tunarr, capsys) -> None:
    code, out, _ = run_cli(capsys, "--url", fake_tunarr.url, "channels", "list")
    assert code == 0
    assert [c["number"] for c in parse(out)] == [1, 2]


def test_channels_get_by_number(fake_tunarr, capsys) -> None:
    code, out, _ = run_cli(capsys, "--url", fake_tunarr.url, "channels", "get", "1")
    assert code == 0
    assert parse(out)["id"] == CHANNEL_ID


def test_channels_get_by_name(fake_tunarr, capsys) -> None:
    code, out, _ = run_cli(capsys, "--url", fake_tunarr.url, "channels", "get", "Second Channel")
    assert code == 0
    assert parse(out)["number"] == 2


# ---------------------------------------------------------------------- search


def test_programs_search_scoped_to_source(fake_tunarr, capsys) -> None:
    state = fake_tunarr.server.state
    state["search_results"] = make_programs(5, NEW_SOURCE_ID, "m")
    code, out, _ = run_cli(
        capsys, "--url", fake_tunarr.url, "programs", "search", "Show", "--limit", "5"
    )
    assert code == 0
    assert len(parse(out)) == 5
    path, body = state["posts"][0]
    assert path == "/api/programs/search"
    assert body["query"]["query"] == "Show"
    assert body["mediaSourceId"] == NEW_SOURCE_ID


def test_programs_search_by_title(fake_tunarr, capsys) -> None:
    state = fake_tunarr.server.state
    state["search_results"] = make_programs(3, NEW_SOURCE_ID, "m")
    code, out, _ = run_cli(
        capsys, "--url", fake_tunarr.url, "programs", "search-by", "--title", "Show 001"
    )
    assert code == 0
    matches = parse(out)
    assert len(matches) == 1
    assert matches[0]["uuid"] == "m-1"


def test_programs_search_by_identifier(fake_tunarr, capsys) -> None:
    state = fake_tunarr.server.state
    state["search_results"] = make_programs(3, NEW_SOURCE_ID, "m")
    code, out, _ = run_cli(
        capsys, "--url", fake_tunarr.url, "programs", "search-by", "--identifier", "tmdb-2"
    )
    assert code == 0
    matches = parse(out)
    assert len(matches) == 1
    assert matches[0]["uuid"] == "m-2"


def test_programs_search_by_requires_filter(fake_tunarr, capsys) -> None:
    code, out, err = run_cli(capsys, "--url", fake_tunarr.url, "programs", "search-by")
    assert code == 1
    assert "search-by requires" in err


# --------------------------------------------------------------------- channels


def _programming(programs: dict, lineup: list, schedule=None) -> dict:
    return {"programs": programs, "lineup": lineup, "schedule": schedule}


def _program_entry(pid: str, title: str, source: str, state: str = "ok", tmdb: str | None = None) -> dict:
    identifiers = [{"id": tmdb, "type": "tmdb"}] if tmdb else []
    return {
        "type": "content",
        "duration": 60000,
        "id": pid,
        "program": {
            "uuid": pid,
            "title": title,
            "sortTitle": title,
            "type": "movie",
            "duration": 60000,
            "state": state,
            "mediaSourceId": source,
            "identifiers": identifiers,
        },
    }


def test_channels_verify_detects_bad_source_and_state(fake_tunarr, capsys) -> None:
    state = fake_tunarr.server.state
    state["programming"][CHANNEL_ID] = _programming(
        {
            "p1": _program_entry("p1", "Good", NEW_SOURCE_ID),
            "p2": _program_entry("p2", "WrongSource", OLD_SOURCE_ID),
            "p3": _program_entry("p3", "BadState", NEW_SOURCE_ID, state="error"),
        },
        [
            {"type": "content", "id": "p1", "duration": 60000},
            {"type": "content", "id": "p2", "duration": 60000},
            {"type": "content", "id": "p3", "duration": 60000},
        ],
    )
    code, out, _ = run_cli(capsys, "--url", fake_tunarr.url, "channels", "verify", "1")
    assert code == 0
    result = parse(out)
    assert result["lineupContent"] == 3
    assert result["uniquePrograms"] == 3
    assert result["badSource"] == 1
    assert result["badState"] == 1
    assert result["badSourceIds"] == ["p2"]
    assert result["badStateIds"] == ["p3"]


def test_channels_verify_clean(fake_tunarr, capsys) -> None:
    state = fake_tunarr.server.state
    state["programming"][CHANNEL_ID] = _programming(
        {"p1": _program_entry("p1", "Good", NEW_SOURCE_ID)},
        [{"type": "content", "id": "p1", "duration": 60000}],
    )
    code, out, _ = run_cli(capsys, "--url", fake_tunarr.url, "channels", "verify", "Test Channel")
    assert code == 0
    result = parse(out)
    assert result["badSource"] == 0
    assert result["badState"] == 0


def test_channels_add_programs_dry_run(fake_tunarr, capsys) -> None:
    state = fake_tunarr.server.state
    state["search_results"] = make_programs(3, NEW_SOURCE_ID, "m")
    code, out, _ = run_cli(
        capsys,
        "--url",
        fake_tunarr.url,
        "channels",
        "add-programs",
        "1",
        "--library",
        "Movies",
        "--query",
        "Show",
        "--limit",
        "3",
        "--dry-run",
    )
    assert code == 0
    result = parse(out)
    assert result["channel"] == CHANNEL_ID
    lineup = result["payload"]["lineup"]
    assert [e["id"] for e in lineup] == ["m-0", "m-1", "m-2"]
    assert result["payload"]["type"] == "manual"
    # dry-run must not POST programming
    assert not any(p[0].endswith("/programming") for p in state["posts"])


def test_channels_create_dry_run_payload_shape(fake_tunarr, capsys) -> None:
    code, out, _ = run_cli(
        capsys,
        "--url",
        fake_tunarr.url,
        "channels",
        "create",
        "--name",
        "New Channel",
        "--number",
        "42",
        "--stream-mode",
        "hls",
        "--dry-run",
    )
    assert code == 0
    result = parse(out)
    payload = result["payload"]
    assert payload["type"] == "new"
    channel = payload["channel"]
    assert channel["name"] == "New Channel"
    assert channel["number"] == 42
    assert channel["streamMode"] == "hls"
    assert channel["transcodeConfigId"] == "transcode-default"
    assert channel["groupTitle"] == "tunarr"
    assert channel["stealth"] is False


def test_channels_create_posts_and_seeds(fake_tunarr, capsys) -> None:
    state = fake_tunarr.server.state
    state["search_results"] = make_programs(2, NEW_SOURCE_ID, "m")
    code, out, _ = run_cli(
        capsys,
        "--url",
        fake_tunarr.url,
        "channels",
        "create",
        "--name",
        "New Channel",
        "--number",
        "42",
        "--query",
        "Show",
        "--limit",
        "2",
    )
    assert code == 0
    result = parse(out)
    assert result["channel"] == state["created_channel"]
    assert result["programming"]["type"] == "manual"
    # one POST to /api/channels and one to the new channel's programming
    paths = [p[0] for p in state["posts"]]
    assert "/api/channels" in paths
    assert f"/api/channels/{state['created_channel']}/programming" in paths


def test_channels_convert_manual_dry_run(fake_tunarr, capsys) -> None:
    state = fake_tunarr.server.state
    state["programming"][CHANNEL_ID] = _programming(
        {"old-1": _program_entry("old-1", "Movie A", OLD_SOURCE_ID, tmdb="tmdb-0")},
        [{"type": "content", "id": "old-1", "duration": 60000}],
    )
    state["search_results"] = make_programs(1, NEW_SOURCE_ID, "n")  # n-0 has tmdb-0
    code, out, _ = run_cli(
        capsys,
        "--url",
        fake_tunarr.url,
        "channels",
        "convert",
        "1",
        "--mode",
        "manual",
        "--dry-run",
    )
    assert code == 0
    result = parse(out)
    assert result["summary"]["mapped"] == 1
    assert result["summary"]["unmatched"] == 0
    lineup = result["payload"]["lineup"]
    assert lineup[0]["id"] == "n-0"
    assert result["payload"]["type"] == "manual"


def test_channels_convert_time_dry_run(fake_tunarr, capsys) -> None:
    state = fake_tunarr.server.state
    schedule = {
        "type": "time",
        "flexPreference": "distribute",
        "latenessMs": 0,
        "maxDays": 365,
        "padMs": 1,
        "period": "day",
        "timeZoneOffset": 300,
        "slots": [
            {"startTime": 0, "type": "show", "showId": "show-1", "order": "next", "id": "slot-1"},
            {"startTime": 1000, "type": "movie", "id": "old-1", "order": "next"},
            {"startTime": 2000, "type": "flex"},
        ],
    }
    state["programming"][CHANNEL_ID] = _programming(
        {"old-1": _program_entry("old-1", "Movie A", OLD_SOURCE_ID, tmdb="tmdb-0")},
        [],
        schedule=schedule,
    )
    state["all_programs"] = [
        {
            "uuid": "show-1",
            "title": "A Show",
            "sortTitle": "A Show",
            "type": "show",
            "duration": None,
            "identifiers": [{"id": "tmdb-0", "type": "tmdb"}],
        }
    ]
    state["search_results"] = make_programs(1, NEW_SOURCE_ID, "n")  # n-0 has tmdb-0
    code, out, _ = run_cli(
        capsys,
        "--url",
        fake_tunarr.url,
        "channels",
        "convert",
        "1",
        "--mode",
        "time",
        "--dry-run",
    )
    assert code == 0
    result = parse(out)
    payload = result["payload"]
    assert payload["type"] == "time"
    assert payload["programs"] == ["n-0"]
    slots = payload["schedule"]["slots"]
    assert slots[0]["showId"] == "n-0"  # show slot remapped
    assert slots[1]["id"] == "n-0"  # movie slot remapped
    assert slots[2]["type"] == "flex"  # flex slot untouched


def test_channels_convert_requires_programs(fake_tunarr, capsys) -> None:
    state = fake_tunarr.server.state
    state["programming"][CHANNEL_ID] = _programming({}, [])
    code, out, err = run_cli(
        capsys, "--url", fake_tunarr.url, "channels", "convert", "1", "--mode", "manual"
    )
    assert code == 1
    assert "no programs to convert" in err


def test_channels_convert_time_requires_schedule(fake_tunarr, capsys) -> None:
    state = fake_tunarr.server.state
    state["programming"][CHANNEL_ID] = _programming(
        {"old-1": _program_entry("old-1", "Movie A", OLD_SOURCE_ID, tmdb="tmdb-0")},
        [{"type": "content", "id": "old-1", "duration": 60000}],
        schedule=None,
    )
    state["search_results"] = make_programs(1, NEW_SOURCE_ID, "n")
    code, out, err = run_cli(
        capsys, "--url", fake_tunarr.url, "channels", "convert", "1", "--mode", "time"
    )
    assert code == 1
    assert "not time-programmed" in err


# ------------------------------------------------------------------- error paths


def test_unknown_source_name_errors(fake_tunarr, capsys) -> None:
    code, out, err = run_cli(
        capsys,
        "--url",
        fake_tunarr.url,
        "--source-name",
        "Does Not Exist",
        "channels",
        "verify",
        "1",
    )
    assert code == 1
    assert "not found" in err


def test_unreachable_server_returns_1(fake_tunarr, capsys) -> None:
    code, out, err = run_cli(capsys, "--url", "http://127.0.0.1:1", "version")
    assert code == 1
    assert "could not reach Tunarr" in err
