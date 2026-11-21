"""API tests with FastAPI's TestClient. All network sources are replaced (no network)."""

from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

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


def _has_water(client, paddock_id):
    farm = client.get("/api/farm").json()
    (props,) = [
        f["properties"] for f in farm["features"] if f["properties"].get("id") == paddock_id
    ]
    return props.get("has_water", True)


def test_replay_mode_has_red_paddocks_and_moves_herd_to_a_watered_paddock(client):
    # Deliberately not tied to a paddock number: the sample farm may be redrawn.
    body = client.get("/api/assess", params={"mode": "replay"}).json()
    rec = body["recommendation"]
    assert body["mode"] == "replay"
    assert body["warning"]["is_replay"] is True
    assert any(p["band"] == "red" for p in body["paddocks"])
    assert rec["message"].startswith("Move the herd to Paddock ")
    assert _has_water(client, rec["paddock_id"]) is True
    assert rec["message"] == f"Move the herd to {rec['name']} by {rec['deadline_label']}"
    assert body["plan"]["moves"][0]["action"] == rec["message"]


def test_replay_times_are_nz_time_when_now_is_utc(client, monkeypatch):
    # Server "now" in UTC: 00:00 UTC = 1pm NZDT, onset 8pm NZDT, move by 5pm NZDT.
    monkeypatch.setattr(main, "now_nz", lambda: datetime(2026, 11, 21, 0, 0, tzinfo=UTC))
    body = client.get("/api/assess", params={"mode": "replay"}).json()
    assert body["recommendation"]["deadline_label"] == "5pm"
    assert body["recommendation"]["message"].endswith(" by 5pm")
    assert body["recommendation"]["deadline"] == "2026-11-21T17:00:00+13:00"
    assert body["warning"]["onset_label"] == "8pm"
    assert body["warning"]["onset"] == "2026-11-21T20:00:00+13:00"


def test_now_nz_is_auckland_time():
    assert main.now_nz().tzinfo == ZoneInfo("Pacific/Auckland")


def test_calm_mode_has_no_deadline_label(client):
    rec = client.get("/api/assess", params={"mode": "calm"}).json()["recommendation"]
    assert rec["deadline"] is None
    assert rec["deadline_label"] is None


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


def test_river_status_is_reported_and_used_in_live_mode(client, monkeypatch):
    monkeypatch.setattr(main, "fetch_live_warnings", lambda: [])
    monkeypatch.setattr(main, "get_river_status", lambda timeout_s=5.0: FakeRiver())
    body = client.get("/api/assess", params={"mode": "live"}).json()
    assert body["river"] == {
        "site": "Ngaruroro River at Fernhill",
        "level_m": 2.4,
        "observed_at": "2026-11-21T09:00:00+13:00",
        "rising": True,
    }
    assert body["river_rising"] is True
    assert all("river rising" in p["reason"] for p in body["paddocks"])


def bands(body):
    return {p["paddock_id"]: (p["band"], p["score"]) for p in body["paddocks"]}


def test_replay_ignores_a_rising_live_gauge(client, monkeypatch):
    # Issue #9: the rehearsed replay must look the same whatever the real river is doing.
    steady = client.get("/api/assess", params={"mode": "replay"}).json()
    monkeypatch.setattr(main, "_river_cache", {"at": None, "status": None})
    monkeypatch.setattr(main, "get_river_status", lambda timeout_s=5.0: FakeRiver())
    body = client.get("/api/assess", params={"mode": "replay"}).json()
    assert bands(body) == bands(steady)
    assert body["recommendation"]["message"] == steady["recommendation"]["message"]
    assert body["river_rising"] is False
    assert body["river"]["rising"] is True  # still shown for display
    assert not any("river rising" in p["reason"] for p in body["paddocks"])


def test_calm_ignores_a_rising_live_gauge(client, monkeypatch):
    monkeypatch.setattr(main, "get_river_status", lambda timeout_s=5.0: FakeRiver())
    body = client.get("/api/assess", params={"mode": "calm"}).json()
    assert body["river_rising"] is False


def test_live_mode_uses_the_real_gauge(client, monkeypatch):
    monkeypatch.setattr(main, "fetch_live_warnings", lambda: [])
    monkeypatch.setattr(main, "get_river_status", lambda timeout_s=5.0: FakeRiver())
    body = client.get("/api/assess", params={"mode": "live"}).json()
    assert body["river_rising"] is True
    assert all("river rising" in p["reason"] for p in body["paddocks"])


def test_replay_explicit_river_rising_true_still_works(client, monkeypatch):
    monkeypatch.setattr(main, "get_river_status", None)
    body = client.get("/api/assess", params={"mode": "replay", "river_rising": "true"}).json()
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


@pytest.mark.parametrize(
    "cache",
    [
        {},  # missing cache file: nothing to apply
        None,  # malformed: not a mapping
        "not json",
        {"p999": 40.0, "zz": 12},  # ids that don't match the farm
        {"p1": "high", "p2": None, "p3": float("nan"), "p4": True},  # bad values
    ],
)
def test_bad_elevation_cache_keeps_geojson_values(monkeypatch, cache):
    farm = main.load_farm()
    before = {p.id: p.elevation_m for p in farm.paddocks}
    monkeypatch.setattr(main, "load_or_refresh_cache", lambda paddocks: cache)
    assert main.apply_elevation_cache(farm) == 0
    assert {p.id: p.elevation_m for p in farm.paddocks} == before


def test_startup_survives_a_crashing_elevation_loader(monkeypatch):
    def broken(paddocks):
        raise ValueError("elevation_cache.json is malformed")

    monkeypatch.setattr(main, "load_or_refresh_cache", broken)
    monkeypatch.setattr(main, "get_river_status", None)
    with TestClient(main.app) as client:  # context manager runs the startup code
        assert client.get("/api/assess", params={"mode": "replay"}).status_code == 200


def test_elevation_cache_is_applied_and_failures_are_ignored(monkeypatch):
    farm = main.load_farm()
    monkeypatch.setattr(main, "load_or_refresh_cache", lambda paddocks: {"p1": 19.5})
    assert main.apply_elevation_cache(farm) == 1
    assert farm.paddocks[0].elevation_m == 19.5

    def broken(paddocks):
        raise OSError("offline")

    monkeypatch.setattr(main, "load_or_refresh_cache", broken)
    assert main.apply_elevation_cache(farm) == 0
