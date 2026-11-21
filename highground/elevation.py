"""Paddock elevation lookups via the Open Topo Data public API (NZ 8 m DEM).

API: https://api.opentopodata.org/v1/nzdem8m?locations=lat,lng|lat,lng
Public API limits: up to 100 locations per request and about 1 request per second, so
batch lookups and cache results. Credit: LINZ (CC BY 4.0) via Open Topo Data.

The demo must work offline, so `load_or_refresh_cache` reads a saved cache first and
falls back to the elevations already in the farm GeoJSON if anything goes wrong.
"""

from __future__ import annotations

import contextlib
import json
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from .geo import Point

if TYPE_CHECKING:
    from .risk import Paddock

API_URL = "https://api.opentopodata.org/v1/nzdem8m"
DATASET = "nzdem8m"
MAX_POINTS = 100  # Open Topo Data public API limit per request
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def lookup_elevations(points: list[Point], timeout_s: float = 10.0) -> list[float | None]:
    """Return elevation (m) for each (lon, lat) point, or None where unavailable."""
    if not points:
        return []
    locations = "|".join(f"{lat},{lon}" for lon, lat in points[:MAX_POINTS])
    response = httpx.get(API_URL, params={"locations": locations}, timeout=timeout_s)
    response.raise_for_status()
    return [r.get("elevation") for r in response.json().get("results", [])]


def _fallback(paddocks: Sequence[Paddock]) -> dict[str, float]:
    """The elevations already in the farm file (placeholders for the sample farm)."""
    return {p.id: float(p.elevation_m) for p in paddocks}


def _read_cache(cache_path: Path, ids: set[str]) -> dict[str, float] | None:
    """Return cached elevations if the cache covers every paddock, else None."""
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        cached = {k: float(v) for k, v in data["elevations"].items()}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None
    if not ids <= cached.keys():
        return None  # paddocks changed since the cache was written
    return {k: cached[k] for k in ids}


def _write_cache(cache_path: Path, elevations: dict[str, float]) -> None:
    payload = {
        "source": f"Open Topo Data {DATASET} (LINZ, CC BY 4.0), paddock centroids",
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "elevations": elevations,
    }
    cache_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_or_refresh_cache(
    paddocks: Sequence[Paddock],
    cache_path: Path = DATA_DIR / "elevation_cache.json",
    refresh: bool = False,
) -> dict[str, float]:
    """Map paddock id -> elevation (m) at its centroid. Never raises.

    1. Unless `refresh`, use the cache file if it covers every paddock.
    2. Otherwise look up centroids (batches of 100, 10 s timeout) and write the cache.
    3. On any failure, return each paddock's existing `elevation_m`.
    """
    try:
        paddocks = list(paddocks)
        fallback = _fallback(paddocks)
        if not refresh:
            cached = _read_cache(Path(cache_path), set(fallback))
            if cached is not None:
                return cached

        elevations: dict[str, float] = {}
        for start in range(0, len(paddocks), MAX_POINTS):
            if start:
                time.sleep(1.0)  # public API allows about 1 request per second
            batch = paddocks[start : start + MAX_POINTS]
            values = lookup_elevations([p.centre for p in batch], timeout_s=10.0)
            if len(values) != len(batch) or any(v is None for v in values):
                return fallback  # partial answers are not trusted
            for p, v in zip(batch, values, strict=True):
                elevations[p.id] = round(float(v), 1)

        # Still use the fresh values even if we can't save them.
        with contextlib.suppress(OSError):
            _write_cache(Path(cache_path), elevations)
        return elevations
    except Exception:  # the demo must never crash on elevation
        try:
            return _fallback(paddocks)
        except Exception:
            return {}
