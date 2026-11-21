# Data sources

| Data | Source | Licence / terms | Used in |
|---|---|---|---|
| Severe weather warnings | MetService CAP feed: `https://alerts.metservice.com/cap/rss` (RSS list of links to CAP 1.2 files; `cap.parse_rss_links()` reads it) | CC BY 4.0 (stated in the feed's `<copyright>`); credit MetService | `cap.py`, `main.py` (live mode) |
| Earthquakes (optional) | GeoNet CAP: `https://api.geonet.org.nz/cap/1.2/GPA1.0/feed/atom1.0/quake` | GeoNet terms; credit GNS Science / GeoNet | not yet used |
| Elevation | Open Topo Data public API, dataset `nzdem8m`: `https://api.opentopodata.org/v1/nzdem8m?locations=lat,lng\|lat,lng` (8 m DEM from LINZ topo contours). Max 100 points per request, about 1 request per second. Upgrade path: LINZ 1 m LiDAR DEM | LINZ data, CC BY 4.0; credit "LINZ via Open Topo Data" | `elevation.py`, `data/elevation_cache.json` |
| River levels | Hawke's Bay Regional Council Hilltop server: `https://data.hbrc.govt.nz/Envirodata/Telemetry.hts?service=Hilltop&request=GetData&Site=Ngaruroro%20River%20at%20Fernhill&Measurement=Stage&TimeInterval=PT2H/now` | HBRC open data, CC BY 4.0; HBRC asks app developers to share a link with them | `river.py` |
| River centreline | OpenStreetMap way 7979568 (Ngaruroro River): `https://api.openstreetmap.org/api/0.6/way/7979568/full` | ODbL; © OpenStreetMap contributors | `data/sample_farm.geojson` (river feature) |
| HBRC gauge location | `https://data.hbrc.govt.nz/Envirodata/Telemetry.hts?service=Hilltop&request=SiteList&Location=LatLong`: Fernhill is at -39.586732, 176.760303 | HBRC, CC BY 4.0 | used to place the demo farm |
| Base map | OpenStreetMap tiles | ODbL; © OpenStreetMap contributors | `web/src/App.tsx` |

## Notes on the HBRC Hilltop server

- The live gauge is in **`Telemetry.hts`**. `EMAR.hts` has no data for Fernhill.
- The water-level measurement is **`Stage`** (mm, data source "Water Level"), sampled every
  5 minutes. `Flow` (l/s) and `Elevation Above Sea Level` are also available.
  `Flow[Water Level]` does **not** exist for this site.
- Times are NZ local time with no offset. `river.py` attaches `Pacific/Auckland`.
- **Spaces must be sent as `%20`.** With `+` (curl `--data-urlencode`, or httpx `params=`)
  Hilltop reads "Ngaruroro+River+at+Fernhill" literally and answers "No data".
- The server sits behind Cloudflare and often answers `522` (origin timeout). `river.py`
  returns `None` then, and the app carries on without a river reading.
- Readings wobble by ±5 mm between samples, so "rising" means up at least 1 cm compared
  with the reading about an hour earlier (`RISE_THRESHOLD_M` in `river.py`).
- Other Ngaruroro sites in `Telemetry.hts`: Chesterhope Bridge, Motorway Bridge, Ohiti,
  Whanawhana, Kuripapango.

## Sample data in this repo

| File | Real or sample | Details |
|---|---|---|
| `data/sample_farm.geojson` | **Fictional paddocks, real river and heights** | 9 invented paddocks beside the real Ngaruroro River. See "How the demo farm was made" below. |
| `data/elevation_cache.json` | **Real** | Same nzdem8m paddock heights as the GeoJSON, fetched 2026-11-21. |
| `data/build_sample_farm.py` | Script | Rebuilds both files above from OSM + Open Topo Data (needs network). |
| `data/replay_warning.xml` | **Sample** (status "Exercise", headline starts "SAMPLE") | Not a real MetService warning. See the record below. |
| `tests/fixtures/hilltop_fernhill_stage_real.xml` | **Real** | HBRC Stage at Fernhill, 24 h to 2026-11-21 12:05 NZDT (river steady, about 2.73 m). |
| `tests/fixtures/hilltop_rising_sample.xml` | **Sample** (hand-made) | Same format, showing a rising river, for tests. |

## How the demo farm was made (fetched 2026-11-21)

1. **River line.** The real Ngaruroro River centreline from OpenStreetMap (way 7979568),
   clipped to the stretch beside the farm, with one extra OSM node at each end so the line
   runs past the farm.
2. **Paddocks.** A fictional 3 x 3 grid of 300 m squares (9 ha each) on the **north bank,
   0.5–1.5 km upstream (west) of the HBRC Fernhill gauge**. South-west corner of Paddock 1:
   lon 176.744, lat -39.5866. Paddocks 1–3 are the row nearest the river, on the
   floodplain. Paddocks 7–9 are the furthest row; Paddock 7 is on the hill to the north-west.
   Paddock 8 has no water.
3. **Heights.** LINZ nzdem8m via Open Topo Data at each paddock centroid, and at 15 points
   every 100 m along the river beside the farm. `river_elevation_m` = the **median** of the
   river points = **38.2 m**. The river points are stored in the GeoJSON under
   `properties.river_points`. The same paddock heights are in the GeoJSON `elevation_m` and in
   `elevation_cache.json`, so offline and cached runs agree (tested).
4. **Placement.** The position was chosen by trying every position along a 4 km stretch on
   both banks and scoring each with the real `score_paddock()` (risk thresholds unchanged).
   Positions where the river crosses a paddock were rejected.

Result with the replay warning (`tests/test_demo_real_heights.py` checks this):

| Paddock | Height (m) | Above river (m) | To river (m) | Score | Band |
|---|---|---|---|---|---|
| 1 | 37.5 | -0.7 | 289 | 0.77 | red |
| 2 | 39.5 | 1.3 | 263 | 0.71 | red |
| 3 | 40.0 | 1.8 | 241 | 0.70 | red |
| 4 | 38.9 | 0.7 | 588 | 0.56 | amber |
| 5 | 40.0 | 1.8 | 562 | 0.49 | amber |
| 6 | 39.9 | 1.7 | 540 | 0.50 | amber |
| 7 | 68.5 | 30.3 | 886 | 0.00 | green |
| 8 | 40.1 | 1.9 | 861 | 0.49 | amber (no water) |
| 9 | 40.1 | 1.9 | 839 | 0.49 | amber |

Recommendation: "Move the herd to Paddock 7". With `river_rising`, Paddock 4 also turns red
(0.66) and Paddock 7 stays green (0.10). On a calm day, every paddock is green.

### Caveats about the heights (say this if asked)

- nzdem8m is built from LINZ 20 m topographic contours, so flat ground comes out as wide
  terraces at exactly 20 m or 40 m. Paddocks 2–6, 8 and 9 all sit at 39–40 m, so near this
  river only Paddock 7, on the hill, is clearly higher ground. The other paddocks differ
  mainly in how far they are from the river.
- The river-point heights rise downstream (34 m to 40 m), which a real river can't do. The
  river bed and its stopbanks are not resolved at this resolution. The median smooths this,
  but height above the river is approximate, to within a few metres.
- The upgrade path is the LINZ 1 m LiDAR DEM for Hawke's Bay.
- A spot right beside the gauge (south bank, river median about 21 m) gave a nicer
  gradient, but the real river line runs through the near row there, so it was rejected.

## Replay warning record

| Field | Value |
|---|---|
| Source URL | None yet. `https://alerts.metservice.com/cap/rss` was checked on 2026-11-21 and had **no active warnings**. No archived MetService CAP file could be found. |
| Issued | n/a (sample dated 2026-02-12) |
| Event / level | Heavy Rain, Red (sample) |
| Area | Rectangle lat -39.50 to -39.75, lon 176.55 to 176.95. Covers every corner of every paddock of the sample farm (tested). |
| Saved on | n/a |

To replace it: when a Hawke's Bay heavy-rain warning is active, open the feed, save the
linked CAP XML over `data/replay_warning.xml`, run `pytest tests/test_cap_real.py` (checks
the level, the labelling and that the polygon covers the farm), and fill in this table.
