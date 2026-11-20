"""Load a farm from GeoJSON: paddock polygons, a river line, and farm settings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .geo import Point
from .risk import Paddock

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Farm:
    name: str
    herd_size: int
    ha_per_cow: float
    river_name: str
    river: list[Point]
    river_elevation_m: float
    paddocks: list[Paddock]
    geojson: dict


def load_farm(path: Path = DATA_DIR / "sample_farm.geojson") -> Farm:
    data = json.loads(path.read_text(encoding="utf-8"))
    props = data["properties"]
    paddocks: list[Paddock] = []
    river: list[Point] = []
    river_name = "river"
    for feature in data["features"]:
        kind = feature["properties"]["kind"]
        coords = feature["geometry"]["coordinates"]
        if kind == "paddock":
            paddocks.append(
                Paddock(
                    id=feature["properties"]["id"],
                    name=feature["properties"]["name"],
                    ring=[tuple(c) for c in coords[0]],
                    elevation_m=feature["properties"]["elevation_m"],
                    has_water=feature["properties"].get("has_water", True),
                )
            )
        elif kind == "river":
            river = [tuple(c) for c in coords]
            river_name = feature["properties"].get("name", river_name)
    if not river:
        raise ValueError("farm GeoJSON needs a river feature")
    return Farm(
        name=props["name"],
        herd_size=props["herd_size"],
        ha_per_cow=props["ha_per_cow"],
        river_name=river_name,
        river=river,
        river_elevation_m=props["river_elevation_m"],
        paddocks=paddocks,
        geojson=data,
    )
