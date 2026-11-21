# Bugs

Owner: Teammate 5 (QA). Every bug found in integration runs. P1 and P2 bugs each have a GitHub issue.

**Severity:** P1 = breaks the demo path · P2 = visible or breaks a hard rule · P3 = minor or polish

**Owners:** T1 UI (`App.tsx`, `styles.css`, `api.ts`, `components/FarmMap.tsx`) · T2 Data (`data/`, `cap.py`, `elevation.py`, `river.py`) · T3 Logic (`risk.py`, `plan.py`, `main.py`, `farm.py`) · T4 Story (`About.tsx`, `SharePlan.tsx`, pitch, README) · Prasish (repo settings)

Last updated: 2026-11-21 15:25 NZDT

## Open

| ID | Sev | Area | Owner | Steps to reproduce | Status |
|---|---|---|---|---|---|
| BUG-007 | P3 | Map | T1 | On main (Leaflet), offline, the map background is grey. | **Fixed by #19** (drawn map, zero network requests). Closes when #19 merges |
| BUG-012 | P3 | Polish | T1 | The recommended paddock isn't marked on the map. | **Fixed by #19** ("herd here" cow on the recommended paddock) |
| BUG-013 | P3 | Docs | T4 | README says "16 tests" (main now 143) and "Four Claude teammates" (five). | Open |
| BUG-014 | P3 | Precision | T1 | Popup/card shows "risk 77/100", suggesting false precision. Still in #19's card. | Open |
| BUG-016 | P3 | Map | T1 | The Leaflet map re-fits on every `resize`, undebounced. | **Goes away with #19** (no Leaflet) |
| BUG-017 | P3 | Mobile | T1 | With #19 at 375×812: Replay → the red (MOVE OUT) row starts below the fold, because the banner + safety line come first. The projector view is fine. | New |
| BUG-018 | P3 | Process | T3 | #17 edited `tests/test_demo_path.py` (QA file). The change was correct (accepts "at river level"). | Noted; please ask QA next time |

## Resolved

| ID | Sev | What | How |
|---|---|---|---|
| BUG-001 | P1 | Map blank after #4 (fixed centre 5 km away) | #14 (`FitToFarm`) merged before #4; 38/38 on main. [#6](https://github.com/prasish01/highground/issues/6) |
| BUG-002 | P2 | Deadline in server time ("4am" on UTC) | #2. [#7](https://github.com/prasish01/highground/issues/7) |
| BUG-003 | P2 | Copied replay plan had no REPLAY line | #14. [#8](https://github.com/prasish01/highground/issues/8) |
| BUG-004 | P2 | Replay scores followed the live river gauge | #15 (QA verified with a stubbed rising gauge). [#9](https://github.com/prasish01/highground/issues/9) |
| BUG-005 | P2 | Gemini had no timeout or cache | #15 (8 s budget, cache). [#10](https://github.com/prasish01/highground/issues/10) |
| BUG-006 | P2 | Pitch said "saved MetService warning" for a sample | #13. [#11](https://github.com/prasish01/highground/issues/11) |
| BUG-008 | P3 | "-1 m above river" | #17: "at river level" / "N m below river level" |
| BUG-009 | P3 | Shed circle filled green | #14 |
| BUG-010 | P3 | `*.tsbuildinfo` not ignored | d0932c1 |
| BUG-011 | P3 | `package-lock.json` ownership | Settled with #1 |
| BUG-015 | P3 | PR #3 duplicated #5 | #3 closed |
| — | P1 | PR #4 gave no red paddocks with real heights | T2 redrew the farm beside the real Ngaruroro |
| — | P3 | QA e2e popup check flaky with Leaflet re-fit | Test waits for the map to settle after screenshots; retries logged |
