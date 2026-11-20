"""Small, dependency-free geometry helpers (WGS84 lon/lat, metres)."""

from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_000.0

Point = tuple[float, float]  # (lon, lat) — GeoJSON order


def haversine_m(a: Point, b: Point) -> float:
    """Great-circle distance between two (lon, lat) points, in metres."""
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def centroid(ring: list[Point]) -> Point:
    """Area-weighted centroid of a simple polygon ring (lon, lat)."""
    pts = ring[:-1] if ring[0] == ring[-1] else ring
    area2 = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1], strict=True):
        cross = x0 * y1 - x1 * y0
        area2 += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if area2 == 0:
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    return (cx / (3 * area2), cy / (3 * area2))


def area_ha(ring: list[Point]) -> float:
    """Approximate polygon area in hectares (equirectangular projection; fine for farm scale)."""
    pts = ring[:-1] if ring[0] == ring[-1] else ring
    lat0 = math.radians(sum(p[1] for p in pts) / len(pts))
    xy = [
        (math.radians(lon) * EARTH_RADIUS_M * math.cos(lat0), math.radians(lat) * EARTH_RADIUS_M)
        for lon, lat in pts
    ]
    s = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(xy, xy[1:] + xy[:1], strict=True))
    return abs(s) / 2 / 10_000


def distance_to_line_m(p: Point, line: list[Point]) -> float:
    """Shortest distance from a point to a polyline, in metres (local flat approximation)."""
    lat0 = math.radians(p[1])

    def to_xy(q: Point) -> tuple[float, float]:
        return (
            math.radians(q[0] - p[0]) * EARTH_RADIUS_M * math.cos(lat0),
            math.radians(q[1] - p[1]) * EARTH_RADIUS_M,
        )

    best = math.inf
    for a, b in zip(line, line[1:], strict=False):
        (ax, ay), (bx, by) = to_xy(a), to_xy(b)
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        t = 0.0 if seg2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / seg2))
        best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def point_in_polygon(p: Point, ring: list[Point]) -> bool:
    """Ray-casting point-in-polygon test (lon, lat)."""
    x, y = p
    inside = False
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1], strict=True):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
            inside = not inside
    return inside
