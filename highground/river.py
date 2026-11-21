"""River level from the Hawke's Bay Regional Council (HBRC) Hilltop server.

Site: Ngaruroro River at Fernhill. Measurement: "Stage" (water level, mm) on Telemetry.hts.
Data: HBRC, CC BY 4.0. Readings arrive every 5 minutes in NZ local time.

Hilltop gotcha: spaces in the query must be sent as %20. If they are sent as "+"
(what httpx `params=` does), Hilltop reads the "+" as part of the site name and
answers "No data".

Everything here is optional for the demo: get_river_status() returns None on any failure.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

HILLTOP_URL = "https://data.hbrc.govt.nz/Envirodata/Telemetry.hts"
SITE = "Ngaruroro River at Fernhill"
MEASUREMENT = "Stage"
TIME_WINDOW = "PT2H/now"  # last two hours, about 24 readings

# "Rising" compares the latest reading with the one about an hour before it.
COMPARE_AGO = timedelta(hours=1)
COMPARE_TOLERANCE = timedelta(minutes=15)  # accept a reading 45-75 minutes earlier
# Readings wobble by a few mm from one 5-minute sample to the next, so ignore
# changes smaller than 1 cm when deciding "rising".
RISE_THRESHOLD_M = 0.01

UNIT_TO_M = {"mm": 0.001, "cm": 0.01, "m": 1.0}

try:
    NZ_TZ: ZoneInfo | None = ZoneInfo("Pacific/Auckland")
except ZoneInfoNotFoundError:  # very minimal systems: keep times naive
    NZ_TZ = None


@dataclass
class RiverStatus:
    site: str
    level_m: float
    observed_at: datetime
    rising: bool


def build_url(site: str = SITE, measurement: str = MEASUREMENT, window: str = TIME_WINDOW) -> str:
    """Hilltop GetData URL with spaces encoded as %20 (see module docstring)."""
    params = {
        "service": "Hilltop",
        "request": "GetData",
        "Site": site,
        "Measurement": measurement,
        "TimeInterval": window,
    }
    query = "&".join(f"{k}={quote(v, safe='/[]')}" for k, v in params.items())
    return f"{HILLTOP_URL}?{query}"


def parse_hilltop_xml(xml_text: str) -> list[tuple[datetime, float]]:
    """Parse a Hilltop GetData response into (time, level in metres), oldest first.

    Times are NZ local (made timezone-aware). Raises ValueError for an error
    response or anything we can't read.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"not XML: {e}") from e
    error = root.find("Error")
    if error is not None:
        raise ValueError(f"Hilltop error: {(error.text or '').strip()}")

    units = (root.findtext(".//ItemInfo/Units") or "").strip().lower()
    scale = UNIT_TO_M.get(units, 1.0)

    readings: list[tuple[datetime, float]] = []
    for e in root.iter("E"):
        t, v = e.findtext("T"), e.findtext("I1")
        if not t or not v:
            continue
        try:
            when = datetime.fromisoformat(t.strip())
            value = float(v) * scale
        except ValueError:
            continue  # skip a bad row rather than lose the whole series
        if when.tzinfo is None and NZ_TZ is not None:
            when = when.replace(tzinfo=NZ_TZ)
        readings.append((when, value))
    readings.sort(key=lambda r: r[0])
    return readings


def status_from_readings(
    readings: list[tuple[datetime, float]], site: str = SITE
) -> RiverStatus | None:
    """Latest level, and whether it is higher than the reading about an hour earlier."""
    if not readings:
        return None
    latest_t, latest_v = readings[-1]
    target = latest_t - COMPARE_AGO
    earlier = [r for r in readings if abs(r[0] - target) <= COMPARE_TOLERANCE]
    if earlier:
        _, before_v = min(earlier, key=lambda r: abs(r[0] - target))
        rising = latest_v - before_v >= RISE_THRESHOLD_M
    else:
        rising = False  # no reading an hour back: don't claim the river is rising
    return RiverStatus(site=site, level_m=round(latest_v, 3), observed_at=latest_t, rising=rising)


def get_river_status(timeout_s: float = 5.0) -> RiverStatus | None:
    """Live Ngaruroro at Fernhill level. Returns None on any failure (offline, bad data)."""
    try:
        response = httpx.get(build_url(), timeout=timeout_s)
        response.raise_for_status()
        return status_from_readings(parse_hilltop_xml(response.text))
    except Exception:  # the river gauge is a bonus, never a dependency of the demo
        return None
