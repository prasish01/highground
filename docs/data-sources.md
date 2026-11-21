# Data sources

| Data | Source | Licence / terms | Used in |
|---|---|---|---|
| Severe weather warnings | MetService CAP feed: `https://alerts.metservice.com/cap/rss` (RSS list of links to CAP 1.2 files; `cap.parse_rss_links()` reads it) | CC BY 4.0 (stated in the feed's `<copyright>`); credit MetService | `cap.py`, `main.py` (live mode) |
| Earthquakes (optional) | GeoNet CAP: `https://api.geonet.org.nz/cap/1.2/GPA1.0/feed/atom1.0/quake` | GeoNet terms; credit GNS Science / GeoNet | not yet used |
| Elevation | Open Topo Data public API, dataset `nzdem8m`: `https://api.opentopodata.org/v1/nzdem8m?locations=lat,lng\|lat,lng` (8 m DEM from LINZ topo contours). Max 100 points per request, about 1 request per second. Upgrade path: LINZ 1 m LiDAR DEM | LINZ data, CC BY 4.0; credit "LINZ via Open Topo Data" | `elevation.py`, `data/elevation_cache.json` |
| River levels | Hawke's Bay Regional Council Hilltop server: `https://data.hbrc.govt.nz/Envirodata/Telemetry.hts?service=Hilltop&request=GetData&Site=Ngaruroro%20River%20at%20Fernhill&Measurement=Stage&TimeInterval=PT2H/now` | HBRC open data, CC BY 4.0; HBRC asks app developers to share a link with them | `river.py` |
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
| `data/sample_farm.geojson` | **Fictional** farm | Paddock `elevation_m` and `river_elevation_m` (20 m) are placeholders. |
| `data/elevation_cache.json` | **Real** | nzdem8m elevations at each paddock centroid, fetched 2026-11-21 from Open Topo Data (LINZ, CC BY 4.0). Rebuild with `load_or_refresh_cache(farm.paddocks, refresh=True)`. |
| `data/replay_warning.xml` | **Sample** (status "Exercise", headline starts "SAMPLE") | Not a real MetService warning. See the record below. |
| `tests/fixtures/hilltop_fernhill_stage_real.xml` | **Real** | HBRC Stage at Fernhill, 24 h to 2026-11-21 12:05 NZDT (river steady, about 2.73 m). |
| `tests/fixtures/hilltop_rising_sample.xml` | **Sample** (hand-made) | Same format, showing a rising river, for tests. |

### Elevation caution

Real nzdem8m heights at the river line are about 30–37 m, and the paddock centroids are
30.8–55.1 m. The farm file still says `river_elevation_m: 20`. If the real paddock heights
are used with that placeholder river height, every paddock is more than 10 m "above the
river" and scores green. Whoever switches the app to cached elevations should also set the
river height from a real lookup. The lowest river point, about 29.6 m, gives a sensible spread:
paddocks 1, 2, 3, 5 and 6 sit 1–4 m above the river, paddock 4 about 7 m, and paddocks 7–9
sit 10–25 m above it.

## Replay warning record

| Field | Value |
|---|---|
| Source URL | None yet. `https://alerts.metservice.com/cap/rss` was checked on 2026-11-21 and had **no active warnings**. No archived MetService CAP file could be found. |
| Issued | n/a (sample dated 2026-02-12) |
| Event / level | Heavy Rain, Red (sample) |
| Area | Rectangle lat -39.50 to -39.75, lon 176.55 to 176.95. Covers the sample farm (tested). |
| Saved on | n/a |

To replace it: when a Hawke's Bay heavy-rain warning is active, open the feed, save the
linked CAP XML over `data/replay_warning.xml`, run `pytest tests/test_cap_real.py` (checks
the level, the labelling and that the polygon covers the farm), and fill in this table.
