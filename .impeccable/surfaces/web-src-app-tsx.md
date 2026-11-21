---
version: 1
slug: "web-src-app-tsx"
primary_target: "web/src/App.tsx"
related_targets: ["web/src/components/FarmMap.tsx","web/src/styles.css"]
---

## Scope

The single HighGround app screen (web/src/App.tsx and its components): calm, replay and live states, plan view, About. Visitor mode: Operate. Main scene: a pitch-room projector, read from ~10 m; must still work at 375 px.

## Audience and task

Judges (today) and Hawke's Bay farmers (intended) need one instruction: which paddock the herd goes to, by when, and why each paddock is red, amber or green. Constraints: demo works offline; safety line on every screen; REPLAY always labelled; traffic-light meaning kept; times only from server labels; no hard-coded paddock names.

## Direction contract

THESIS: The farm is a drawn map, not a GIS layer. A warning is *stamped* onto it, paddock by paddock, the way a farm marks woolpacks and gate tags. Refuses the grey slippy-map-plus-sidebar dashboard.

OWN-WORLD: Pale paper-green ground with soft grain; deep woolpack-ink indigo header band; paddocks as loose watercolour washes inside wobbly pencil outlines; river a blue wash with a double ink line. Risk inks: stamp red, ochre amber, field green. Type: Bricolage Grotesque (display, friendly), Atkinson Hyperlegible (body, projector legibility), Saira Stencil One (stamps and paddock numbers only). Icons hand-drawn SVG in one 2px ink stroke.

STORY: In calm, a quiet drawn farm. Press Replay warning: stamps press onto every paddock from the river outward, the header shows a rubber-stamped REPLAY, and the banner states the move in huge type. Tap a paddock for its reason; Show plan opens the shareable checklist.

FIRST VIEWPORT: Indigo header: wordmark left, mode buttons right (Replay warning primary). Below: the move instruction at display size across the full width with the warning window. Main area: the drawn map (~65%) with a stamp legend; side sheet (~35%) with river gauge and paddock list or plan. Safety line footer always visible.

FORM: #7 of 7 (woolpack stencil and ink stamps), translated to the pinned dreamy hand-drawn brief. seed:20e9d34baa4d151b (degraded roll, no challengers).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
