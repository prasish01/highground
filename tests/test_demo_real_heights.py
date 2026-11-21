"""The demo moment must survive real LINZ heights (no network: the saved cache is used).

Replay warning + cached heights -> some red paddocks, a green one, and a move to a
paddock with water.
"""

import statistics
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from highground import elevation
from highground.cap import as_replay, parse_cap
from highground.farm import DATA_DIR, load_farm
from highground.geo import point_in_polygon
from highground.risk import recommend, score_paddock


@pytest.fixture
def no_network(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("network used in a test")

    monkeypatch.setattr(elevation.httpx, "get", boom)


@pytest.fixture
def farm():
    return load_farm()


@pytest.fixture
def cached(farm, no_network):
    assert (DATA_DIR / "elevation_cache.json").exists()
    heights = elevation.load_or_refresh_cache(farm.paddocks)
    return [replace(p, elevation_m=heights[p.id]) for p in farm.paddocks]


@pytest.fixture
def replay():
    xml = (DATA_DIR / "replay_warning.xml").read_text(encoding="utf-8")
    return as_replay(parse_cap(xml), now=datetime(2026, 11, 21, 9, 0, tzinfo=UTC))


def _assess(farm, paddocks, warning, river_rising=False):
    risks = [
        score_paddock(p, farm.river, farm.river_elevation_m, warning, river_rising)
        for p in paddocks
    ]
    rec = recommend(paddocks, risks, farm.herd_size, farm.ha_per_cow, warning)
    return risks, rec


@pytest.mark.parametrize("river_rising", [False, True])
def test_demo_has_red_and_green_and_a_watered_move(farm, cached, replay, river_rising):
    risks, rec = _assess(farm, cached, replay, river_rising)
    bands = [r.band for r in risks]
    assert bands.count("red") >= 2, bands
    assert bands.count("green") >= 1, bands
    assert rec is not None
    assert {p.id: p for p in cached}[rec.paddock_id].has_water
    assert rec.message.startswith("Move the herd to ")


def test_red_paddocks_are_the_ones_nearest_the_river(farm, cached, replay):
    risks, rec = _assess(farm, cached, replay)
    red = {r.paddock_id for r in risks if r.band == "red"}
    assert red <= {"p1", "p2", "p3"}
    assert rec.name == "Paddock 7"


def test_cached_heights_match_the_geojson(farm, cached):
    """Offline (GeoJSON) and cached runs must give the same answer."""
    for original, cache in zip(farm.paddocks, cached, strict=True):
        assert cache.elevation_m == pytest.approx(original.elevation_m, abs=0.05)


def test_river_height_is_median_of_river_points(farm):
    points = farm.geojson["properties"]["river_points"]
    assert len(points) >= 5
    median = statistics.median(p["elevation_m"] for p in points)
    assert farm.river_elevation_m == pytest.approx(median, abs=0.05)


def test_river_does_not_run_through_any_paddock(farm):
    river = farm.river
    samples = [
        (x0 + (x1 - x0) * t / 50, y0 + (y1 - y0) * t / 50)
        for (x0, y0), (x1, y1) in zip(river, river[1:], strict=False)
        for t in range(51)
    ]
    for p in farm.paddocks:
        assert not any(point_in_polygon(s, p.ring) for s in samples), p.id


def test_farm_basics_kept(farm):
    assert [p.id for p in farm.paddocks] == [f"p{i}" for i in range(1, 10)]
    assert [p.name for p in farm.paddocks] == [f"Paddock {i}" for i in range(1, 10)]
    assert [p.id for p in farm.paddocks if not p.has_water] == ["p8"]
    assert farm.herd_size == 300 and farm.ha_per_cow == 0.02
    assert "FICTIONAL" in farm.name.upper() or "FICTIONAL" in farm.geojson["properties"]["note"]
    for p in farm.paddocks:
        assert p.area_ha == pytest.approx(9, abs=0.5)


def test_calm_day_is_all_green(farm, cached):
    risks, _ = _assess(farm, cached, None)
    assert {r.band for r in risks} == {"green"}
