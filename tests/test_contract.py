"""Contract test: /api/assess must match what the UI expects in web/src/api.ts.

Owner: Teammate 5 (QA). If this fails, either the API dropped or retyped a field the UI
reads, or the UI started expecting a field the API never sends. Fix one side, then re-run.

How it works, simply:
1. Read the TypeScript interfaces in web/src/api.ts and list each field and whether it is
   optional (`name?:`). That way the test follows the UI file automatically.
2. Call the API in calm, replay and live (offline) mode and check every required field is
   present with the right type, and optional fields are missing, null or the right type.

No network: every outgoing connection raises, so live data sources must fall back safely.
"""

from __future__ import annotations

import re
import socket
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from highground import main

API_TS = Path(__file__).resolve().parents[1] / "web" / "src" / "api.ts"

# Optional in api.ts: may be missing or null, but if present must have the right type.
OPTIONAL_TOP_LEVEL = {"river", "live_status", "river_rising"}


# --- no network --------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any attempt to reach the internet fails, like a farm with no signal."""

    def refuse(*_args, **_kwargs):
        raise httpx.ConnectError("network disabled in tests")

    def refuse_socket(self, address, *args, **kwargs):
        if isinstance(address, tuple):  # IP sockets only; leave unix sockets alone
            raise OSError("network disabled in tests")
        return real_connect(self, address, *args, **kwargs)

    real_connect = socket.socket.connect
    monkeypatch.setattr(httpx, "get", refuse)
    monkeypatch.setattr(httpx.Client, "send", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse_socket)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # Start each test with empty caches so nothing carries over between tests.
    for cache in ("_live_cache", "_river_cache"):
        if hasattr(main, cache):
            monkeypatch.setattr(main, cache, {"at": None, "warnings": [], "status": None})


@pytest.fixture
def client():
    with TestClient(main.app) as c:  # "with" runs startup too: it must survive offline
        yield c


# --- reading web/src/api.ts ----------------------------------------------------------------


def ts_interface(name: str) -> dict[str, tuple[bool, str]]:
    """Top-level fields of `export interface <name> { ... }` as {field: (optional, type)}."""
    text = API_TS.read_text(encoding="utf-8")
    start = re.search(rf"export interface {name}\s*{{", text)
    assert start, f"interface {name} not found in {API_TS}"
    depth, i, body_start = 1, start.end(), start.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    body = text[body_start : i - 1]
    body = re.sub(r"/\*.*?\*/|//[^\n]*", "", body, flags=re.S)  # drop comments

    fields: dict[str, tuple[bool, str]] = {}
    depth, line = 0, ""
    for ch in body:  # split on ';' and newlines only at the top level of the interface
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        if depth == 0 and ch in ";\n":
            m = re.match(r"\s*(\w+)(\?)?\s*:\s*(.+)", line, re.S)
            if m:
                fields[m.group(1)] = (bool(m.group(2)), " ".join(m.group(3).split()))
            line = ""
        else:
            line += ch
    return fields


def test_api_ts_parser_reads_the_ui_types():
    fields = ts_interface("Assessment")
    for name in ("mode", "warning", "paddocks", "recommendation", "plan", "disclaimer"):
        assert name in fields and fields[name][0] is False, name
    assert set(ts_interface("PaddockRisk")) >= {"paddock_id", "band", "reason", "score"}


# --- type checks -------------------------------------------------------------------------

PY_TYPE = {"string": str, "number": (int, float), "boolean": bool}


def check_value(value, ts_type: str, where: str) -> None:
    """Check a value against a simple TS type: string, number, boolean, literal unions."""
    ts_type = ts_type.strip()
    if "{" in ts_type or "[]" in ts_type:  # object/array: nested fields are checked separately
        nullable = ts_type.startswith("null") or ts_type.endswith("null")
        if value is None:
            assert nullable, f"{where} is null but api.ts does not allow null"
            return
        assert isinstance(value, list if ts_type.endswith("[]") else dict), where
        return
    options = [t.strip() for t in ts_type.split("|")]
    if "null" in options and value is None:
        return
    literals = [t.strip("\"'") for t in options if t[:1] in "\"'"]
    if literals:
        assert value in literals, f"{where}: {value!r} not one of {literals}"
        return
    base = [t for t in options if t in PY_TYPE]
    if base:
        assert any(
            isinstance(value, PY_TYPE[t]) and not (t == "number" and isinstance(value, bool))
            for t in base
        ), f"{where}: {value!r} is not {ts_type}"


def check_object(obj: dict, interface: str, where: str) -> None:
    assert isinstance(obj, dict), f"{where} should be an object"
    for name, (optional, ts_type) in ts_interface(interface).items():
        if name not in obj:
            assert optional, f"{where}.{name} is required by api.ts but missing"
            continue
        check_value(obj[name], ts_type, f"{where}.{name}")


def check_assessment(body: dict) -> None:
    check_object(body, "Assessment", "assessment")

    for i, p in enumerate(body["paddocks"]):
        check_object(p, "PaddockRisk", f"paddocks[{i}]")
        assert 0 <= p["score"] <= 1

    w = body["warning"]
    if w is not None:
        for key, typ in [("event", str), ("headline", str), ("onset", str), ("expires", str)]:
            assert isinstance(w.get(key), typ), f"warning.{key}"
        assert w["level"] in ("yellow", "orange", "red")
        assert isinstance(w["is_replay"], bool)

    rec = body["recommendation"]
    if rec is not None:
        assert isinstance(rec["name"], str) and isinstance(rec["message"], str)
        assert rec["deadline"] is None or isinstance(rec["deadline"], str)
        # deadline_label (from the Logic PR) is optional: missing, null or a short string
        assert rec.get("deadline_label") is None or isinstance(rec["deadline_label"], str)

    plan = body["plan"]
    assert isinstance(plan["summary"], str)
    assert plan["source"] in ("gemini", "template")
    assert all(isinstance(m["time"], str) and isinstance(m["action"], str) for m in plan["moves"])
    assert all(isinstance(c, str) for c in plan["checklist"])

    # Optional fields: missing, null or the right type. Extra fields the UI doesn't declare
    # yet are fine (it ignores them), so the Logic PR can merge before the UI PR.
    declared = ts_interface("Assessment")
    for name in OPTIONAL_TOP_LEVEL & declared.keys():
        assert declared[name][0], f"api.ts should mark {name!r} optional (older servers omit it)"
    if body.get("river") is not None and "RiverReading" in API_TS.read_text(encoding="utf-8"):
        check_object(body["river"], "RiverReading", "river")
    assert body.get("river_rising") is None or isinstance(body["river_rising"], bool)
    assert body.get("live_status") in (None, "ok", "unavailable")


# --- the contract ------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["calm", "replay"])
def test_assess_matches_api_ts(client, mode):
    res = client.get("/api/assess", params={"mode": mode})
    assert res.status_code == 200
    check_assessment(res.json())


@pytest.mark.parametrize("river_rising", ["true", "false"])
def test_assess_with_river_rising_param_matches_api_ts(client, river_rising):
    res = client.get("/api/assess", params={"mode": "replay", "river_rising": river_rising})
    assert res.status_code == 200
    check_assessment(res.json())


def test_live_mode_offline_never_500(client):
    """With no network, live mode must not crash. The UI handles 200 + unavailable (or 502)."""
    res = client.get("/api/assess", params={"mode": "live"})
    assert res.status_code in (200, 502), res.text
    if res.status_code == 200:
        body = res.json()
        check_assessment(body)
        assert body["warning"] is None
        if "live_status" in body:
            assert body["live_status"] == "unavailable", "offline must not look like all clear"


def test_farm_endpoint_is_geojson_with_paddocks_and_river(client):
    farm = client.get("/api/farm").json()
    assert farm["type"] == "FeatureCollection"
    kinds = [f["properties"].get("kind") for f in farm["features"]]
    assert kinds.count("paddock") >= 3 and "river" in kinds
    assessed = {p["paddock_id"] for p in client.get("/api/assess").json()["paddocks"]}
    drawn = {
        f["properties"]["id"] for f in farm["features"] if f["properties"].get("kind") == "paddock"
    }
    assert assessed == drawn, "every paddock on the map needs a score (popups look them up by id)"
