"""Integration tests for TunarrClient against the fake Tunarr server."""

from __future__ import annotations

from tunarr_cli.client import TunarrClient, TunarrError

from conftest import (
    CHANNEL_ID,
    DEFAULT_TRANSCODE_ID,
    MOVIE_LIBRARY_ID,
    NEW_SOURCE_ID,
    OLD_SOURCE_ID,
    TV_LIBRARY_ID,
    make_programs,
)


def test_version(fake_tunarr) -> None:
    client = TunarrClient(fake_tunarr.url)
    assert client.version() == {"version": "1.3.15"}


def test_media_sources_and_libraries(fake_tunarr) -> None:
    client = TunarrClient(fake_tunarr.url)
    sources = client.media_sources()
    assert [s.name for s in sources] == ["Plex", "Plex In Cluster"]

    libraries = client.libraries()
    assert len(libraries) == 2
    tv = next(l for l in libraries if l.name == "TV Shows")
    assert tv.id == TV_LIBRARY_ID
    assert tv.raw["sourceId"] == NEW_SOURCE_ID
    assert tv.raw["sourceName"] == "Plex In Cluster"


def test_transcode_configs(fake_tunarr) -> None:
    client = TunarrClient(fake_tunarr.url)
    configs = client.transcode_configs()
    assert configs[0].id == DEFAULT_TRANSCODE_ID
    assert configs[0].is_default is True


def test_channels(fake_tunarr) -> None:
    client = TunarrClient(fake_tunarr.url)
    channels = client.channels()
    assert [c.number for c in channels] == [1, 2]


def test_channel_programming(fake_tunarr) -> None:
    state = fake_tunarr.server.state
    state["programming"][CHANNEL_ID] = {
        "programs": {
            "p1": {
                "type": "content",
                "duration": 60000,
                "id": "p1",
                "program": {"uuid": "p1", "title": "A", "type": "movie", "duration": 60000},
            }
        },
        "lineup": [{"type": "content", "id": "p1", "duration": 60000}],
        "schedule": None,
    }
    client = TunarrClient(fake_tunarr.url)
    programming = client.channel_programming(CHANNEL_ID)
    assert programming.content_ids() == ["p1"]
    assert programming.programs["p1"].title == "A"


def test_program_detail(fake_tunarr) -> None:
    state = fake_tunarr.server.state
    state["all_programs"] = [
        {"uuid": "show-1", "title": "A Show", "type": "show", "duration": None}
    ]
    client = TunarrClient(fake_tunarr.url)
    program = client.program("show-1")
    assert program.title == "A Show"


def test_search_pagination_walks_pages(fake_tunarr) -> None:
    """The client must request 20/page and walk pages until limit is met."""
    state = fake_tunarr.server.state
    state["search_results"] = make_programs(45, NEW_SOURCE_ID, "m")
    client = TunarrClient(fake_tunarr.url)
    programs = client.search_programs("Show", limit=45)
    assert len(programs) == 45
    assert programs[0].uuid == "m-0"
    # 45 results at 20/page means 3 search requests.
    search_posts = [p for p in state["posts"] if p[0] == "/api/programs/search"]
    assert len(search_posts) == 3
    pages = [body["page"] for _, body in search_posts]
    assert pages == [1, 2, 3]
    assert all(body["limit"] == 20 for _, body in search_posts)


def test_search_respects_limit(fake_tunarr) -> None:
    state = fake_tunarr.server.state
    state["search_results"] = make_programs(45, NEW_SOURCE_ID, "m")
    client = TunarrClient(fake_tunarr.url)
    programs = client.search_programs("Show", limit=25)
    assert len(programs) == 25
    search_posts = [p for p in state["posts"] if p[0] == "/api/programs/search"]
    assert len(search_posts) == 2  # 20 + 5


def test_search_all_uses_null_query(fake_tunarr) -> None:
    state = fake_tunarr.server.state
    state["search_results"] = make_programs(10, NEW_SOURCE_ID, "m")
    client = TunarrClient(fake_tunarr.url)
    programs = client.search_all(library_id=MOVIE_LIBRARY_ID, limit=10)
    assert len(programs) == 10
    path, body = state["posts"][0]
    assert path == "/api/programs/search"
    assert body["query"]["query"] is None
    assert body["libraryId"] == MOVIE_LIBRARY_ID
    assert body["expandParents"] is True


def test_http_error_raises_tunarr_error(fake_tunarr) -> None:
    client = TunarrClient(fake_tunarr.url)
    try:
        client.channel_programming("missing")
    except TunarrError as error:
        assert "HTTP 404" in str(error)
    else:
        raise AssertionError("expected TunarrError")


def test_unreachable_server_raises_tunarr_error() -> None:
    client = TunarrClient("http://127.0.0.1:1", timeout=2.0)
    try:
        client.version()
    except TunarrError as error:
        assert "could not reach Tunarr" in str(error)
    else:
        raise AssertionError("expected TunarrError")
