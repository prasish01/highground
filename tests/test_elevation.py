"""Tests for elevation caching. These never touch the network: httpx.get is faked."""

import json

import pytest

from highground import elevation
from highground.elevation import load_or_refresh_cache
from highground.risk import Paddock


def _paddock(pid: str, lon: float, elev: float) -> Paddock:
    d = 0.001
    ring = [(lon, -39.63), (lon + d, -39.63), (lon + d, -39.629), (lon, -39.629), (lon, -39.63)]
    return Paddock(id=pid, name=pid.upper(), ring=ring, elevation_m=elev)


PADDOCKS = [_paddock("p1", 176.720, 21.0), _paddock("p2", 176.722, 30.0)]


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise elevation.httpx.HTTPStatusError("bad", request=None, response=None)

    def json(self) -> dict:
        return self._payload


@pytest.fixture
def no_network(monkeypatch):
    """Fail loudly if a test reaches httpx.get without faking it."""

    def boom(*args, **kwargs):
        raise AssertionError("network used in a test")

    monkeypatch.setattr(elevation.httpx, "get", boom)


def fake_api(monkeypatch, values, calls=None):
    def fake_get(url, params, timeout):
        assert url == elevation.API_URL
        assert timeout == 10.0
        n = len(params["locations"].split("|"))
        if calls is not None:
            calls.append(n)
        return FakeResponse({"results": [{"elevation": v} for v in values[:n]], "status": "OK"})

    monkeypatch.setattr(elevation.httpx, "get", fake_get)


def test_lookup_writes_cache(tmp_path, monkeypatch):
    fake_api(monkeypatch, [33.44, 32.0])
    cache = tmp_path / "elevation_cache.json"
    result = load_or_refresh_cache(PADDOCKS, cache_path=cache)
    assert result == {"p1": 33.4, "p2": 32.0}
    saved = json.loads(cache.read_text())
    assert saved["elevations"] == result
    assert "LINZ" in saved["source"]


def test_uses_cache_without_network(tmp_path, no_network):
    cache = tmp_path / "elevation_cache.json"
    cache.write_text(json.dumps({"elevations": {"p1": 40.0, "p2": 41.5, "old": 1.0}}))
    assert load_or_refresh_cache(PADDOCKS, cache_path=cache) == {"p1": 40.0, "p2": 41.5}


def test_refresh_ignores_cache(tmp_path, monkeypatch):
    cache = tmp_path / "elevation_cache.json"
    cache.write_text(json.dumps({"elevations": {"p1": 1.0, "p2": 2.0}}))
    fake_api(monkeypatch, [50.0, 51.0])
    assert load_or_refresh_cache(PADDOCKS, cache_path=cache, refresh=True) == {
        "p1": 50.0,
        "p2": 51.0,
    }


def test_cache_missing_a_paddock_triggers_lookup(tmp_path, monkeypatch):
    cache = tmp_path / "elevation_cache.json"
    cache.write_text(json.dumps({"elevations": {"p1": 1.0}}))
    fake_api(monkeypatch, [50.0, 51.0])
    assert load_or_refresh_cache(PADDOCKS, cache_path=cache)["p2"] == 51.0


def test_network_failure_falls_back(tmp_path, monkeypatch):
    def offline(*args, **kwargs):
        raise elevation.httpx.ConnectError("Wi-Fi off")

    monkeypatch.setattr(elevation.httpx, "get", offline)
    cache = tmp_path / "elevation_cache.json"
    assert load_or_refresh_cache(PADDOCKS, cache_path=cache) == {"p1": 21.0, "p2": 30.0}
    assert not cache.exists()


def test_http_error_falls_back(tmp_path, monkeypatch):
    monkeypatch.setattr(elevation.httpx, "get", lambda *a, **k: FakeResponse({}, status=429))
    result = load_or_refresh_cache(PADDOCKS, cache_path=tmp_path / "c.json")
    assert result == {"p1": 21.0, "p2": 30.0}


def test_null_elevation_falls_back(tmp_path, monkeypatch):
    fake_api(monkeypatch, [33.0, None])
    result = load_or_refresh_cache(PADDOCKS, cache_path=tmp_path / "c.json")
    assert result == {"p1": 21.0, "p2": 30.0}


def test_corrupt_cache_falls_back(tmp_path, no_network):
    cache = tmp_path / "elevation_cache.json"
    cache.write_text("{not json")
    # Cache is unreadable and the lookup "fails" (no_network raises): fallback values.
    assert load_or_refresh_cache(PADDOCKS, cache_path=cache) == {"p1": 21.0, "p2": 30.0}


def test_batches_of_100(tmp_path, monkeypatch):
    monkeypatch.setattr(elevation.time, "sleep", lambda s: None)
    many = [_paddock(f"p{i}", 176.72 + i * 0.00001, 20.0) for i in range(150)]
    calls: list[int] = []
    fake_api(monkeypatch, [10.0] * 150, calls)
    result = load_or_refresh_cache(many, cache_path=tmp_path / "c.json")
    assert calls == [100, 50]
    assert len(result) == 150


def test_unwritable_cache_still_returns_values(tmp_path, monkeypatch):
    fake_api(monkeypatch, [33.0, 32.0])
    cache = tmp_path / "missing_dir" / "c.json"
    assert load_or_refresh_cache(PADDOCKS, cache_path=cache) == {"p1": 33.0, "p2": 32.0}


def test_saved_cache_covers_sample_farm(no_network):
    """The committed cache lets the demo use real LINZ elevations with Wi-Fi off."""
    from highground.farm import load_farm

    farm = load_farm()
    assert (elevation.DATA_DIR / "elevation_cache.json").exists()
    result = load_or_refresh_cache(farm.paddocks)
    assert set(result) == {p.id for p in farm.paddocks}
    assert all(0 < v < 200 for v in result.values())
