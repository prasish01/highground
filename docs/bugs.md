# Bugs

Owner: Teammate 5 (QA). Every bug found in integration runs. P1 and P2 bugs each have a GitHub issue.

**Severity:** P1 = breaks the demo path · P2 = visible or breaks a hard rule · P3 = minor or polish

**Owners:** T1 UI (`App.tsx`, `styles.css`, `api.ts`) · T2 Data (`data/`, `cap.py`, `elevation.py`, `river.py`) · T3 Logic (`risk.py`, `plan.py`, `main.py`, `farm.py`) · T4 Story (`About.tsx`, `SharePlan.tsx`, pitch, README) · Prasish (repo settings)

Last updated: 2026-11-21 14:25 NZDT

## Open

| ID | Sev | Area | Owner | Steps to reproduce | Status |
|---|---|---|---|---|---|
| BUG-001 | **P1** | Map | T1 | Merge #4 without #14 → Replay → the map is empty (0/10 shapes on screen). | **Fix in #14, verified** (38/38 ×3 with #14 → #4): [#6](https://github.com/prasish01/highground/issues/6). Closes when #14 merges |
| BUG-003 | P2 | Share | T1 | `SharePlan` used without `isReplay` → copied replay plan has no REPLAY line. | **Fix in #14, verified** (copied text has REPLAY): [#8](https://github.com/prasish01/highground/issues/8) |
| BUG-004 | P2 | API | T3 | Replay scores followed the live HBRC gauge when `river_rising` was omitted. | **Fix in #15, verified** (stubbed rising gauge: replay bands unchanged; explicit `true` still applies): [#9](https://github.com/prasish01/highground/issues/9) |
| BUG-005 | P2 | Plan | T3 | Gemini had no timeout and no cache, so slow wifi could stall Replay. | **Fix in #15, verified by its tests** (8 s budget, cache, no Gemini when there's no warning): [#10](https://github.com/prasish01/highground/issues/10) |
| BUG-006 | P2 | Pitch | T4 | Pitch called the replay "a saved MetService warning"; the banner says SAMPLE. | **Fix in #13** (wording checked): [#11](https://github.com/prasish01/highground/issues/11) |
| BUG-007 | P3 | Map | T1 | Offline (no tiles) the map background is grey. The coloured paddocks still work. | Open |
| BUG-008 | P3 | Wording | T3 | With #4 heights, Paddock 1 reads "-1 m above river". Say "1 m below river". QA tests already accept "below". | Open |
| BUG-012 | P3 | Polish | T1 | The recommended paddock isn't marked on the map; names only show on hover. | Open |
| BUG-013 | P3 | Docs | T4 | README says "16 tests" (main now 76; 132 with all PRs) and "Four Claude teammates" (five). | Open |
| BUG-014 | P3 | Precision | T1 | Popup "risk 77/100" suggests false precision; band words + reason are enough. | Open |
| BUG-016 | P3 | Map | T1 | #14 re-fits the map on every window `resize`, undebounced. A tap during the re-fit animation misses (found via a full-page screenshot in e2e), and any resize snaps back a presenter's manual zoom. Suggest debouncing ~250 ms and only re-fitting if the size really changed. | New |

## Resolved

| ID | Sev | What | How |
|---|---|---|---|
| — | P1 | PR #4 on hold: real heights gave no red paddocks | T2 redrew the farm beside the real Ngaruroro; 3 red, 1 green |
| BUG-002 | P2 | Deadline in server time ("4am" on UTC) | Merged in #2. `test_banner_time_is_nz_time_whatever_the_server_clock` now runs as a normal test on main ([#7](https://github.com/prasish01/highground/issues/7)) |
| BUG-009 | P3 | Shed circle filled green | Fixed in #14 (grey shed), seen in screenshots |
| BUG-010 | P3 | `*.tsbuildinfo` not ignored | Added to `.gitignore` on main (d0932c1) |
| BUG-011 | P3 | `web/package-lock.json` ownership | Merged with #1; no more merge snags this run |
| BUG-015 | P3 | PR #3 duplicated #5 | #3 closed, #5 merged |
| — | P3 | QA e2e popup check flaky with #14 | Test artefact: the full-page screenshot resized the viewport → map re-fit. The test now waits for the map to settle after screenshots and retries the click (logs retries). |
