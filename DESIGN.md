---
name: HighGround
description: A drawn farm map with warnings stamped onto it, paddock by paddock.
colors:
  paper: "#e7edd9"
  paper-sheet: "#f6f8ef"
  paper-deep: "#d6dfc4"
  ink: "#1c2450"
  ink-soft: "#414a74"
  ink-line: "#2a2f45"
  muted: "#4e5670"
  stamp-red: "#b3261e"
  stamp-amber: "#8f5a00"
  stamp-green: "#2c6b3c"
  wash-red: "#e0645a"
  wash-amber: "#f0bf55"
  wash-green: "#8fc27a"
  river-wash: "#7fb3e0"
  river-ink: "#2a5c9a"
  shed: "#8a8f99"
  level-red: "#ab2a22"
  level-orange: "#b8560f"
  level-yellow: "#e6be3e"
typography:
  move:
    fontFamily: "Bricolage Grotesque, Atkinson Hyperlegible, system-ui, sans-serif"
    fontSize: "clamp(2rem, 4.4vw, 3.8rem)"
    fontWeight: 800
    lineHeight: 1.02
    letterSpacing: "-0.035em"
  heading:
    fontFamily: "Bricolage Grotesque, Atkinson Hyperlegible, system-ui, sans-serif"
    fontSize: "1.45rem"
    fontWeight: 800
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Atkinson Hyperlegible, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.45
  stamp:
    fontFamily: "Saira Stencil One, Bricolage Grotesque, sans-serif"
    fontSize: "0.85rem"
    fontWeight: 400
    letterSpacing: "0.1em"
rounded:
  stamp: "5px"
  card: "16px"
  sheet: "18px"
  pill: "999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "20px"
  lg: "28px"
components:
  button-primary:
    backgroundColor: "{colors.stamp-red}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "0 22px"
    height: "46px"
  button-on-ink:
    backgroundColor: "transparent"
    textColor: "{colors.paper-sheet}"
    rounded: "{rounded.pill}"
    padding: "0 18px"
    height: "46px"
  button-on-ink-pressed:
    backgroundColor: "{colors.paper-sheet}"
    textColor: "{colors.ink}"
  chip-red:
    backgroundColor: "{colors.paper-sheet}"
    textColor: "{colors.stamp-red}"
    typography: "{typography.stamp}"
    rounded: "{rounded.stamp}"
  sheet:
    backgroundColor: "{colors.paper-sheet}"
    rounded: "{rounded.sheet}"
    padding: "18px 22px"
---

# Design System: HighGround

## Overview

**Creative North Star: "The warning, stamped on the farm map"**

HighGround is drawn, not plotted. The farm is a watercolour-and-pencil map, like the one pinned on the woolshed wall, and a weather warning is *pressed onto it* with ink stamps: MOVE OUT, WATCH, SAFE. The ground is pale paper-green, the frame is woolpack-ink indigo, and one instruction ("Move the herd to Paddock 7 by 7pm") is the loudest thing on screen. It is built for a projector at a pitch (read from about 10 m) and still works on a phone.

The world lends type, palette, the paper grain and one signature move: the stamps. Layout and controls stay those of an ordinary working app.

**Key Characteristics:**
- A hand-drawn SVG farm map generated from the API's GeoJSON: no map tiles, works offline, always fits the farm.
- Risk shown three ways: watercolour wash colour, a stamped word, and a reason in words.
- The warning banner carries the move instruction at display size, in the warning level's colour.
- Paper grain on every surface; ink indigo for frame and text.

## Colors

Committed palette: paper greens for ground and sheets, ink indigo for the frame, and three risk inks that each come as a dark stamp ink and a light watercolour wash.

### Primary
- **Woolpack Ink** (`ink`): header, footer, all text, focus rings. The colour of the brand.

### Secondary
- **Stamp Red / Amber / Green** (`stamp-*`): stamp ink, chips, the primary button (red). Always on paper, never on their own wash.
- **Washes** (`wash-*`): paddock fills and legend swatches only, at ~80% opacity with multiply blending.

### Tertiary
- **River** (`river-wash`, `river-ink`): the river and water troughs. Nothing else is blue.
- **Warning levels** (`level-*`): the instruction banner background only.

### Neutral
- **Paper** (`paper`), **Sheet** (`paper-sheet`), **Deep paper** (`paper-deep`): page ground, cards, dashed dividers and calm banner. **Shed grey** (`shed`) marks the shed so it is never mistaken for a risk colour.

### Named Rules
**The Traffic Light Rule.** Red, amber and green mean only risk (move stock out / could flood / low risk). No decoration, chart or brand use may borrow them.

**The Ink-on-Paper Rule.** Stamp ink sits on paper (a 90% paper patch inside the stamp frame), never directly on a wash, so the word always clears 3:1.

## Typography

**Display:** Bricolage Grotesque (600, 800), self-hosted via @fontsource.
**Body:** Atkinson Hyperlegible (400, 700), chosen for legibility at distance; its slashed zero is intended.
**Stamp:** Saira Stencil One, only for stamp words, chips and the REPLAY tag.

### Hierarchy
- **Move** (800, clamp(2rem, 4.4vw, 3.8rem), 1.02): the instruction. One per screen.
- **Heading** (800, 1.45rem): side-sheet sections (River gauge, Paddocks, Storm plan).
- **Map labels** (800, display face, sized in map units: names min(width x 0.13, 46)).
- **Body** (400, 18px desktop / 17px phone, 1.45).
- **Stamp** (Saira Stencil One, tracked 0.08 to 0.14em, uppercase words).

### Named Rules
**The Stencil-Only-Stamps Rule.** The stencil face is for stamped words. Never headings, never body.

## Layout

App shell: indigo header (wordmark left, mode buttons right) → full-width instruction banner → two columns: the map card (map plus a legend column) and a 300-400px side sheet → safety line. Desktop pins the safety line to the bottom. At 820px and below, everything stacks; the safety line moves directly under the banner (not pinned, so it never covers the map), and the mode buttons form a 2-column grid with Replay warning full width. Spacing rhythm 8/12/20/28px.

## Elevation & Depth

Flat paper with one soft lift: `--shadow` (0 10px 30px -14px ink at 35%, plus 0 2px 6px -2px ink at 18%) for the map card, side sheet, paddock card and About dialog. No hard offset shadows.

## Shapes

Pill buttons; 18px sheets; 16px paddock card; 5px stamp chips, each rotated a degree or so; the hand-drawn map uses SVG filters (pencil displacement, watercolour edge and grain, stamp speckle), not clip-paths.

## Components

### Buttons
Pills, 46px tall (52px for Replay warning on phones). On the indigo header: outlined in paper at 55%, filled paper when pressed (`aria-pressed`). **Replay warning** is the one stamp-red primary.

### Chips (if used)
Stamp chips: stencil word in band ink, 2px border in currentColor, paper fill, slight tilt. Used in the paddock list, legend and paddock card.

### Cards / Containers
Map card and side sheet: paper sheet with grain, 18px radius, soft shadow. Dividers inside are 1.5px dashed `paper-deep`.

### Navigation
The header's mode buttons are the navigation: Replay warning, Live mode, Reset, Show plan, About.

### The Drawn Farm Map (signature)
`web/src/components/FarmMap.tsx`. Each paddock contains a wash, an inset pencil outline, its name (bottom-left), its height above the river with 0-3 drawn hills (top-left, from `height_above_river_m`), and a trough drop if it has water. When a warning is in force, each paddock gets an ink stamp, pressed in order of distance from the river (420ms exponential ease-out, 85ms stagger; none with reduced motion). The recommended paddock gets a drawn cow and "herd here". There is also a shed, a north arrow and a scale bar computed from real distances. Paddocks are keyboard buttons carrying `data-band`; selecting one opens a paddock card with the band, risk out of 100 and the reason.

## Do's and Don'ts

### Do:
- **Do** draw every map mark from API data (paddock shapes, heights, troughs, shed, river); label anything synthetic.
- **Do** keep the safety line verbatim and visible in the first screen on every viewport.
- **Do** stamp REPLAY on anything from the replay warning.
- **Do** show times only from the server's NZ-time labels.

### Don't:
- **Don't** use red, amber or green for anything but risk.
- **Don't** put stamp ink straight onto a wash.
- **Don't** use the stencil face outside stamps.
- **Don't** add map ornament (trees, gates, stock) that the data doesn't support.
- **Don't** reintroduce map tiles: the demo must work offline.
