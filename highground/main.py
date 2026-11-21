"""FastAPI app: farm, warnings (replay or live), river gauge, assessment and plan."""

from __future__ import annotations

import logging
import math
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime
from typing import Any, Literal

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .cap import Warning, as_replay, parse_cap
from .farm import DATA_DIR, Farm, load_farm
from .plan import facts, make_plan
from .risk import NZ_TZ, format_time, recommend, score_paddock, to_nz

# Optional data sources from the Data teammate. If they are not merged yet, or fail,
# we fall back to the GeoJSON elevations and "river not rising".
try:
    from .elevation import load_or_refresh_cache
except ImportError:  # pragma: no cover - depends on what is merged
    load_or_refresh_cache = None
try:
    from .river import get_river_status
except ImportError:  # pragma: no cover - depends on what is merged
    get_river_status = None

log = logging.getLogger("highground")

METSERVICE_CAP_RSS = "https://alerts.metservice.com/cap/rss"
LIVE_CACHE_SECONDS = 10 * 60
RIVER_CACHE_SECONDS = 5 * 60
DISCLAIMER = (
    "Official MetService warnings and Civil Defence advice always come first. "
    "This is guidance, not a guarantee."
)

FARM = load_farm()
REPLAY = parse_cap((DATA_DIR / "replay_warning.xml").read_text(encoding="utf-8"))


def apply_elevation_cache(farm: Farm) -> int:
    """Replace placeholder paddock elevations with cached live values. Returns how many.

    Never raises: a missing or broken cache, wrong ids or bad values are logged and the
    GeoJSON elevations are kept for any paddock without a good value.
    """
    if load_or_refresh_cache is None:
        log.info("Elevation module not available, using GeoJSON elevations")
        return 0
    try:
        cache = load_or_refresh_cache(farm.paddocks)
    except Exception as exc:  # network or file problem: keep the GeoJSON values
        log.warning("Elevation cache unavailable, using GeoJSON values: %s", exc)
        return 0
    if not isinstance(cache, dict):
        log.warning("Elevation cache is not a mapping (%s), ignoring it", type(cache).__name__)
        return 0

    ids = {p.id for p in farm.paddocks}
    unknown = sorted(str(k) for k in cache if k not in ids)
    if unknown:
        log.warning("Elevation cache has ids not on this farm, ignoring: %s", unknown)
    updated = 0
    for p in farm.paddocks:
        value = cache.get(p.id)
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
        ):
            if p.id in cache:
                log.warning("Bad elevation for %s (%r), keeping %s m", p.id, value, p.elevation_m)
            continue
        p.elevation_m = float(value)
        updated += 1
    missing = len(ids) - updated
    if missing:
        log.warning("%d paddock(s) kept their GeoJSON elevation", missing)
    return updated


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        n = apply_elevation_cache(FARM)
        log.info("Applied %d live paddock elevations", n)
    except Exception:  # belt and braces: startup must never fail on elevation
        log.exception("Elevation update failed, using GeoJSON values")
    yield


app = FastAPI(title="HighGround API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def now_nz() -> datetime:
    """Current time in New Zealand, whatever time zone this server is set to."""
    return datetime.now(NZ_TZ)


# --- live MetService warnings (cached 10 minutes) ------------------------------

_live_cache: dict[str, Any] = {"at": None, "warnings": []}


def fetch_live_warnings() -> list[Warning]:
    """Fetch the MetService CAP RSS list, then each linked CAP file."""
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


def live_warnings() -> list[Warning]:
    """Live warnings, reusing a successful fetch for 10 minutes. May raise on failure."""
    at = _live_cache["at"]
    if at is not None and time.monotonic() - at < LIVE_CACHE_SECONDS:
        return _live_cache["warnings"]
    warnings = fetch_live_warnings()
    _live_cache.update(at=time.monotonic(), warnings=warnings)
    return warnings


def active_warning(mode: str) -> tuple[Warning | None, str | None]:
    """(warning, live_status). live_status is None outside live mode."""
    if mode == "replay":
        return as_replay(REPLAY, now_nz()), None
    if mode == "live":
        try:
            warnings = live_warnings()
        except Exception as exc:  # never a 500: tell the UI the feed is unavailable
            log.warning("MetService feed unavailable: %s", exc)
            return None, "unavailable"
        candidates = [w for w in warnings if any(w.covers(p.centre) for p in FARM.paddocks)]
        order = {"red": 3, "orange": 2, "yellow": 1, "none": 0}
        return max(candidates, key=lambda w: order.get(w.level, 0), default=None), "ok"
    return None, None


# --- river gauge (cached 5 minutes) --------------------------------------------

_river_cache: dict[str, Any] = {"at": None, "status": None}


def current_river() -> dict[str, Any] | None:
    """Latest river reading as {site, level_m, observed_at, observed_label, rising}, or None."""
    if get_river_status is None:
        return None
    at = _river_cache["at"]
    if at is not None and time.monotonic() - at < RIVER_CACHE_SECONDS:
        return _river_cache["status"]
    try:
        status = get_river_status(timeout_s=5.0)
        river = (
            None
            if status is None
            else {
                "site": status.site,
                "level_m": status.level_m,
                "observed_at": to_nz(status.observed_at).isoformat(),
                "observed_label": format_time(status.observed_at),  # e.g. "2:15pm", NZ time
                "rising": bool(status.rising),
            }
        )
    except Exception as exc:  # gauge down: carry on without it
        log.warning("River gauge unavailable: %s", exc)
        river = None
    _river_cache.update(at=time.monotonic(), status=river)
    return river


# --- endpoints -----------------------------------------------------------------


@app.get("/api/farm")
def get_farm() -> dict:
    return FARM.geojson


@app.get("/api/assess")
def assess(
    mode: Literal["calm", "replay", "live"] = "calm",
    river_rising: bool | None = None,
) -> dict:
    warning, live_status = active_warning(mode)
    river = current_river()  # shown for display in every mode
    if river_rising is None:
        # Only live mode lets the real gauge change scores. Calm and replay are rehearsed
        # demo states, so they assume a steady river unless the caller says otherwise.
        river_rising = mode == "live" and bool(river and river["rising"])
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
            "onset": to_nz(warning.onset).isoformat(),
            "expires": to_nz(warning.expires).isoformat(),
            "onset_label": format_time(warning.onset),
            "expires_label": format_time(warning.expires),
        },
        "paddocks": [asdict(r) for r in risks],
        "recommendation": None
        if rec is None
        else {**asdict(rec), "deadline": rec.deadline.isoformat() if rec.deadline else None},
        "plan": make_plan(facts(FARM.name, FARM.herd_size, warning, risks, rec)),
        "disclaimer": DISCLAIMER,
        "river": river,
        "river_rising": river_rising,
        "live_status": live_status,
    }
