# HighGround — hackathon plan

**Goal:** a demo that works every time, with real NZ data behind it and a real farmer's voice in the pitch.

## Before the event

- [ ] **Check the rules.** Many hackathons require code to be written during the event. If so, keep this repo private until the start and be upfront with judges about what was prepared beforehand (idea, docs, data research) and what was built on the day.
- [ ] Get a Gemini API key from AI Studio and put it in `.env`.
- [ ] Save a real MetService CAP warning (ideally a past heavy-rain warning for Hawke's Bay) to replace `data/replay_warning.xml`. Note the source and issue date in `docs/data-sources.md`.
- [ ] Message one farmer (or rural contact) for a 10-minute chat: "When a red warning comes, how do you decide where the stock go?" Ask permission to quote them.

## Phase 1 — Make the scaffold run (≈1 h)

- [ ] `pytest` passes (16 tests)
- [ ] API runs: `/api/assess?mode=replay` returns red paddocks and "Move the herd to Paddock 7 by …"
- [ ] UI runs: map shows the farm, Replay turns paddocks red, banner appears, plan shows
- **Checkpoint:** the full demo path works end to end on your laptop

## Phase 2 — Real data (≈3–4 h)

- [ ] Replace the sample replay warning with a real saved CAP file
- [ ] Live elevation: on startup, look up each paddock centroid with `elevation.lookup_elevations`, cache to `data/elevation_cache.json`, fall back to the GeoJSON values
- [ ] Gemini plan working with your key; check it never adds facts
- [ ] Live mode: show "No active warnings for this farm" gracefully when there are none
- **Checkpoint:** replay uses a real warning; elevations come from LINZ data

## Phase 3 — River gauge (≈2–3 h, stretch)

- [ ] Fetch the latest Ngaruroro River at Fernhill level from HBRC Hilltop (see data-sources)
- [ ] Rising = last hour higher than the hour before → pass `river_rising=true`
- [ ] Show the gauge reading and trend in the side panel
- **Checkpoint:** a rising river visibly raises scores

## Phase 4 — Polish (≈2–3 h)

- [ ] About screen with data credits and the safety statement
- [ ] Share: copy plan as text, print view
- [ ] Paddock click → shows its score and reason
- [ ] Mobile layout check
- [ ] Draw-your-own-paddocks (only if everything else is done)

## Phase 5 — Pitch (≈2 h)

- [ ] Rehearse the 3-minute pitch three times (`docs/pitch.md`)
- [ ] Record a backup video of the demo path
- [ ] Freeze the code 1 hour before judging; only fix demo-breaking bugs

## Team roles (if in a team)

| Role | Owns |
|---|---|
| Map + UI | `web/`, the demo flow, polish |
| Data | CAP replay/live, elevation, river gauge |
| Logic + AI | `risk.py`, recommendation, Gemini prompt |
| Story | farmer conversation, pitch, backup video |

## Cut list if time runs short

River gauge → draw-your-own-paddocks → live mode. **Never cut:** replay, red paddocks, the move banner, the plan, the safety line.
