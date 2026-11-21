"""Rebuild data/sample_farm.geojson and data/elevation_cache.json from real data.

    python data/build_sample_farm.py

Not used by the app (needs the network). It documents exactly how the demo farm was made:
1. River: OpenStreetMap way 7979568 (Ngaruroro River), via api.openstreetmap.org (ODbL).
2. Paddocks: FICTIONAL 3 x 3 grid of 300 m squares (9 ha) on the north bank, 0.5-1.5 km
   upstream of the HBRC Fernhill gauge. Row p1-p3 is nearest the river.
3. Heights: LINZ nzdem8m via Open Topo Data (CC BY 4.0) at each paddock centroid and at
   points every 100 m along the river beside the farm. river_elevation_m = their median.
"""

from __future__ import annotations

import json
import math
import statistics
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from highground.elevation import load_or_refresh_cache, lookup_elevations
from highground.farm import load_farm
from highground.geo import centroid

DATA = Path(__file__).resolve().parent
OSM_WAY = "https://api.openstreetmap.org/api/0.6/way/7979568/full"
X0, Y0 = 176.744, -39.5866  # south-west corner of Paddock 1 (lon, lat)
SIDE_M = 300.0  # paddock side: 300 m x 300 m = 9 ha
M_LAT = 111_320.0  # metres per degree of latitude
M_LON = M_LAT * math.cos(math.radians(39.59))  # metres per degree of longitude here


def r6(v: float) -> float:
    return round(v, 6)


def river_line() -> list[tuple[float, float]]:
    """OSM centreline from 1 km west to 1 km east of the farm, plus one node each side."""
    root = ET.fromstring(
        httpx.get(OSM_WAY, timeout=60, headers={"User-Agent": "highground-demo"}).text
    )
    nodes = {n.get("id"): (float(n.get("lon")), float(n.get("lat"))) for n in root.iter("node")}
    way = [nodes[nd.get("ref")] for nd in root.find("way").findall("nd")]
    farm_w = 3 * SIDE_M / M_LON
    idx = [i for i, (x, _) in enumerate(way) if X0 - 0.008 <= x <= X0 + farm_w + 0.008]
    return [(r6(x), r6(y)) for x, y in way[max(idx[0] - 1, 0) : idx[-1] + 2]]


def points_along(line, step_m=100.0):
    out, carry = [], 0.0
    for (x0, y0), (x1, y1) in zip(line, line[1:], strict=False):
        seg = math.hypot((x1 - x0) * M_LON, (y1 - y0) * M_LAT)
        d = carry
        while d < seg:
            t = d / seg
            out.append((r6(x0 + (x1 - x0) * t), r6(y0 + (y1 - y0) * t)))
            d += step_m
        carry = d - seg
    return out


def main() -> None:
    dlon, dlat = SIDE_M / M_LON, SIDE_M / M_LAT
    paddocks = []
    for row in range(3):
        for col in range(3):
            k = row * 3 + col + 1
            lo, la = X0 + col * dlon, Y0 + row * dlat
            ring = [(lo, la), (lo + dlon, la), (lo + dlon, la + dlat), (lo, la + dlat), (lo, la)]
            ring = [(r6(x), r6(y)) for x, y in ring]
            paddocks.append({"id": f"p{k}", "ring": ring, "has_water": k != 8})

    river = river_line()
    beside = [p for p in points_along(river) if X0 - dlon <= p[0] <= X0 + 4 * dlon]
    heights = lookup_elevations([centroid(p["ring"]) for p in paddocks] + beside, timeout_s=30)
    if None in heights or len(heights) != 9 + len(beside):
        raise SystemExit("elevation lookup incomplete; try again")
    river_z = heights[9:]

    features = [
        {
            "type": "Feature",
            "properties": {
                "kind": "paddock",
                "id": p["id"],
                "name": f"Paddock {p['id'][1:]}",
                "elevation_m": round(z, 1),
                "has_water": p["has_water"],
            },
            "geometry": {"type": "Polygon", "coordinates": [[list(c) for c in p["ring"]]]},
        }
        for p, z in zip(paddocks, heights[:9], strict=True)
    ]
    features.append(
        {
            "type": "Feature",
            "properties": {
                "kind": "river",
                "name": "Ngaruroro River",
                "source": "OpenStreetMap way 7979568 (ODbL, © OpenStreetMap contributors)",
            },
            "geometry": {"type": "LineString", "coordinates": [list(c) for c in river]},
        }
    )
    nw5 = paddocks[4]["ring"][3]  # north-west corner of Paddock 5
    shed = [r6(nw5[0] + 0.0004), r6(nw5[1] - 0.0004)]
    features.append(
        {
            "type": "Feature",
            "properties": {"kind": "shed", "name": "Milking shed"},
            "geometry": {"type": "Point", "coordinates": shed},
        }
    )
    fetched = time.strftime("%Y-%m-%d")
    farm = {
        "type": "FeatureCollection",
        "properties": {
            "name": "Demo Farm (fictional), Hawke's Bay",
            "herd_size": 300,
            "ha_per_cow": 0.02,
            "river_elevation_m": round(statistics.median(river_z), 1),
            "note": (
                "FICTIONAL demo farm: invented paddocks placed beside the real Ngaruroro "
                "River, on the north bank 0.5-1.5 km upstream of the HBRC Fernhill gauge. "
                "River line: OpenStreetMap (ODbL). Heights: LINZ nzdem8m via Open Topo Data "
                f"(CC BY 4.0), fetched {fetched}. river_elevation_m is the median of the "
                "river-point heights in river_points. Rebuild: data/build_sample_farm.py."
            ),
            "river_points": [
                {"lon": x, "lat": y, "elevation_m": round(z, 1)}
                for (x, y), z in zip(beside, river_z, strict=True)
            ],
        },
        "features": features,
    }
    (DATA / "sample_farm.geojson").write_text(json.dumps(farm, indent=2) + "\n", encoding="utf-8")
    time.sleep(1.1)  # Open Topo Data: about 1 request per second
    cache = load_or_refresh_cache(load_farm().paddocks, refresh=True)
    print("river_elevation_m:", farm["properties"]["river_elevation_m"])
    print("paddocks:", cache)


if __name__ == "__main__":
    main()
