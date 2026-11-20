"""FastAPI app: farm, warnings (replay or live), assessment and plan."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .cap import Warning, as_replay, parse_cap
from .farm import DATA_DIR, load_farm
from .plan import facts, make_plan
from .risk import recommend, score_paddock

METSERVICE_CAP_RSS = "https://alerts.metservice.com/cap/rss"

app = FastAPI(title="HighGround API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

FARM = load_farm()
REPLAY = parse_cap((DATA_DIR / "replay_warning.xml").read_text(encoding="utf-8"))


def now_nz() -> datetime:
    return datetime.now(UTC).astimezone()


def live_warnings() -> list[Warning]:
    """Fetch the MetService CAP RSS list, then each linked CAP file. TODO: cache for 10 minutes."""
    import xml.etree.ElementTree as ET

    rss = httpx.get(METSERVICE_CAP_RSS, timeout=10)
    rss.raise_for_status()
    # Item links point at individual CAP files; skip the channel's own link.
    links = [el.text for el in ET.fromstring(rss.text).iter("link") if el.text]
    cap_links = [link for link in links if "/cap/" in link and link != METSERVICE_CAP_RSS]
    warnings = []
    for link in cap_links:
        try:
            warnings.append(parse_cap(httpx.get(link, timeout=10).text))
        except Exception:  # skip one bad file rather than failing the whole feed
            continue
    return warnings


def active_warning(mode: str) -> Warning | None:
    if mode == "replay":
        return as_replay(REPLAY, now_nz())
    if mode == "live":
        try:
            candidates = [
                w for w in live_warnings() if any(w.covers(p.centre) for p in FARM.paddocks)
            ]
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Could not reach MetService feed: {exc}") from exc
        order = {"red": 3, "orange": 2, "yellow": 1, "none": 0}
        return max(candidates, key=lambda w: order[w.level], default=None)
    return None


@app.get("/api/farm")
def get_farm() -> dict:
    return FARM.geojson


@app.get("/api/assess")
def assess(mode: Literal["calm", "replay", "live"] = "calm", river_rising: bool = False) -> dict:
    warning = active_warning(mode)
    risks = [
        score_paddock(p, FARM.river, FARM.river_elevation_m, warning, river_rising)
        for p in FARM.paddocks
    ]
    rec = recommend(FARM.paddocks, risks, FARM.herd_size, FARM.ha_per_cow, warning)
    return {
        "mode": mode,
        "warning": None
        if warning is None
        else {
            **{k: v for k, v in asdict(warning).items() if k not in ("areas", "onset", "expires")},
            "onset": warning.onset.isoformat(),
            "expires": warning.expires.isoformat(),
        },
        "paddocks": [asdict(r) for r in risks],
        "recommendation": None
        if rec is None
        else {**asdict(rec), "deadline": rec.deadline.isoformat() if rec.deadline else None},
        "plan": make_plan(facts(FARM.name, FARM.herd_size, warning, risks, rec)),
        "disclaimer": "Official MetService warnings and Civil Defence advice always come first. "
        "This is guidance, not a guarantee.",
    }
