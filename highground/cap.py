"""Parse Common Alerting Protocol (CAP 1.2) warnings, e.g. from MetService.

Live feed: https://alerts.metservice.com/cap/rss (an RSS list of links to CAP XML files).
Replay: data/replay_warning.xml, with its times shifted so onset is a few hours from "now".
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .geo import Point, point_in_polygon

NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}

LEVELS = ("none", "yellow", "orange", "red")


@dataclass
class Warning:
    identifier: str
    event: str
    headline: str
    level: str  # one of LEVELS
    onset: datetime
    expires: datetime
    areas: list[list[Point]] = field(default_factory=list)  # polygons as (lon, lat) rings
    instruction: str = ""
    is_replay: bool = False

    def covers(self, p: Point) -> bool:
        return any(point_in_polygon(p, ring) for ring in self.areas)


def _text(el: ET.Element | None, path: str) -> str:
    found = el.find(path, NS) if el is not None else None
    return (found.text or "").strip() if found is not None else ""


def _parse_polygon(text: str) -> list[Point]:
    """CAP polygons are 'lat,lon lat,lon ...'. Return (lon, lat) pairs."""
    pts = []
    for pair in text.split():
        lat, lon = (float(v) for v in pair.split(","))
        pts.append((lon, lat))
    return pts


def _level(info: ET.Element) -> str:
    """Map CAP fields to a colour level. MetService puts colour in parameters/event text."""
    blob = " ".join(
        [_text(info, "cap:event"), _text(info, "cap:headline")]
        + [_text(p, "cap:value") for p in info.findall("cap:parameter", NS)]
    ).lower()
    for level in ("red", "orange", "yellow"):
        if level in blob:
            return level
    severity = _text(info, "cap:severity").lower()
    return {"extreme": "red", "severe": "orange", "moderate": "yellow"}.get(severity, "yellow")


def parse_cap(xml_text: str) -> Warning:
    root = ET.fromstring(xml_text)
    info = root.find("cap:info", NS)
    if info is None:
        raise ValueError("CAP message has no <info> block")
    areas = [
        _parse_polygon(poly.text or "")
        for area in info.findall("cap:area", NS)
        for poly in area.findall("cap:polygon", NS)
        if poly.text
    ]
    return Warning(
        identifier=_text(root, "cap:identifier"),
        event=_text(info, "cap:event"),
        headline=_text(info, "cap:headline"),
        level=_level(info),
        onset=datetime.fromisoformat(_text(info, "cap:onset")),
        expires=datetime.fromisoformat(_text(info, "cap:expires")),
        areas=areas,
        instruction=_text(info, "cap:instruction"),
    )


def as_replay(warning: Warning, now: datetime, onset_in: timedelta = timedelta(hours=7)) -> Warning:
    """Shift a saved warning so it starts `onset_in` from now, keeping its duration."""
    duration = warning.expires - warning.onset
    onset = now + onset_in
    return Warning(
        identifier=warning.identifier,
        event=warning.event,
        headline=warning.headline,
        level=warning.level,
        onset=onset,
        expires=onset + duration,
        areas=warning.areas,
        instruction=warning.instruction,
        is_replay=True,
    )
