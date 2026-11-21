# 3-minute pitch script

Total: 3:00. One speaker talks, one person clicks (see `docs/demo-checklist.md`).
Times are cumulative. Lines in quotes are said out loud; lines in *italics* are actions.

Before starting: app open on the sample farm in **calm** mode (all paddocks green), side panel showing the paddock list.

---

## 0:00 – 0:20 · Hook

"In February 2023, Cyclone Gabrielle reached Hawke's Bay. Many farmers had to decide where to move their animals with little time and limited information."

"We built HighGround for that moment: the hours before the water arrives."

> Keep it respectful. No flood photos, no figures we haven't checked. If quoting any Gabrielle statistic, cite the source on the slide: [TBD source].

## 0:20 – 0:40 · Problem

"Warnings are issued for a region. But the decision a farmer makes is paddock by paddock: which paddocks are at risk, where the herd goes, and by when."

"Today that means joining up the MetService warning, the council river page and memory of the last flood."

## 0:40 – 2:10 · Demo (90 s)

| Time | Click | Say |
|---|---|---|
| 0:40 | *(nothing — point at the map)* | "This is a sample farm on the Hawke's Bay plains. It's fictional, but the river and the data sources are real." |
| 0:50 | *Click **Replay warning*** | "This is a saved MetService heavy-rain warning, replayed with its times shifted to now. You can see it's labelled REPLAY." |
| 1:00 | *(point at the red paddocks)* | "The paddocks low and close to the river turn red. Higher ground stays green." |
| 1:10 | *(point at the banner)* | "And the banner gives one clear instruction: move the herd to [paddock shown], by [time shown]." |
| 1:20 | *Hover or click a red paddock by the river* | "Every colour has a reason: [read the reason shown, e.g. height above river and distance]. It's simple rules you can check, not a black box." |
| 1:35 | *Click **Show plan*** | "Gemini turns those facts into a short plan a tired person can follow at 5am: the moves with times, and a checklist." |
| 1:50 | *Click **Copy as text*** (wait for "Copied") | "One tap copies it as a text message for the farm team. Or print it for the shed wall." |
| 2:00 | *(point at the footer)* | "And on every screen: official MetService warnings and Civil Defence advice always come first. This is guidance, not a guarantee." |

> Read the paddock name, time and reasons off the banner and map. Don't memorise them: replay shifts the times to "now", and the recommended paddock may change once the farm is redrawn on real terrain.

## 2:10 – 2:35 · How it works

"Real New Zealand data: MetService warnings, LINZ elevation data, and Hawke's Bay Regional Council river gauges."

"The risk score is plain code: low ground and closeness to the river, scaled by the warning level. Gemini only writes the plan from facts we give it. It isn't allowed to add any."

## 2:35 – 2:45 · A real farmer

"We asked a farmer how they decide where stock go when a warning comes. They told us: [TBD: farmer quote, used with permission — see `docs/farmer-interview.md`]."

> No quote yet? Cut this section and give the 10 s to "What's next". Never paraphrase someone we haven't spoken to.

## 2:45 – 3:00 · What's next and close

"Next: an alert when a warning covers your farm, drawing your own paddocks, more regions, and working with councils and Civil Defence."

"HighGround: know where your herd should be before the river rises."

---

## Likely judge questions

**How accurate is it?**
It's guidance from public data with simple, visible rules, and official advice always comes first. Elevation comes from an 8 m model built from LINZ data, so it can miss small dips and banks; LINZ 1 m LiDAR is the upgrade. Each paddock shows the reason for its colour so a farmer can disagree with it. [TBD: if the team checks results against real flood extents, say what was checked.]

**Why not just use the MetService app?**
MetService tells you a region is at risk, and it should stay the first source. HighGround starts from that warning and answers the next question: which of my paddocks, where do the animals go, and by when.

**What does Gemini do?**
It rewrites facts our code has already worked out (paddock names, colours, the recommended paddock and the deadline) into a plain-language plan and checklist. The prompt forbids adding facts. Risk scores, times and the recommendation come from code. Without a key or network, a built-in template writes the plan instead, so the demo works offline.

**Where does the data come from?**
MetService CAP warnings; Toitū Te Whenua LINZ elevation via Open Topo Data (CC BY 4.0); Hawke's Bay Regional Council river levels (CC BY 4.0); OpenStreetMap map data. The demo farm is fictional and the replayed warning is labelled. Full list: `docs/data-sources.md`.

**Is the warning in the demo real?**
"This is a replay of a sample warning in the official MetService format; live mode checks the real MetService feed."

> If Teammate 2 saves a real past MetService warning into `data/replay_warning.xml`, update this answer with its source and issue date from `docs/data-sources.md`: [TBD].

**How did you decide the deadline?**
Warning onset minus three hours, so there's daylight and time to muster. It's a setting in the code, and a farmer would tune it to their own farm.

**What's next?**
Alerts when a warning covers your farm, draw-your-own-paddocks, more regions and river gauges, LiDAR elevation, and talking with councils and Civil Defence about how it fits alongside their advice.

**What did you build during the hackathon?**
See the "Built during the hackathon" section of the README. Be upfront about what was prepared beforehand (idea, docs, data research).
