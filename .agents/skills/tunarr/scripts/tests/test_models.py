"""Unit tests for the typed model layer (no HTTP involved)."""

from __future__ import annotations

from tunarr_cli.models import (
    Channel,
    Identifier,
    Library,
    LineupEntry,
    MediaSource,
    Program,
    Programming,
    Schedule,
    Slot,
    TranscodeConfig,
)


def test_program_round_trip_preserves_unknown_fields() -> None:
    data = {
        "uuid": "p1",
        "title": "Bluey",
        "sortTitle": "Bluey",
        "type": "episode",
        "duration": 1234,
        "state": "ok",
        "mediaSourceId": "src",
        "identifiers": [{"id": "tmdb-1", "type": "tmdb"}],
        "someUnknownField": "kept",
    }
    program = Program.from_dict(data)
    assert program.to_dict() == data
    assert program.is_playable
    assert program.identifiers_by_type() == {"tmdb": "tmdb-1"}


def test_program_not_playable_without_duration() -> None:
    program = Program.from_dict({"uuid": "p", "type": "movie", "duration": None})
    assert not program.is_playable


def test_program_not_playable_wrong_type() -> None:
    program = Program.from_dict({"uuid": "p", "type": "show", "duration": 100})
    assert not program.is_playable


def test_identifier_round_trip() -> None:
    data = {"id": "tt123", "type": "imdb"}
    assert Identifier.from_dict(data).to_dict() == data


def test_lineup_entry_round_trip() -> None:
    data = {"type": "content", "id": "p1", "duration": 60000, "extra": 1}
    entry = LineupEntry.from_dict(data)
    assert entry.to_dict() == data
    assert entry.id == "p1"


def test_slot_round_trip() -> None:
    data = {
        "startTime": 0,
        "type": "show",
        "showId": "show-1",
        "order": "next",
        "id": "slot-1",
        "direction": "forward",
    }
    slot = Slot.from_dict(data)
    assert slot.to_dict() == data
    assert slot.show_id == "show-1"
    assert slot.start_time == 0


def test_schedule_round_trip() -> None:
    data = {
        "type": "time",
        "flexPreference": "distribute",
        "latenessMs": 0,
        "maxDays": 365,
        "padMs": 1,
        "period": "day",
        "timeZoneOffset": 300,
        "slots": [{"startTime": 0, "type": "flex"}],
    }
    schedule = Schedule.from_dict(data)
    assert schedule.to_dict() == data
    assert len(schedule.slots) == 1


def test_programming_parses_program_map_and_lineup() -> None:
    data = {
        "programs": {
            "p1": {
                "type": "content",
                "duration": 60000,
                "id": "p1",
                "program": {"uuid": "p1", "title": "A", "type": "movie", "duration": 60000},
            },
            "p2": {
                "type": "content",
                "duration": 70000,
                "id": "p2",
                "program": {"uuid": "p2", "title": "B", "type": "movie", "duration": 70000},
            },
        },
        "lineup": [
            {"type": "content", "id": "p1", "duration": 60000},
            {"type": "flex", "duration": 1000},
            {"type": "content", "id": "p2", "duration": 70000},
        ],
        "schedule": None,
    }
    programming = Programming.from_dict(data)
    assert set(programming.programs) == {"p1", "p2"}
    assert programming.programs["p1"].title == "A"
    assert programming.content_ids() == ["p1", "p2"]
    assert programming.to_dict() == data


def test_programming_with_schedule() -> None:
    data = {
        "programs": {},
        "lineup": [],
        "schedule": {"type": "time", "slots": [{"startTime": 0, "type": "flex"}]},
    }
    programming = Programming.from_dict(data)
    assert programming.schedule is not None
    assert programming.schedule.slots[0].type == "flex"
    assert programming.to_dict() == data


def test_media_source_and_library_round_trip() -> None:
    data = {
        "id": "src",
        "name": "Plex In Cluster",
        "uri": "http://plex.plex",
        "libraries": [{"id": "lib", "name": "TV Shows", "mediaType": "tv"}],
    }
    source = MediaSource.from_dict(data)
    assert source.to_dict() == data
    assert source.libraries[0].name == "TV Shows"


def test_library_round_trip() -> None:
    data = {"id": "lib", "name": "Movies", "mediaType": "movie", "enabled": True}
    assert Library.from_dict(data).to_dict() == data


def test_channel_round_trip() -> None:
    data = {"id": "c1", "name": "Cartoons", "number": 1}
    channel = Channel.from_dict(data)
    assert channel.to_dict() == data
    assert channel.number == 1


def test_transcode_config_round_trip() -> None:
    data = {"id": "t1", "name": "Default", "isDefault": True}
    config = TranscodeConfig.from_dict(data)
    assert config.to_dict() == data
    assert config.is_default is True
