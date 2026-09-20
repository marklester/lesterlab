"""Shared fixtures: a fake Tunarr HTTP server for integration tests.

The fake server implements just enough of the Tunarr REST API (version,
media-sources, transcode_configs, channels, channel programming, program
detail, and the paginated programs/search endpoint) for the CLI and client
to be exercised end-to-end over real HTTP without a live Tunarr instance.

All POST bodies are recorded in ``server.state["posts"]`` so tests can
assert on exactly what the CLI would have sent to the server.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from typing import Any

import sys
from pathlib import Path

import pytest

# Make the tunarr_cli package importable regardless of pytest's rootdir.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

OLD_SOURCE_ID = "old-source"
NEW_SOURCE_ID = "new-source"
TV_LIBRARY_ID = "tv-library"
MOVIE_LIBRARY_ID = "movie-library"
DEFAULT_TRANSCODE_ID = "transcode-default"

CHANNEL_ID = "channel-1"
CHANNEL_2_ID = "channel-2"


def make_programs(n: int, source_id: str, prefix: str) -> list[dict[str, Any]]:
    """Generate ``n`` movie programs with tmdb identifiers tmdb-0..tmdb-n-1."""
    return [
        {
            "uuid": f"{prefix}-{i}",
            "title": f"Show {i:03d}",
            "sortTitle": f"Show {i:03d}",
            "type": "movie",
            "duration": 600000 + i,
            "state": "ok",
            "mediaSourceId": source_id,
            "identifiers": [{"id": f"tmdb-{i}", "type": "tmdb"}],
        }
        for i in range(n)
    ]


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: Any) -> None:  # silence request logging
        pass

    def _send(self, code: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        state: dict[str, Any] = self.server.state  # type: ignore[attr-defined]
        path = self.path
        if path == "/api/version":
            self._send(200, {"version": "1.3.15"})
        elif path == "/api/media-sources":
            self._send(200, state["media_sources"])
        elif path == "/api/transcode_configs":
            self._send(200, state["transcode_configs"])
        elif path == "/api/channels":
            self._send(200, state["channels"])
        elif path.startswith("/api/channels/") and path.endswith("/programming"):
            cid = path.split("/")[3]
            if cid in state["programming"]:
                self._send(200, state["programming"][cid])
            else:
                self._send(404, {"error": "channel not found"})
        elif path.startswith("/api/programs/") and path.endswith("/descendants"):
            pid = path.split("/")[3]
            self._send(200, state["descendants"].get(pid, []))
        elif path.startswith("/api/programs/"):
            pid = path.rsplit("/", 1)[1]
            for program in state["all_programs"]:
                if program["uuid"] == pid:
                    self._send(200, program)
                    return
            self._send(404, {"error": "program not found"})
        else:
            self._send(404, {"error": f"no route for {path}"})

    def do_POST(self) -> None:
        state: dict[str, Any] = self.server.state  # type: ignore[attr-defined]
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"null")
        state["posts"].append((self.path, body))
        if self.path == "/api/programs/search":
            results = state["search_results"]
            page = int(body.get("page", 1))
            limit = int(body.get("limit", 20))
            start = (page - 1) * limit
            chunk = results[start : start + limit]
            total_pages = max(1, -(-len(results) // limit))
            self._send(
                200,
                {"results": chunk, "totalPages": total_pages, "total": len(results)},
            )
        elif self.path == "/api/channels":
            channel_id = body["channel"]["id"]
            state["created_channel"] = channel_id
            self._send(200, {"id": channel_id})
        elif self.path.startswith("/api/channels/") and self.path.endswith("/programming"):
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error": f"no route for {self.path}"})


@pytest.fixture()
def fake_tunarr():
    """Start a fake Tunarr server on a random localhost port.

    Yields ``SimpleNamespace(url, server)``; tests mutate ``server.state``
    (programming, search_results, all_programs, ...) before running the CLI.
    """
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.state = {  # type: ignore[attr-defined]
        "media_sources": [
            {
                "id": OLD_SOURCE_ID,
                "name": "Plex",
                "uri": "http://plex.old",
                "libraries": [],
            },
            {
                "id": NEW_SOURCE_ID,
                "name": "Plex In Cluster",
                "uri": "http://plex.plex",
                "libraries": [
                    {
                        "id": TV_LIBRARY_ID,
                        "name": "TV Shows",
                        "mediaType": "tv",
                        "enabled": True,
                        "type": "Plex",
                        "externalKey": "tv",
                    },
                    {
                        "id": MOVIE_LIBRARY_ID,
                        "name": "Movies",
                        "mediaType": "movie",
                        "enabled": True,
                        "type": "Plex",
                        "externalKey": "movie",
                    },
                ],
            },
        ],
        "transcode_configs": [
            {"id": DEFAULT_TRANSCODE_ID, "name": "Default", "isDefault": True},
            {"id": "transcode-other", "name": "Other", "isDefault": False},
        ],
        "channels": [
            {"id": CHANNEL_ID, "name": "Test Channel", "number": 1},
            {"id": CHANNEL_2_ID, "name": "Second Channel", "number": 2},
        ],
        "programming": {},
        "all_programs": [],
        "search_results": [],
        "descendants": {},
        "posts": [],
        "created_channel": None,
    }
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield SimpleNamespace(
        url=f"http://127.0.0.1:{server.server_address[1]}", server=server
    )
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
