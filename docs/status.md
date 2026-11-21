# QA status

**2026-11-21 14:25 NZDT** · Teammate 5 (QA + Direction) · overwritten each check-in

## Overall: 🟢 Green

- **main 🟢:** demo path 38/38 at 1366px and 375px; 76 tests pass; NZ time is correct on a UTC server.
- **All open PRs merged together 🟢:** 132 tests pass, no merge conflicts, 38/38 browser checks (run twice).
- **#4 is safe to merge immediately after #14,** and not before. #4 alone still blanks the map (0/10 shapes on screen). #14 then #4: 38/38 in three runs out of three.

## Demo path, step by step (main + #15 + #13 + #14 + #4)

| Step | Desktop 1366 | Mobile 375 | Notes |
|---|---|---|---|
| Sample farm loads, map fits the farm | ✅ | ✅ | 9/9 paddocks on screen (`fitBounds`, #14) |
| Replay warning → REPLAY label | ✅ | ✅ | Banner also shows "Warning 9:24pm – 3:24pm" |
| ≥ 2 red near river, ≥ 1 green | ✅ | ✅ | 3 red (P1–P3), 5 amber, 1 green (P7) |
| Banner "Move the herd to Paddock N by time" | ✅ | ✅ | "Move the herd to Paddock 7 by 6pm" (NZ time on a UTC container) |
| Paddock popup shows reason | ✅ | ✅ | Opens on the first tap; fits inside the map at 375px |
| Show plan: moves + checklist | ✅ | ✅ | REPLAY note shown first, 2 moves, 7 items |
| Copy / Print | ✅ | ✅ | Copied text has REPLAY + safety line (#8 fixed) |
| About shows credits | ✅ | ✅ | Real About component: MetService, LINZ, Open Topo Data, HBRC, OSM |
| Safety line on every screen | ✅ | ✅ | |
| Live mode offline | ✅ | ✅ | "LIVE WARNINGS UNAVAILABLE", never "all clear" |
| No horizontal scroll / no JS errors | ✅ | ✅ | |

## Tests

| Where | Merge | ruff + format | pytest | Browser (38 checks) |
|---|---|---|---|---|
| main | — | ✅ | 76 passed (the NZ-time test now runs as a normal test) | 38/38 |
| main + #13 | clean | ✅ | 76 passed | — |
| main + #14 | clean | ✅ | 76 passed | 38/38 |
| main + #15 | clean | ✅ | 88 passed | — |
| main + #4 | clean | ✅ | 120 passed | **34/38**: map blank (why #4 is held) |
| main + #14 + #4 | clean | ✅ | — | **38/38 ×3** |
| main + all four | clean | ✅ | **132 passed** | **38/38 ×2** |

`npm run build` ✅ on main and on the full integration.

**QA test change this run:** a full-page screenshot in `web/e2e/demo-path.cjs` briefly resizes the viewport. #14 re-fits the map on resize, so the next click sometimes landed mid-animation. I proved this is a test artefact (screenshot before the click: misses 2/2; no screenshot: opens 2/2). The test now waits for the map to settle after screenshots and retries the popup click up to 3 times, logging any retry. None were needed in the final runs.

## Open PRs and merge order

| Order | PR | Owner | Verdict |
|---|---|---|---|
| 1 | #14 UI: fit map to farm, real About/SharePlan, grey shed, server time labels | T1 | ✅ ready. Closes #6, #8 |
| 2 | **#4 Data: real-terrain farm** | T2 | ✅ **merge right after #14** |
| 3 | #15 Logic: replay ignores live gauge, Gemini timeout + cache | T3 | ✅ ready. Closes #9, #10 (order-independent) |
| 4 | #13 Story: "sample warning" wording | T4 | ✅ ready. Closes #11 (order-independent) |

The branch `claude/nifty-bohr-q6fcnu` is superseded by #14 (cherry-picked with the `isReplay` fix) and can be deleted.

## Top 3 risks

1. **Merging #4 before #14** → blank map on stage. Merge #14 first and re-run the e2e once after both.
2. **Map tiles need internet:** offline, the background is a grey box (BUG-007). The coloured paddocks still show. Rehearse once with wifi off.
3. **No farmer quote yet:** judging angle (e). The pitch cuts that section if there's no consent.

## P1 / P2 bugs

- No open P1s.
- P1 #6 and P2 #8 fixed in #14 (verified); P2 #9 and #10 fixed in #15 (verified, see review); P2 #11 fixed in #13; P2 #7 fixed on main (#2).

Full list: [`docs/bugs.md`](bugs.md).

## Direction check (judging angles)

| Angle | Status | Note |
|---|---|---|
| (a) Real NZ data, credited | 🟡 | Real LINZ heights, OSM river and HBRC gauge (after #4), all credited. The replay warning is honestly labelled a **sample** in the app and the pitch (#13). |
| (b) One wow moment, offline | 🟢 | Red paddocks + banner work with the network blocked; replay no longer depends on the live river (#15). Only the tiles need wifi. |
| (c) Responsible | 🟢 | Safety line everywhere, REPLAY on screen and in copied text, Gemini validated with an 8 s budget and template fallback. |
| (d) Polish: projector + mobile | 🟢 | The map fits itself, the shed is grey, the popup fits at 375px. Remaining P3s: "-1 m above river", "risk 77/100". |
| (e) Real user voice | 🔴 | Still no farmer quote. |

**Scope:** no scope creep. Draw-your-own-paddocks hasn't started, which is right. Cut list: river gauge → draw-your-own paddocks → live mode. **Never cut:** replay, red paddocks, banner, plan, safety line.

## Next actions

- **Prasish:** merge **#14 → #4**, then #15 and #13 (any order); delete the `nifty-bohr` branch; book the farmer chat.
- **Teammate 1 (UI):** P3s: debounce the resize re-fit (BUG-016); "risk 77/100" → band words (BUG-014); mark the recommended paddock on the map (BUG-012).
- **Teammate 2 (Data):** after #4 merges, consider `river.observed_label` (requested in #14).
- **Teammate 3 (Logic):** "-1 m above river" → "1 m below river" (BUG-008).
- **Teammate 4 (Story):** README test count and team size (BUG-013); add the screenshot once #4 is on main.
- **Teammate 5 (QA):** re-run the full e2e on main as soon as #14 and #4 are merged; then a wifi-off rehearsal check.
