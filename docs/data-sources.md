# Data sources

| Data | Source | Licence / terms | Used in |
|---|---|---|---|
| Severe weather warnings | MetService CAP feed: `https://alerts.metservice.com/cap/rss` (RSS list of CAP 1.2 files) | MetService terms; credit MetService | `cap.py`, `main.py` (live mode) |
| Earthquakes (optional) | GeoNet CAP: `https://api.geonet.org.nz/cap/1.2/GPA1.0/feed/atom1.0/quake` | GeoNet terms; credit GNS Science / GeoNet | not yet used |
| Elevation | Open Topo Data public API, dataset `nzdem8m`: `https://api.opentopodata.org/v1/nzdem8m?locations=lat,lng` (8 m DEM from LINZ topo contours). Upgrade path: LINZ 1 m LiDAR DEM | LINZ CC BY 4.0; check Open Topo Data's public-API usage limits | `elevation.py` |
| River levels | Hawke's Bay Regional Council Hilltop server, e.g. `https://data.hbrc.govt.nz/Envirodata/EMAR.hts?service=Hilltop&request=GetData&Site=Ngaruroro River at Fernhill&Measurement=Flow[Water Level]` | HBRC open data, CC BY 4.0; HBRC asks app developers to share a link with them | planned (Phase 3) |
| Base map | OpenStreetMap tiles | ODbL; © OpenStreetMap contributors | `web/src/App.tsx` |

## Sample data in this repo

- `data/sample_farm.geojson` — a **fictional** farm on the Hawke's Bay plains. Paddock elevations are placeholders until replaced by live lookups.
- `data/replay_warning.xml` — a **sample** CAP warning (status "Exercise"). Replace with a real saved MetService CAP file before the demo and record it below.

## Replay warning record

| Field | Value |
|---|---|
| Source URL | [TBD] |
| Issued | [TBD] |
| Event / level | [TBD] |
| Saved on | [TBD] |
