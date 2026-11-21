# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary, today:** hackathon judges watching a 3-minute pitch on a projector (GDG "Best Build for Aotearoa"). They see the demo path once and need to understand it from the back of the room.
- **Intended:** New Zealand pastoral farmers (e.g. Hawke's Bay sheep, beef and dairy) and their farm staff, in the hours before a heavy-rain or flood event, deciding paddock by paddock where stock should go and by when. Often tired, early morning, possibly on a phone.

## Product Purpose

Turns an official severe-weather warning into a per-paddock plan: colours each paddock green, amber or red by flood risk, names the paddock to move the herd to and the deadline ("Move the herd to Paddock 7 by 4pm"), and writes a short storm checklist the team can copy as a text or print for the shed wall. Success: a farmer acts earlier, with a plan everyone on the farm shares.

## Positioning

Warnings are issued per region; the farmer's decision is per paddock. HighGround joins the MetService warning, the farm's own terrain (height above and distance to the river) and the river gauge into one instruction, with a plain, checkable reason for every colour. The AI only rewrites facts it is given.

## Operating Context

- Demo path that must always work: load the sample farm → **Replay warning** → river paddocks turn red → banner shows the move and deadline → **Show plan** → **Copy as text** → **About**.
- Modes: calm, replay (a saved sample warning, times shifted to now, labelled REPLAY), live (real MetService CAP feed; may be unavailable).
- The demo must work offline (no map tiles, no live data).

## Capabilities and Constraints

- API: `GET /api/farm` (GeoJSON paddocks, river LineString, shed Point), `GET /api/assess?mode=` (warning, per-paddock score/band/reason, recommendation, plan, river reading, live_status, server-formatted NZ time labels).
- The UI never formats times itself; it shows server labels.
- Paddock names and the recommended paddock come from the API; never hard-coded.
- Stack: Vite + React + TypeScript. The farm is drawn as plain SVG (no Leaflet, no map tiles).

## Brand Commitments

- Name: HighGround. Tagline (README): "Know where your herd should be before the river rises."
- **Safety line on every screen, verbatim:** "Official MetService warnings and Civil Defence advice always come first. This is guidance, not a guarantee."
- Anything from the replay warning is labelled **REPLAY**.
- Risk meaning stays a traffic-light code: green = low, amber = watch, red = move stock out.
- Data credited: MetService, LINZ via Open Topo Data, Hawke's Bay Regional Council, OpenStreetMap.
- Any te reo Māori is checked with a speaker and credited.
- Tone: respectful of real flood loss (Cyclone Gabrielle); no flood imagery, no unchecked figures.

## Evidence on Hand

- `data/sample_farm.geojson`: a **fictional** 9-paddock farm on the Ngaruroro River, Hawke's Bay.
- `data/replay_warning.xml`: sample CAP warning.
- No farmer quote yet (`docs/farmer-interview.md` is TBD). No screenshots, testimonials or usage figures exist; do not fabricate them.

## Product Principles

1. One clear instruction beats a dashboard: the move and the deadline come first.
2. Every colour has a reason a farmer can check.
3. Official warnings come first; HighGround is guidance.
4. The demo never depends on the network.
5. Plain words for tired people.

## Accessibility & Inclusion

- Projector legibility: key text readable from ~10 m; high contrast.
- Risk is never colour-only: bands carry words (and the popup/list carries the reason).
- Works at 375 px wide with ≥44 px tap targets.
