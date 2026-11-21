"""Demo-path rules at the API level. Owner: Teammate 5 (QA).

The demo we show judges must ALWAYS work, offline, whatever the laptop's time zone:
  sample farm -> Replay warning -> at least 2 red paddocks near the river, at least 1 green
  -> banner "Move the herd to Paddock N by <time>" -> each paddock has a reason
  -> plan has moves + checklist -> safety line on every response, REPLAY is labelled.

If one of these fails, the demo is broken: fix it before anything else.
No network: every outgoing connection raises.
"""

from __future__ import annotations

import re
import socket
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from highground import main, risk

SAFETY = (
    "Official MetService warnings and Civil Defence advice always come first. "
    "This is guidance, not a guarantee."
)
BANNER = re.compile(r"^Move the herd to (Paddock \d+) by (\d{1,2}(:\d{2})?(am|pm))$")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise httpx.ConnectError("network disabled in tests")

    def refuse_socket(self, address, *args, **kwargs):
        if isinstance(address, tuple):
            raise OSError("network disabled in tests")
        return real_connect(self, address, *args, **kwargs)

    real_connect = socket.socket.connect
    monkeypatch.setattr(httpx, "get", refuse)
    monkeypatch.setattr(httpx.Client, "send", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse_socket)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    for cache in ("_live_cache", "_river_cache"):
        if hasattr(main, cache):
            monkeypatch.setattr(main, cache, {"at": None, "warnings": [], "status": None})


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


def replay(client, **params):
    res = client.get("/api/assess", params={"mode": "replay", **params})
    assert res.status_code == 200, res.text
    return res.json()


def farm_props(client) -> dict[str, dict]:
    farm = client.get("/api/farm").json()
    return {
        f["properties"]["id"]: f["properties"]
        for f in farm["features"]
        if f["properties"].get("kind") == "paddock"
    }


# --- step by step ------------------------------------------------------------------------


def test_step1_sample_farm_loads(client):
    assert len(farm_props(client)) >= 3


def test_step2_replay_is_labelled_replay(client):
    w = replay(client)["warning"]
    assert w is not None, "Replay warning produced no warning"
    assert w["is_replay"] is True
    assert w["level"] in ("orange", "red"), "needs orange/red for a move deadline"


def test_step3_at_least_two_red_and_one_green(client):
    bands = [p["band"] for p in replay(client)["paddocks"]]
    assert bands.count("red") >= 2, f"need >= 2 red paddocks, got {bands}"
    assert bands.count("green") >= 1, f"need >= 1 green paddock, got {bands}"


def test_step3_red_paddocks_are_the_ones_near_the_river(client):
    paddocks = replay(client)["paddocks"]
    red = [p for p in paddocks if p["band"] == "red"]
    green = [p for p in paddocks if p["band"] == "green"]
    assert max(p["distance_to_river_m"] for p in red) < min(p["distance_to_river_m"] for p in green)


def test_step4_banner_names_a_safe_watered_paddock_and_a_time(client):
    body = replay(client)
    rec = body["recommendation"]
    assert rec is not None
    m = BANNER.match(rec["message"])
    assert m, f"banner text {rec['message']!r} does not match 'Move the herd to Paddock N by 4pm'"
    target = next(p for p in body["paddocks"] if p["name"] == m.group(1))
    assert target["band"] == "green", "never send the herd to an amber or red paddock"
    props = farm_props(client)[target["paddock_id"]]
    assert props.get("has_water", True), "recommended paddock has no water"


def test_step5_every_paddock_has_a_reason(client):
    for p in replay(client)["paddocks"]:
        # "below river" allowed: real heights can put a paddock under the median river level
        assert re.search(r"(above|below) river", p["reason"]) and "from river" in p["reason"], p


def test_step6_plan_has_moves_and_checklist(client):
    body = replay(client)
    plan = body["plan"]
    assert plan["moves"], "plan has no moves"
    assert len(plan["checklist"]) >= 3, "plan checklist too short"
    assert any(body["recommendation"]["message"] in m["action"] for m in plan["moves"]), (
        "plan must repeat the banner's move, word for word"
    )
    assert plan["source"] == "template", "no API key in tests, so the template must be used"


@pytest.mark.parametrize("mode", ["calm", "replay", "live"])
def test_safety_line_on_every_response(client, mode):
    res = client.get("/api/assess", params={"mode": mode})
    if res.status_code == 200:
        assert res.json()["disclaimer"] == SAFETY


# --- robustness ----------------------------------------------------------------------------


def test_demo_still_works_when_the_river_is_rising(client):
    body = replay(client, river_rising="true")
    bands = [p["band"] for p in body["paddocks"]]
    assert bands.count("red") >= 2 and bands.count("green") >= 1, bands
    assert BANNER.match(body["recommendation"]["message"])


def test_deadline_is_in_the_future_and_before_onset(client):
    body = replay(client)
    deadline = datetime.fromisoformat(body["recommendation"]["deadline"])
    onset = datetime.fromisoformat(body["warning"]["onset"])
    now = datetime.now(UTC)
    assert now < deadline < onset
    assert onset - deadline >= timedelta(hours=3)


@pytest.mark.xfail(
    not hasattr(risk, "NZ_TZ"),
    reason="BUG-002 open on main (server time zone used); fixed by PR #2",
    strict=True,
)
@pytest.mark.parametrize("utc_hour", [0, 6, 12, 18])
def test_banner_time_is_nz_time_whatever_the_server_clock(client, monkeypatch, utc_hour):
    """The demo laptop or a cloud server may be on UTC. The banner must still show NZ time.

    BUG-002: main uses the server's local zone. Fixed by PR #2 (Logic) via main.now_nz().
    """
    from zoneinfo import ZoneInfo

    nz = ZoneInfo("Pacific/Auckland")
    fake_now = datetime(2026, 11, 21, utc_hour, 0, tzinfo=UTC)
    monkeypatch.setattr(main, "now_nz", lambda: fake_now)
    body = replay(client)
    deadline = datetime.fromisoformat(body["recommendation"]["deadline"])
    nz_deadline = deadline.astimezone(nz)
    expected = f"{nz_deadline.hour % 12 or 12}{'am' if nz_deadline.hour < 12 else 'pm'}"
    if nz_deadline.minute:
        expected = expected.replace(expected[:-2], f"{expected[:-2]}:{nz_deadline.minute:02d}")
    assert deadline.utcoffset() in (timedelta(hours=12), timedelta(hours=13)), (
        f"deadline {body['recommendation']['deadline']} is not in NZ time"
    )
    assert body["recommendation"]["message"].endswith(f" by {expected}")


def test_live_mode_offline_does_not_claim_all_clear(client):
    res = client.get("/api/assess", params={"mode": "live"})
    assert res.status_code != 500, res.text
    if res.status_code == 200:
        body = res.json()
        assert body["warning"] is None
        assert body.get("live_status", "unavailable") == "unavailable"
