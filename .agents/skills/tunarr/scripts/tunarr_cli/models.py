"""Typed data objects for Tunarr API payloads.

Every model wraps the raw JSON dict it was parsed from (``raw``) so that
``to_dict()`` round-trips losslessly: fields the CLI does not model are
preserved when a payload is sent back to the server. This matters for
``channels convert``, which rewrites a schedule and must not drop unknown
slot or schedule fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PLAYABLE_TYPES = {"movie", "episode", "track", "music_video", "other_video"}
STREAM_MODES = ("hls", "hls_slower", "mpegts", "hls_direct", "hls_direct_v2")


def _raw(data: dict[str, Any]) -> dict[str, Any]:
    return dict(data)


@dataclass
class Identifier:
    """An external identifier (tmdb, imdb, tvdb, plex-guid, ...).

    Tunarr attaches zero or more identifiers to every program. Cross-source
    matching (``channels convert``) prefers tmdb, then imdb, then tvdb; the
    plex-guid is source-specific and deliberately not used for matching.

    Fields:
        id: The identifier value (e.g. a TMDB id as a string).
        type: Identifier namespace (``tmdb``, ``imdb``, ``tvdb``,
            ``plex-guid``, ...).
    """

    id: str
    type: str
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Identifier":
        return cls(id=str(data.get("id", "")), type=str(data.get("type", "")), raw=_raw(data))

    def to_dict(self) -> dict[str, Any]:
        return self.raw or {"id": self.id, "type": self.type}


@dataclass
class Program:
    """A single program from a media source (movie, episode, track, ...).

    The ``programs`` map of a channel's programming is keyed by ``uuid``.
    ``state`` is the source's health for the item; verification counts
    entries whose state is not ``"ok"`` as bad.

    Fields:
        uuid: Tunarr-unique program id; the key in the programming map and
            the ``id`` referenced by lineup/schedule entries.
        title: Display title as reported by the source.
        sort_title: Title variant used for alphabetical ordering.
        type: Item kind (``movie``, ``episode``, ``show``, ``track``,
            ``music_video``, ``other_video``, ...). Playability is
            ``type in PLAYABLE_TYPES and duration is not None``.
        duration: Duration in milliseconds, or ``None`` for non-playable
            items such as shows.
        state: Source health (``"ok"`` when healthy).
        media_source_id: Id of the media source this program came from;
            used by verification to detect wrong-source content.
        identifiers: External identifiers (see :class:`Identifier`).
    """

    uuid: str
    title: str = ""
    sort_title: str = ""
    type: str = ""
    duration: int | None = None
    state: str = ""
    media_source_id: str = ""
    identifiers: list[Identifier] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Program":
        return cls(
            uuid=str(data.get("uuid", "")),
            title=str(data.get("title", "")),
            sort_title=str(data.get("sortTitle", "")),
            type=str(data.get("type", "")),
            duration=data.get("duration"),
            state=str(data.get("state", "")),
            media_source_id=str(data.get("mediaSourceId", "")),
            identifiers=[Identifier.from_dict(i) for i in data.get("identifiers", [])],
            raw=_raw(data),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.raw or {
            "uuid": self.uuid,
            "title": self.title,
            "sortTitle": self.sort_title,
            "type": self.type,
            "duration": self.duration,
            "state": self.state,
            "mediaSourceId": self.media_source_id,
            "identifiers": [i.to_dict() for i in self.identifiers],
        }

    def identifiers_by_type(self) -> dict[str, str]:
        """Map identifier type -> id, skipping empty entries."""
        return {i.type: i.id for i in self.identifiers if i.type and i.id}

    @property
    def is_playable(self) -> bool:
        return self.type in PLAYABLE_TYPES and self.duration is not None


@dataclass
class LineupEntry:
    """One entry of a channel's materialized lineup.

    The lineup is the fully expanded schedule Tunarr actually plays; it is
    the authoritative source for coverage verification (never the schedule
    slots, which are only the recipe).

    Fields:
        type: ``"content"`` (a real program) or ``"flex"`` (filler/overlay
            segment).
        id: Program uuid for ``content`` entries; ``None`` for flex.
        duration: Segment duration in milliseconds.
    """

    type: str
    id: str | None = None
    duration: int | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineupEntry":
        return cls(
            type=str(data.get("type", "")),
            id=data.get("id"),
            duration=data.get("duration"),
            raw=_raw(data),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.raw or {"type": self.type, "id": self.id, "duration": self.duration}


@dataclass
class Slot:
    """One slot of a time-based schedule (show, movie, flex, ...).

    Slots are the recipe Tunarr expands into the materialized lineup. Slot
    types include ``show`` (plays the show's episodes), ``movie`` (the slot's
    ``id`` is the movie's program uuid), ``smart-collection``, ``flex``,
    ``redirect``, ``filler``, and ``custom-show``.

    Fields:
        type: Slot kind (see above).
        start_time: Offset in milliseconds from the top of the hour.
        order: Playback order for multi-item slots (``next``, ``shuffle``,
            ``ordered_shuffle``, ``alphanumeric``, ``chronological``).
        id: For ``movie`` slots, the movie's program uuid; empty for most
            other types.
        show_id: Show program uuid for ``show`` slots.
    """

    type: str
    start_time: int = 0
    order: str = ""
    id: str = ""
    show_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Slot":
        return cls(
            type=str(data.get("type", "")),
            start_time=int(data.get("startTime", 0) or 0),
            order=str(data.get("order", "")),
            id=str(data.get("id", "")),
            show_id=str(data.get("showId", "")),
            raw=_raw(data),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.raw or {
            "type": self.type,
            "startTime": self.start_time,
            "order": self.order,
            "id": self.id,
            "showId": self.show_id,
        }


@dataclass
class Schedule:
    """A time-based schedule: a list of slots plus tuning parameters.

    This is the ``schedule`` half of a channel's programming (the other
    half being the ``programs`` map). ``channels convert`` rewrites the
    slots and re-POSTs the schedule; unknown fields survive via ``raw``.

    Fields:
        type: ``"time"`` for the standard time-based schedule.
        slots: The ordered list of :class:`Slot` entries.
    """

    type: str = "time"
    slots: list[Slot] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Schedule":
        return cls(
            type=str(data.get("type", "time")),
            slots=[Slot.from_dict(s) for s in data.get("slots", [])],
            raw=_raw(data),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.raw or {"type": self.type, "slots": [s.to_dict() for s in self.slots]}


@dataclass
class Programming:
    """A channel's programming: program map, materialized lineup, schedule.

    Returned by ``GET /api/channels/{id}/programming`` and (minus the
    materialized ``lineup``) re-POSTed by ``channels convert``.

    Fields:
        programs: Map of program uuid -> :class:`Program`. Only the programs
            actually referenced by the schedule appear here.
        lineup: The fully materialized schedule; verification of source
            health and coverage is computed from this list only.
        schedule: The time-based :class:`Schedule` (``None`` for manually
            built channels).
    """

    programs: dict[str, Program] = field(default_factory=dict)
    lineup: list[LineupEntry] = field(default_factory=list)
    schedule: Schedule | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Programming":
        programs = {
            str(pid): Program.from_dict(entry.get("program", {}))
            for pid, entry in data.get("programs", {}).items()
            if isinstance(entry, dict)
        }
        schedule_data = data.get("schedule")
        return cls(
            programs=programs,
            lineup=[LineupEntry.from_dict(e) for e in data.get("lineup", [])],
            schedule=Schedule.from_dict(schedule_data) if isinstance(schedule_data, dict) else None,
            raw=_raw(data),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.raw or {
            "programs": {pid: {"program": p.to_dict()} for pid, p in self.programs.items()},
            "lineup": [e.to_dict() for e in self.lineup],
            "schedule": self.schedule.to_dict() if self.schedule else None,
        }

    def content_ids(self) -> list[str]:
        """Ids of all ``content`` lineup entries, in lineup order."""
        return [str(e.id) for e in self.lineup if e.type == "content" and e.id is not None]


@dataclass
class Library:
    """A library (e.g. ``TV Shows``, ``Movies``) within a media source.

    Library arguments to the CLI may be either the ``id`` or the ``name``;
    name resolution is scoped to the selected media source.

    Fields:
        id: Library id; used as ``libraryId`` in search payloads.
        name: Display name (e.g. ``"TV Shows"``).
        media_type: Content kind (``tv``, ``movie``, ...).
        enabled: Whether the library is enabled in the source.
        type: Library type as reported by the source.
        external_key: Source-side key (e.g. the Plex section id).
    """

    id: str
    name: str = ""
    media_type: str = ""
    enabled: bool | None = None
    type: str = ""
    external_key: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Library":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            media_type=str(data.get("mediaType", "")),
            enabled=data.get("enabled"),
            type=str(data.get("type", "")),
            external_key=str(data.get("externalKey", "")),
            raw=_raw(data),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.raw or {
            "id": self.id,
            "name": self.name,
            "mediaType": self.media_type,
            "enabled": self.enabled,
            "type": self.type,
            "externalKey": self.external_key,
        }


@dataclass
class MediaSource:
    """A connected media source (e.g. the ``Plex In Cluster`` Plex server).

    Fields:
        id: Source id; programs carry it as ``media_source_id`` and search
            payloads take it as ``mediaSourceId``.
        name: Display name; the CLI's ``--source-name`` matches this.
        uri: Base URL of the backing server.
        libraries: The :class:`Library` entries under this source.
    """

    id: str
    name: str = ""
    uri: str = ""
    libraries: list[Library] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MediaSource":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            uri=str(data.get("uri", "")),
            libraries=[Library.from_dict(l) for l in data.get("libraries", [])],
            raw=_raw(data),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.raw or {
            "id": self.id,
            "name": self.name,
            "uri": self.uri,
            "libraries": [l.to_dict() for l in self.libraries],
        }


@dataclass
class Channel:
    """A Tunarr channel (one row of ``GET /api/channels``).

    Fields:
        id: Channel uuid; the path parameter for programming endpoints.
        name: Display name.
        number: Channel number (the CLI's positional channel argument
            matches this).
    """

    id: str
    name: str = ""
    number: int | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Channel":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            number=data.get("number"),
            raw=_raw(data),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.raw or {"id": self.id, "name": self.name, "number": self.number}


@dataclass
class TranscodeConfig:
    """A transcode profile (``GET /api/transcode_configs``).

    Channel creation requires a transcode config id; the CLI defaults to
    the profile flagged ``is_default``.

    Fields:
        id: Profile id.
        name: Display name.
        is_default: True for the source's default profile.
    """

    id: str
    name: str = ""
    is_default: bool = False
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TranscodeConfig":
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            is_default=bool(data.get("isDefault", False)),
            raw=_raw(data),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.raw or {"id": self.id, "name": self.name, "isDefault": self.is_default}
