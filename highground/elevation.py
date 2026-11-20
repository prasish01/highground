"""Paddock elevation lookups via the Open Topo Data public API (NZ 8 m DEM).

API: https://api.opentopodata.org/v1/nzdem8m?locations=lat,lng|lat,lng
Public API limits: up to 100 locations per request and about 1 request per second, so
batch lookups and cache results. Credit: LINZ (CC BY 4.0) via Open Topo Data.
"""

from __future__ import annotations

import httpx

from .geo import Point

API_URL = "https://api.opentopodata.org/v1/nzdem8m"


def lookup_elevations(points: list[Point], timeout_s: float = 10.0) -> list[float | None]:
    """Return elevation (m) for each (lon, lat) point, or None where unavailable."""
    if not points:
        return []
    locations = "|".join(f"{lat},{lon}" for lon, lat in points[:100])
    response = httpx.get(API_URL, params={"locations": locations}, timeout=timeout_s)
    response.raise_for_status()
    return [r.get("elevation") for r in response.json().get("results", [])]
