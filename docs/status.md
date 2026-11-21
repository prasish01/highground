# QA status

**2026-11-21 16:20 NZDT** · Teammate 5 (QA + Direction) · overwritten each check-in

## Overall: 🟢 Green

- **main 🟢 with #19 merged** (hand-drawn map; rollback tag `pre-redesign` exists). 143 tests pass; demo path **42/42** at 1366px and 375px (run twice), including QA's independent checks (bands match the API, washes really red/green).
- **Fully offline on main:** with the page loaded and Replay pressed, **zero requests leave localhost**. This is the wifi-off rehearsal check, done in the browser.
- **#20 (Leaflet removed, Presentation mode, BUG-014/017 fixes): ✅ ready.** With #20 + #16 on main: 143 tests, demo path **42/42 ×2** normal and **42/42** in Presentation mode, their `presentation.cjs` 18/18, zero external requests.
- **#16 (this QA PR):** up to date with main; merges cleanly with #20. **Ready to merge.** #20 and #16 can go in either order.
- **UI freeze from now:** fixes only. Re-run `node web/e2e/demo-path.cjs` after every merge.

## Demo path, step by step (main, with #19)

| Step | Desktop 1366 | Mobile 375 | Notes |
|---|---|---|---|
| Sample farm loads | ✅ | ✅ | Drawn map, 9 paddocks, river, shed, scale bar, north arrow |
| Replay warning → REPLAY label | ✅ | ✅ | Rubber-stamped REPLAY in the banner |
| ≥ 2 red near river, ≥ 1 green | ✅ | ✅ | 3 MOVE OUT, 5 WATCH, 1 SAFE. Bands match the API, paddock by paddock; washes really are red and green |
| Banner "Move the herd to Paddock N by time" | ✅ | ✅ | "Move the herd to Paddock 7 by 7pm", plus a "herd here" cow on Paddock 7 |
| Paddock card shows reason | ✅ | ✅ | "MOVE OUT · at river level, 289 m from river, inside red warning" |
| Show plan: moves + checklist | ✅ | ✅ | REPLAY note first |
| Copy / Print | ✅ | ✅ | Copied text has REPLAY + safety line |
| About shows credits | ✅ | ✅ | MetService, LINZ, Open Topo Data, HBRC, OSM (river line) |
| Safety line on every screen | ✅ | ✅ | Pinned at the bottom on desktop; under the banner on phones |
| Works offline | ✅ | ✅ | No requests leave localhost (fonts self-hosted, no tiles) |
| No horizontal scroll / no JS errors | ✅ | ✅ | |

On main today (Leaflet map) the same path is 38/38, with tiles needing wifi.

## Tests

| Where | Merge | ruff + format | pytest | Browser |
|---|---|---|---|---|
| main before #19 | — | ✅ | 143 passed | 38/38 ×2 (Leaflet) |
| **main now (with #19)** | — | ✅ | **143 passed** | **42/42 ×2** (drawn; incl. 4 QA independent checks) |
| main + #16 (this PR) | clean (conflict resolved here) | ✅ | 143 passed | 42/42 (same test) |
| main + #20 + #16 | clean | ✅ | 143 passed | **42/42 ×2** normal, **42/42** `?present=1`, presentation.cjs 18/18 |

`npm run build` ✅ on both (bundle 305 kB → 164 kB JS with #19, as Leaflet is no longer used).

**QA test change this run:** `web/e2e/demo-path.cjs` now detects which map is on the page (Leaflet or drawn) and runs the same checks on either. On the drawn map it adds two checks that don't rely on the map's own markup: bands match `/api/assess` for every paddock, and red/green washes are really painted red/green.

## PRs merged since last check-in without a QA run (re-checked now on main)

- **#17** (Logic): "at river level" / "N m below river level" (fixes BUG-008), and `river.observed_label`. ✅ on main. It also edited `tests/test_demo_path.py` (a QA file) to accept "at river level". The change is correct; next time please ask QA or leave a note.
- **#18** (UI): river panel says when a reading is live during replay. ✅ on main.

## Open PRs and merge order

| Order | PR | Owner | Verdict |
|---|---|---|---|
| 1 | #20 UI follow-ups: remove Leaflet, Presentation mode, BUG-014/017 | T1 | ✅ ready (either order with #16) |
| 2 | #16 QA status (this PR) | T5 | ✅ ready: QA files only, up to date with main |

## Top 3 risks

1. **Late changes:** #19 (+1220 lines) is in and passes everything. Any further UI change risks the demo; **freeze UI features**, fixes only, and re-run the e2e after every merge. Rollback point: tag `pre-redesign`.
2. **Phone: red paddocks start below the fold** with #19 (banner + safety line push the map down at 375×812). Fine on the projector; a phone viewer must scroll (BUG-017, P3).
3. **No farmer quote yet:** judging angle (e).

## P1 / P2 bugs

None open. All issues #6–#11 are fixed on main.

Full list: [`docs/bugs.md`](bugs.md).

## Direction check (judging angles)

| Angle | Status | Note |
|---|---|---|
| (a) Real NZ data, credited | 🟢 | LINZ heights, OSM river, HBRC gauge (with "live reading" label in replay), MetService format; sample warning labelled honestly |
| (b) One wow moment, offline | 🟢 | With #19: stamps press on paddock by paddock, nothing needs the network |
| (c) Responsible | 🟢 | Safety line pinned on every screen, REPLAY everywhere, Gemini validated with timeout, "at river level" instead of false precision |
| (d) Polish: projector + mobile | 🟢 | #19 is legible from the back of the room; phone needs one scroll to see the reds |
| (e) Real user voice | 🔴 | Still no farmer quote |

**Scope:** #19 is a big change late in the day, but it serves angles (b) and (d) directly and removes the tile dependency, so I'd take it. **After #19, no more redesigns.** Cut list unchanged; draw-your-own-paddocks still not started (good).

## Next actions

- **Prasish:** merge #20 and #16; **then freeze UI**; record the backup demo video in Presentation mode (`/?present=1`); book the farmer chat.
- **Teammate 1 (UI):** all QA notes done in #20 🎉. After it merges: fixes only.
- **Teammate 2 (Data):** nothing blocking. 🎉
- **Teammate 3 (Logic):** nothing blocking. Please leave QA files to QA (or ping first).
- **Teammate 4 (Story):** match About/SharePlan to #19's shared styles (requested in #19); README test count (BUG-013); add the screenshot now the farm is final.
- **Teammate 5 (QA):** re-run the e2e after every merge; final check before code freeze (1 h before judging).
