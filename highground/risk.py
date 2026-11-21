"""Per-paddock flood risk scoring and stock-move recommendation.

Deliberately simple and explainable — every score comes with a one-line reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from .cap import Warning
from .geo import Point, area_ha, centroid, distance_to_line_m

# Tunable thresholds (document changes in docs/decisions.md)
SAFE_HEIGHT_M = 10.0  # at or above this height over the river, height risk is 0
SAFE_DISTANCE_M = 500.0  # at or beyond this distance from the river, distance risk is 0
HEIGHT_WEIGHT = 0.6
DISTANCE_WEIGHT = 0.4
LEVEL_MULTIPLIER = {"none": 0.3, "yellow": 0.5, "orange": 0.8, "red": 1.0}
RIVER_RISING_BONUS = 0.1
MOVE_BUFFER = timedelta(hours=3)

# Every time a farmer sees is New Zealand time, whatever the server's own time zone is.
NZ_TZ = ZoneInfo("Pacific/Auckland")


def to_nz(t: datetime) -> datetime:
    """Convert to New Zealand time. A time with no zone is assumed to be NZ time already."""
    if t.tzinfo is None:
        return t.replace(tzinfo=NZ_TZ)
    return t.astimezone(NZ_TZ)


@dataclass
class Paddock:
    id: str
    name: str
    ring: list[Point]
    elevation_m: float
    has_water: bool = True

    @property
    def centre(self) -> Point:
        return centroid(self.ring)

    @property
    def area_ha(self) -> float:
        return area_ha(self.ring)


@dataclass
class PaddockRisk:
    paddock_id: str
    name: str
    score: float
    band: str  # green | amber | red
    reason: str
    height_above_river_m: float
    distance_to_river_m: float


def band(score: float) -> str:
    if score < 0.33:
        return "green"
    if score < 0.66:
        return "amber"
    return "red"


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def score_paddock(
    paddock: Paddock,
    river: list[Point],
    river_elevation_m: float,
    warning: Warning | None,
    river_rising: bool = False,
) -> PaddockRisk:
    height = paddock.elevation_m - river_elevation_m
    distance = distance_to_line_m(paddock.centre, river)
    low = _clamp01(1 - height / SAFE_HEIGHT_M)
    near = _clamp01(1 - distance / SAFE_DISTANCE_M)
    base = HEIGHT_WEIGHT * low + DISTANCE_WEIGHT * near

    in_warning = warning is not None and warning.covers(paddock.centre)
    level = warning.level if in_warning else "none"
    score = base * LEVEL_MULTIPLIER[level]
    if river_rising:
        score += RIVER_RISING_BONUS
    score = round(_clamp01(score), 2)

    parts = [f"{height:.0f} m above river", f"{distance:.0f} m from river"]
    if in_warning:
        parts.append(f"inside {level} warning")
    if river_rising:
        parts.append("river rising")
    return PaddockRisk(
        paddock_id=paddock.id,
        name=paddock.name,
        score=score,
        band=band(score),
        reason=", ".join(parts),
        height_above_river_m=round(height, 1),
        distance_to_river_m=round(distance),
    )


@dataclass
class Recommendation:
    paddock_id: str
    name: str
    deadline: datetime | None
    message: str
    deadline_label: str | None = None  # e.g. "4pm", NZ time


def format_time(t: datetime) -> str:
    """'4pm', '10:30am' style, in NZ time."""
    t = to_nz(t)
    hour = t.hour % 12 or 12
    suffix = "am" if t.hour < 12 else "pm"
    return f"{hour}{suffix}" if t.minute == 0 else f"{hour}:{t.minute:02d}{suffix}"


def recommend(
    paddocks: list[Paddock],
    risks: list[PaddockRisk],
    herd_size: int,
    ha_per_cow: float,
    warning: Warning | None,
) -> Recommendation | None:
    """Safest paddock with water and enough room.

    Deadline = onset minus buffer, rounded down to the hour, in NZ time.
    """
    by_id = {p.id: p for p in paddocks}
    needed_ha = herd_size * ha_per_cow
    candidates = [
        r
        for r in risks
        if by_id[r.paddock_id].has_water and by_id[r.paddock_id].area_ha >= needed_ha
    ]
    if not candidates:
        return None
    best = min(candidates, key=lambda r: (r.score, -r.height_above_river_m))

    deadline = None
    label = None
    if warning is not None and warning.level in ("orange", "red"):
        # Subtract in UTC so a daylight-saving change can't shift the buffer, then show in NZ.
        latest = to_nz(warning.onset).astimezone(UTC) - MOVE_BUFFER
        deadline = to_nz(latest).replace(minute=0, second=0, microsecond=0)
        label = format_time(deadline)
        message = f"Move the herd to {best.name} by {label}"
    else:
        message = f"Safest paddock if conditions worsen: {best.name}"
    return Recommendation(best.paddock_id, best.name, deadline, message, label)
