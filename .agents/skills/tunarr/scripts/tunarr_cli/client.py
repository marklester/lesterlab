"""HTTP client for the Tunarr REST API.

The client is deliberately thin: it speaks JSON over HTTP and returns raw
dicts. Typed access happens in the model layer (``from_dict``) and in the
typed convenience methods below, which return dataclass instances.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from tunarr_cli.models import (
    Channel,
    Library,
    MediaSource,
    Program,
    Programming,
    TranscodeConfig,
)


class TunarrError(RuntimeError):
    """Raised for any Tunarr API or transport failure."""


class TunarrClient:
    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------ HTTP

    def request(self, method: str, path: str, payload: Any = None) -> Any:
        url = f"{self.base_url}/api/{path.lstrip('/')}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise TunarrError(f"Tunarr API returned HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise TunarrError(f"could not reach Tunarr at {url}: {error.reason}") from error
        if not body:
            return None
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise TunarrError(f"Tunarr returned invalid JSON from {url}") from error

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, payload: Any) -> Any:
        return self.request("POST", path, payload)

    # ------------------------------------------------- typed convenience API

    def version(self) -> dict[str, Any]:
        return self.get("version")

    def media_sources(self) -> list[MediaSource]:
        data = self.get("media-sources")
        return [MediaSource.from_dict(s) for s in data]

    def libraries(self) -> list[Library]:
        out: list[Library] = []
        for source in self.media_sources():
            for library in source.libraries:
                library.raw.setdefault("sourceId", source.id)
                library.raw.setdefault("sourceName", source.name)
                out.append(library)
        return out

    def transcode_configs(self) -> list[TranscodeConfig]:
        data = self.get("transcode_configs")
        return [TranscodeConfig.from_dict(c) for c in data]

    def channels(self) -> list[Channel]:
        data = self.get("channels")
        return [Channel.from_dict(c) for c in data]

    def channel_programming(self, channel_id: str) -> Programming:
        return Programming.from_dict(self.get(f"channels/{channel_id}/programming"))

    def program(self, program_id: str) -> Program:
        return Program.from_dict(self.get(f"programs/{program_id}"))

    def descendants(self, program_id: str) -> list[dict[str, Any]]:
        """Fetch the descendant programs of a show (its episodes).

        Each entry is a content entry: ``{"type": "content", "duration":
        <ms>, "id": <episode uuid>, "program": {...}}``. The ``id`` values
        are the episode uuids to pass in a time-schedule ``programs`` list.
        """
        return self.get(f"programs/{program_id}/descendants")

    def search_programs(
        self,
        query: str | None,
        library_id: str | None = None,
        media_source_id: str | None = None,
        limit: int = 20,
    ) -> list[Program]:
        """Search programs, following Tunarr's one-based pagination.

        Tunarr 1.3.15 caps this endpoint at 20 results per page, so the
        client requests 20 at a time and walks pages until ``limit`` results
        are collected or the server runs out of pages.
        """
        results: list[dict[str, Any]] = []
        page = 1
        while len(results) < limit:
            payload: dict[str, Any] = {
                "query": {"query": query, "sort": [{"field": "title", "direction": "asc"}]},
                "page": page,
                "limit": 20,
                "expandParents": True,
            }
            if library_id is not None:
                payload["libraryId"] = library_id
            if media_source_id is not None:
                payload["mediaSourceId"] = media_source_id
            response = self.post("programs/search", payload)
            results.extend(response.get("results", []))
            total_pages = int(response.get("totalPages", 1) or 1)
            if page >= total_pages:
                break
            page += 1
        return [Program.from_dict(r) for r in results[:limit]]

    def search_all(
        self,
        library_id: str | None = None,
        media_source_id: str | None = None,
        limit: int = 20000,
    ) -> list[Program]:
        """Fetch every program in a library/source, sorted by title."""
        return self.search_programs(
            None, library_id=library_id, media_source_id=media_source_id, limit=limit
        )
