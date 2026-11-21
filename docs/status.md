# QA status

**2026-11-21 14:00 NZDT** · Teammate 5 (QA + Direction) · overwritten each check-in

## Overall: 🟡 Amber

- **main is 🟢:** the demo path works (2 red, 6 green, banner, plan), but times are in the server's zone (BUG-002, fixed by PR #2).
- **The integrated build is 🔴 until BUG-001 is fixed:** with all PRs merged, the map shows no paddocks (it's centred 5 km from the redrawn farm). Everything else passes. With the map centred on the farm, all 38 browser checks pass at 1366px and 375px.

## Demo path, step by step (all open PRs merged: #2, #4, #1, #3, #5)

| Step | Desktop 1366 | Mobile 375 | Notes |
|---|---|---|---|
| Sample farm loads | ✅ | ✅ | 9 paddocks, river, shed |
| Replay warning → REPLAY label | ✅ | ✅ | |
| ≥ 2 red near river, ≥ 1 green | ✅ data / ❌ **on screen** | ✅ / ❌ | API: 3 red, 5 amber, 1 green. Map: 0/10 shapes in view (BUG-001) |
| Banner "Move the herd to Paddock N by time" | ✅ | ✅ | "Move the herd to Paddock 7 by 5pm" on a **UTC** container, so NZ time is correct |
| Paddock popup shows reason | ❌ (off-screen) | ❌ | ✅ once centred: "RED · -1 m above river, 289 m from river, inside red warning" |
| Show plan: moves + checklist | ✅ | ✅ | 2 moves, 7 items, template |
| Copy / Print | ✅ | ✅ | Copied text has REPLAY + safety line (but not on the nifty-bohr branch, BUG-003) |
| About shows credits | ✅ | ✅ | MetService, LINZ, Open Topo Data, HBRC, OSM |
| Safety line on every screen | ✅ | ✅ | calm, replay, plan, About |
| Live mode offline | ✅ | ✅ | `live_status: "unavailable"`, amber banner, never "all clear" |
| No horizontal scroll / no JS errors | ✅ | ✅ | |

How to re-run: start the API and `npm run dev`, then `node web/e2e/demo-path.cjs`.

## Tests

| Where | ruff | pytest | npm build |
|---|---|---|---|
| main | ✅ | 16 passed (+ QA: 20 passed, 4 xfail for BUG-002) | ✅ |
| Integration (all PRs) | ✅ + format ✅ | **120 passed** (96 team + 24 QA), no network | ✅ |
| Each PR alone + QA tests | ✅ | all pass: #2, #4, #1, #5, nifty-bohr | ✅ |

Merging: no conflicts between any of the PRs. Only snag: PR #1's `web/package-lock.json` clashes with a local untracked lock.

## Open PRs: review and recommended merge order

| Order | PR | Owner | Verdict |
|---|---|---|---|
| 1 | #2 Logic: Gemini validation, river, NZ time | T3 | ✅ ready (merge now; it fixes BUG-002). Follow-ups #9 and #10 can come in a later PR |
| 2 | #5 UI: live_status banner, NZ-time-safe | T1 | ✅ ready. **Close #3** (contained in #5) |
| 3 | #1 Story: About, SharePlan, pitch | T4 | ✅ ready (fix the pitch line in #11 before rehearsal) |
| 4 | T1: map `fitBounds` fix (#6) + nifty-bohr PR with `isReplay` (#8) | T1 | not opened yet |
| 5 | #4 Data: real terrain farm, LINZ cache, HBRC gauge | T2 | ✅ code ready, but **merge only after step 4**, or the map goes blank |

## Top 3 risks

1. **Blank map after the Data merge** (BUG-001). It's a one-line fix, but it must land before #4.
2. **Live data creeping into the demo:** replay scores follow the real river (#9), Gemini has no timeout (#10), and map tiles need wifi (BUG-007). Rehearse once with wifi off.
3. **Pitch honesty gaps:** the replay warning is still a SAMPLE (#11), and there's no farmer quote yet (judging angle e).

## P1 / P2 bugs

- P1 [#6](https://github.com/prasish01/highground/issues/6) T1: map centred away from the farm
- P2 [#7](https://github.com/prasish01/highground/issues/7) T3: UTC deadline on main (fixed in PR #2)
- P2 [#8](https://github.com/prasish01/highground/issues/8) T1: SharePlan without `isReplay`
- P2 [#9](https://github.com/prasish01/highground/issues/9) T3: replay depends on the live river gauge
- P2 [#10](https://github.com/prasish01/highground/issues/10) T3: Gemini has no timeout or cache
- P2 [#11](https://github.com/prasish01/highground/issues/11) T4: pitch says "saved MetService warning" for a sample

Full list, including P3s: [`docs/bugs.md`](bugs.md).

## Direction check (judging angles)

| Angle | Status | Note |
|---|---|---|
| (a) Real NZ data, credited | 🟡 | Real LINZ heights, OSM river and HBRC gauge, all credited in About and data-sources. The replay **warning** is still a sample, because MetService had no active warnings. Say so plainly. |
| (b) One wow moment, offline | 🟡 | Red paddocks + banner work offline in the API and UI, but need BUG-001, and the map background is grey without tiles. |
| (c) Responsible | 🟢 | Safety line everywhere; Gemini can't add digits (validated, template fallback); REPLAY labelled. Watch #8 and "risk 77/100" (BUG-014). |
| (d) Polish: projector + mobile | 🟢 | Big banner and high contrast; 375px stacks cleanly with no overflow. |
| (e) Real user voice | 🔴 | The interview guide is ready, but there's no quote yet. Prasish needs to do the 10-minute chat, or the pitch cuts that section. |

**Scope:** no scope creep seen. Draw-your-own-paddocks hasn't started, which is good. Cut list if time runs short: river gauge → draw-your-own paddocks → live mode. **Never cut:** replay, red paddocks, banner, plan, safety line.

## Next actions

- **Teammate 1 (UI):** 🔝 fix #6 (`fitBounds` to the farm), then open the nifty-bohr PR with `isReplay` (#8); close #3.
- **Teammate 2 (Data):** hold #4 until #6 lands; if possible, find a real past MetService CAP file (or confirm none is available) for #11.
- **Teammate 3 (Logic):** follow-up PR for #9 (replay ignores the live gauge) and #10 (Gemini timeout and cache); "below river" wording (BUG-008).
- **Teammate 4 (Story):** fix the pitch line at 0:50 (#11); update the README test count and team size (BUG-013).
- **Prasish:** merge #2 → #5 → #1; add `*.tsbuildinfo` to `.gitignore`; book the farmer chat; decide whether to rehearse with wifi off.
- **Teammate 5 (QA):** re-run integration after the UI fix; then remove the BUG-002 xfail once #2 is merged (it becomes a normal test on its own).
