"""API tests with FastAPI's TestClient. All network sources are replaced (no network)."""

from datetime import UTC, datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from highground import main
from highground.cap import Warning

DISCLAIMER = (
    "Official MetService warnings and Civil Defence advice always come first. "
    "This is guidance, not a guarantee."
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(main, "get_river_status", None)
    monkeypatch.setattr(main, "_live_cache", {"at": None, "warnings": []})
    monkeypatch.setattr(main, "_river_cache", {"at": None, "status": None})
    return TestClient(main.app)  # not used as a context manager: startup lookups don't run


def test_replay_mode_has_red_paddocks_and_moves_herd_to_paddock_7(client):
    body = client.get("/api/assess", params={"mode": "replay"}).json()
    assert body["mode"] == "replay"
    assert body["warning"]["is_replay"] is True
    assert any(p["band"] == "red" for p in body["paddocks"])
    assert body["recommendation"]["message"].startswith("Move the herd to Paddock 7 by")
    assert body["plan"]["moves"][0]["action"] == body["recommendation"]["message"]


def test_calm_mode_has_no_red_paddocks(client):
    body = client.get("/api/assess", params={"mode": "calm"}).json()
    assert body["warning"] is None
    assert all(p["band"] != "red" for p in body["paddocks"])


@pytest.mark.parametrize("mode", ["calm", "replay", "live"])
def test_disclaimer_and_river_field_always_present(client, monkeypatch, mode):
    monkeypatch.setattr(main, "fetch_live_warnings", lambda: [])
    body = client.get("/api/assess", params={"mode": mode}).json()
    assert body["disclaimer"] == DISCLAIMER
    assert "river" in body


def test_live_mode_with_no_warnings_is_calm(client, monkeypatch):
    monkeypatch.setattr(main, "fetch_live_warnings", lambda: [])
    response = client.get("/api/assess", params={"mode": "live"})
    assert response.status_code == 200
    body = response.json()
    assert body["warning"] is None
    assert body["live_status"] == "ok"
    assert all(p["band"] != "red" for p in body["paddocks"])


def test_live_mode_feed_down_is_not_an_error(client, monkeypatch):
    def down():
        raise httpx.ConnectError("no route to MetService")

    monkeypatch.setattr(main, "fetch_live_warnings", down)
    response = client.get("/api/assess", params={"mode": "live"})
    assert response.status_code == 200
    assert response.json()["warning"] is None
    assert response.json()["live_status"] == "unavailable"


def test_live_warnings_are_cached(client, monkeypatch):
    calls = []

    def fetch():
        calls.append(1)
        return []

    monkeypatch.setattr(main, "fetch_live_warnings", fetch)
    client.get("/api/assess", params={"mode": "live"})
    client.get("/api/assess", params={"mode": "live"})
    assert len(calls) == 1


def test_live_mode_uses_a_warning_covering_the_farm(client, monkeypatch):
    now = datetime.now(UTC)
    w = Warning(
        identifier="test",
        event="Heavy Rain",
        headline="Test",
        level="orange",
        onset=now + timedelta(hours=6),
        expires=now + timedelta(hours=20),
        areas=[[(176.5, -39.5), (177.0, -39.5), (177.0, -39.8), (176.5, -39.8), (176.5, -39.5)]],
    )
    monkeypatch.setattr(main, "fetch_live_warnings", lambda: [w])
    body = client.get("/api/assess", params={"mode": "live"}).json()
    assert body["warning"]["level"] == "orange"
    assert body["warning"]["is_replay"] is False


class FakeRiver:
    site = "Ngaruroro River at Fernhill"
    level_m = 2.4
    observed_at = datetime(2026, 11, 21, 9, 0, tzinfo=timezone(timedelta(hours=13)))
    rising = True


def test_river_status_is_reported_and_used_when_param_not_given(client, monkeypatch):
    monkeypatch.setattr(main, "get_river_status", lambda timeout_s=5.0: FakeRiver())
    body = client.get("/api/assess", params={"mode": "replay"}).json()
    assert body["river"] == {
        "site": "Ngaruroro River at Fernhill",
        "level_m": 2.4,
        "observed_at": "2026-11-21T09:00:00+13:00",
        "rising": True,
    }
    assert body["river_rising"] is True
    assert all("river rising" in p["reason"] for p in body["paddocks"])


def test_explicit_river_rising_param_overrides_the_gauge(client, monkeypatch):
    monkeypatch.setattr(main, "get_river_status", lambda timeout_s=5.0: FakeRiver())
    body = client.get("/api/assess", params={"mode": "replay", "river_rising": "false"}).json()
    assert body["river_rising"] is False
    assert body["river"]["rising"] is True  # still shown, just not used for scoring


def test_river_gauge_failure_gives_null_river(client, monkeypatch):
    def broken(timeout_s=5.0):
        raise TimeoutError("gauge timed out")

    monkeypatch.setattr(main, "get_river_status", broken)
    body = client.get("/api/assess", params={"mode": "calm"}).json()
    assert body["river"] is None
    assert body["river_rising"] is False


def test_elevation_cache_is_applied_and_failures_are_ignored(monkeypatch):
    farm = main.load_farm()
    monkeypatch.setattr(main, "load_or_refresh_cache", lambda paddocks: {"p1": 19.5})
    assert main.apply_elevation_cache(farm) == 1
    assert farm.paddocks[0].elevation_m == 19.5

    def broken(paddocks):
        raise OSError("offline")

    monkeypatch.setattr(main, "load_or_refresh_cache", broken)
    assert main.apply_elevation_cache(farm) == 0
