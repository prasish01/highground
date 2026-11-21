// The farm, drawn: paddocks as watercolour washes inside pencil outlines, the river as a blue wash,
// and, once a warning is in force, an ink stamp pressed onto every paddock (MOVE OUT / WATCH / SAFE).
//
// It is plain SVG drawn from the /api/farm GeoJSON, so it needs no map tiles (the demo works offline)
// and always fits the farm, wherever the farm is (issue #6).

import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import type { Band, PaddockRisk } from "../api";
import { BAND_STAMP, BAND_WORDS } from "../bands";

type XY = [number, number];

interface Props {
  farm: GeoJSON.FeatureCollection;
  risks: Map<string, PaddockRisk>;
  /** True while a warning is in force: paddocks get their stamps. */
  stamped: boolean;
  /** Paddock id the herd should move to, if any. */
  herdTo?: string | null;
}

interface DrawnPaddock {
  id: string;
  name: string;
  hasWater: boolean;
  d: string;
  centre: XY;
  width: number;
  top: number;
  bottom: number;
  left: number;
}

const VIEW_W = 1000; // the drawing is always 1000 units wide; height follows the farm's shape
const PAD = 40;
const M_PER_DEG = 111_320;

function ringsOf(g: GeoJSON.Geometry): number[][][] {
  if (g.type === "Polygon") return g.coordinates as number[][][];
  if (g.type === "MultiPolygon") return (g.coordinates as number[][][][]).flat();
  return [];
}

/** Simple local projection: fine for a farm a few km across. North is up. */
function useDrawing(farm: GeoJSON.FeatureCollection) {
  return useMemo(() => {
    const paddockFeatures = farm.features.filter((f) => f.properties?.kind === "paddock");
    const shed = farm.features.find((f) => f.properties?.kind === "shed");
    const river = farm.features.find((f) => f.properties?.kind === "river");

    const pts: number[][] = paddockFeatures.flatMap((f) => ringsOf(f.geometry).flat());
    if (shed?.geometry.type === "Point") pts.push(shed.geometry.coordinates as number[]);
    if (pts.length === 0) return null;

    const lat0 = pts.reduce((s, p) => s + p[1], 0) / pts.length;
    const k = Math.cos((lat0 * Math.PI) / 180);
    let minLon = Math.min(...pts.map((p) => p[0]));
    let maxLon = Math.max(...pts.map((p) => p[0]));
    let minLat = Math.min(...pts.map((p) => p[1]));
    let maxLat = Math.max(...pts.map((p) => p[1]));

    // Pull in the stretch of river that runs past the farm, so it is on the drawing.
    const riverCoords =
      river?.geometry.type === "LineString" ? (river.geometry.coordinates as number[][]) : [];
    const spanLon = maxLon - minLon;
    const near = riverCoords.filter(
      (p) => p[0] >= minLon - spanLon * 0.1 && p[0] <= maxLon + spanLon * 0.1 && Math.abs(p[1] - (minLat + maxLat) / 2) < (maxLat - minLat) * 1.2,
    );
    for (const p of near) {
      minLat = Math.min(minLat, p[1]);
      maxLat = Math.max(maxLat, p[1]);
    }

    const spanX = (maxLon - minLon) * k;
    const spanY = maxLat - minLat;
    const scale = (VIEW_W - PAD * 2) / spanX;
    const viewH = Math.round(spanY * scale + PAD * 2);
    const project = (p: number[]): XY => [PAD + (p[0] - minLon) * k * scale, PAD + (maxLat - p[1]) * scale];
    const path = (ring: number[][]) => "M" + ring.map((p) => project(p).map((n) => n.toFixed(1)).join(" ")).join(" L") + " Z";

    const paddocks: DrawnPaddock[] = paddockFeatures.map((f) => {
      const rings = ringsOf(f.geometry);
      const outer = rings[0].map(project);
      const xs = outer.map((p) => p[0]);
      const ys = outer.map((p) => p[1]);
      const ring = outer.slice(0, -1).length ? outer.slice(0, -1) : outer;
      return {
        id: String(f.properties?.id),
        name: String(f.properties?.name ?? ""),
        hasWater: Boolean(f.properties?.has_water),
        d: rings.map(path).join(" "),
        centre: [ring.reduce((s, p) => s + p[0], 0) / ring.length, ring.reduce((s, p) => s + p[1], 0) / ring.length],
        width: Math.max(...xs) - Math.min(...xs),
        top: Math.min(...ys),
        bottom: Math.max(...ys),
        left: Math.min(...xs),
      };
    });

    const riverD = riverCoords.length
      ? "M" + riverCoords.map((p) => project(p).map((n) => n.toFixed(1)).join(" ")).join(" L")
      : null;
    const shedXY = shed?.geometry.type === "Point" ? project(shed.geometry.coordinates as number[]) : null;

    // Scale bar: a round number of metres about a fifth of the drawing wide.
    const metresPerUnit = M_PER_DEG / scale;
    const target = metresPerUnit * VIEW_W * 0.2;
    const nice = [50, 100, 200, 250, 500, 1000, 2000].reduce((a, b) => (Math.abs(b - target) < Math.abs(a - target) ? b : a));
    return {
      viewH,
      paddocks,
      riverD,
      riverName: String(river?.properties?.name ?? "River"),
      shedXY,
      shedName: String(shed?.properties?.name ?? "Shed"),
      scaleBar: { metres: nice, units: nice / metresPerUnit },
    };
  }, [farm]);
}

export default function FarmMap({ farm, risks, stamped, herdTo }: Props) {
  const drawing = useDrawing(farm);
  const wrapRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState<{ id: string; x: number; y: number; below: boolean } | null>(null);

  // Stamps land from the river outwards: order paddocks by distance to the river.
  const stampOrder = useMemo(() => {
    const ids = [...risks.values()].sort((a, b) => a.distance_to_river_m - b.distance_to_river_m).map((r) => r.paddock_id);
    return new Map(ids.map((id, i) => [id, i]));
  }, [risks]);

  if (!drawing) return <p className="map-empty">This farm has no paddocks to draw.</p>;
  const { viewH, paddocks, riverD, riverName, shedXY, shedName, scaleBar } = drawing;

  const select = (id: string, el: Element) => {
    const wrap = wrapRef.current?.getBoundingClientRect();
    const box = el.getBoundingClientRect();
    if (!wrap) return;
    // Keep the card inside the map: clamp it sideways, and open it below the paddock near the top.
    const half = Math.min(150, wrap.width * 0.43);
    const cx = box.left - wrap.left + box.width / 2;
    const cy = box.top - wrap.top + box.height / 2;
    const x = Math.min(Math.max(cx, half + 8), wrap.width - half - 8);
    setOpen((cur) => (cur?.id === id ? null : { id, x, y: cy, below: cy < 190 }));
  };
  const onKey = (e: KeyboardEvent<SVGGElement>, id: string) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      select(id, e.currentTarget);
    }
  };

  const openRisk = open ? risks.get(open.id) : undefined;
  const openName = open ? paddocks.find((p) => p.id === open.id)?.name : "";
  const herd = paddocks.find((p) => p.id === herdTo);

  return (
    <div
      className="farm-map"
      ref={wrapRef}
      onKeyDown={(e) => e.key === "Escape" && setOpen(null)}
    >
      <svg
        className="farm-svg"
        viewBox={`0 0 ${VIEW_W} ${viewH}`}
        style={{ aspectRatio: `${VIEW_W} / ${viewH}` }}
        role="group"
        aria-label="Drawn map of the farm. Select a paddock for its risk and reason."
        onClick={(e) => e.target === e.currentTarget && setOpen(null)}
      >
        <defs>
          {/* Pencil: displace straight lines a little so they wobble like a hand-drawn line. */}
          <filter id="hg-pencil" x="-5%" y="-5%" width="110%" height="110%">
            <feTurbulence type="fractalNoise" baseFrequency="0.012" numOctaves="2" seed="3" />
            <feDisplacementMap in="SourceGraphic" scale="16" />
          </filter>
          {/* Watercolour: a ragged edge, a soft bleed, and pigment granulation. */}
          <filter id="hg-wash" x="-8%" y="-8%" width="116%" height="116%">
            <feTurbulence type="fractalNoise" baseFrequency="0.022" numOctaves="3" seed="7" result="edge" />
            <feDisplacementMap in="SourceGraphic" in2="edge" scale="16" result="ragged" />
            <feGaussianBlur in="ragged" stdDeviation="1.6" result="soft" />
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" seed="2" result="grain" />
            <feColorMatrix in="grain" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -0.55 1.05" result="grainA" />
            <feComposite in="soft" in2="grainA" operator="in" />
          </filter>
          {/* Ink stamp: speckle the ink so it reads as pressed by hand, not printed. */}
          <filter id="hg-stamp" x="-10%" y="-10%" width="120%" height="120%">
            <feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="2" seed="11" result="n" />
            <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -2.4 2.05" result="speckle" />
            <feComposite in="SourceGraphic" in2="speckle" operator="in" result="inked" />
            <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="1" seed="5" result="w" />
            <feDisplacementMap in="inked" in2="w" scale="3" />
          </filter>
        </defs>

        {/* River */}
        {riverD && (
          <g className="river" aria-label={riverName}>
            <path d={riverD} className="river-wash" filter="url(#hg-wash)" />
            <path d={riverD} className="river-line" filter="url(#hg-pencil)" />
          </g>
        )}

        {/* Paddocks */}
        {paddocks.map((p) => {
          const risk = risks.get(p.id);
          const band: Band = risk?.band ?? "green";
          const words = BAND_WORDS[band];
          const fs = Math.min(p.width * 0.115, 44);
          const nameFs = Math.min(p.width * 0.15, 54);
          const tilt = ((p.id.charCodeAt(p.id.length - 1) % 5) - 2) * 2.2; // a hand never stamps square
          return (
            <g
              key={p.id}
              className={`paddock paddock-${band}${open?.id === p.id ? " is-open" : ""}`}
              data-band={band}
              data-id={p.id}
              role="button"
              tabIndex={0}
              aria-label={`${p.name}: ${words.long}${risk ? `. ${risk.reason}` : ""}`}
              aria-expanded={open?.id === p.id}
              onClick={(e) => select(p.id, e.currentTarget)}
              onKeyDown={(e) => onKey(e, p.id)}
            >
              <path
                d={p.d}
                className="paddock-wash"
                filter="url(#hg-wash)"
                transform={`translate(${p.centre[0]} ${p.centre[1]}) scale(0.92) translate(${-p.centre[0]} ${-p.centre[1]})`}
              />
              <path d={p.d} className="paddock-hit" />
              {/* Each paddock drawn with its own slightly inset line, like fences either side of a gap. */}
              <path
                d={p.d}
                className="paddock-line"
                filter="url(#hg-pencil)"
                transform={`translate(${p.centre[0]} ${p.centre[1]}) scale(0.975) translate(${-p.centre[0]} ${-p.centre[1]})`}
              />
              <text x={p.left + 18} y={p.bottom - 20} className="paddock-name" fontSize={nameFs}>
                {p.name}
              </text>
              {risk && (
                <Terrain
                  x={p.centre[0]}
                  y={p.top + 46}
                  size={nameFs}
                  height={risk.height_above_river_m}
                />
              )}
              {p.hasWater && (
                <g transform={`translate(${p.left + p.width - 34} ${p.top + 38}) scale(1.5)`} className="trough">
                  <path d="M0 -11 C5 -4 8 0 8 4 A8 8 0 0 1 -8 4 C-8 0 -5 -4 0 -11Z" />
                  <title>Water trough</title>
                </g>
              )}
              {stamped && risk && (
                <g
                  className="stamp-pos"
                  transform={`translate(${p.centre[0].toFixed(1)} ${(p.centre[1] - fs * 0.45).toFixed(1)}) rotate(${tilt})`}
                >
                  <g className="stamp" style={{ animationDelay: `${(stampOrder.get(p.id) ?? 0) * 85}ms` }} filter="url(#hg-stamp)">
                    <rect x={-fs * 3.1} y={-fs * 0.95} width={fs * 6.2} height={fs * 1.9} rx={fs * 0.28} className="stamp-frame" />
                    <rect x={-fs * 2.9} y={-fs * 0.78} width={fs * 5.8} height={fs * 1.56} rx={fs * 0.2} className="stamp-frame inner" />
                    <text y={fs * 0.36} fontSize={fs} className="stamp-text" style={{ fill: BAND_STAMP[band] }}>
                      {words.stamp}
                    </text>
                  </g>
                </g>
              )}
            </g>
          );
        })}

        {/* Where the herd goes */}
        {stamped && herd && (
          <g className="herd" transform={`translate(${herd.centre[0].toFixed(1)} ${(herd.centre[1] + Math.min(herd.width * 0.115, 44) * 1.35).toFixed(1)})`}>
            <g transform="translate(-96 -18) scale(2.2)">
              <Cow />
            </g>
            <text x="-26" y="18" className="herd-label">herd here</text>
          </g>
        )}

        {/* Shed: neutral grey, never a risk colour */}
        {shedXY && (
          <g className="shed" transform={`translate(${shedXY[0].toFixed(1)} ${shedXY[1].toFixed(1)}) scale(1.6)`}>
            <path d="M-14 6 V-6 L0 -16 L14 -6 V6 Z" filter="url(#hg-pencil)" />
            <path d="M-4 6 V-2 H4 V6" className="shed-door" />
            <title>{shedName}</title>
          </g>
        )}

        {/* North arrow and scale bar */}
        <g className="compass" transform={`translate(${VIEW_W - 30} ${viewH - 58}) scale(1.3)`}>
          <path d="M0 -26 L9 8 L0 2 L-9 8 Z" />
          <text y="30">N</text>
        </g>
        <g className="scalebar" transform={`translate(${PAD} ${viewH - 26})`}>
          <path d={`M0 0 H${scaleBar.units.toFixed(1)} M0 -7 V7 M${scaleBar.units.toFixed(1)} -7 V7`} filter="url(#hg-pencil)" />
          <text x={scaleBar.units / 2} y="-12">
            {scaleBar.metres >= 1000 ? `${scaleBar.metres / 1000} km` : `${scaleBar.metres} m`}
          </text>
        </g>
      </svg>

      {open && openRisk && (
        <div className={`paddock-card${open.below ? " is-below" : ""}`} role="dialog" aria-label={openName} style={{ left: open.x, top: open.y }}>
          <button className="card-close" aria-label="Close" onClick={() => setOpen(null)}>
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M3 3 L13 13 M13 3 L3 13" />
            </svg>
          </button>
          <strong>{openName}</strong>
          {/* The band word and the reason say it all; a raw score invites "is 77 bad?" (BUG-014). */}
          <span className={`chip chip-${openRisk.band}`}>{BAND_WORDS[openRisk.band].stamp}</span>
          <p>{openRisk.reason}</p>
        </div>
      )}
    </div>
  );
}

/**
 * Height above the river as drawn hills (from the API's height_above_river_m): one hill per ~8 m,
 * at most three; low ground gets a flat line. No number here, so the map never words the height
 * differently from the paddock's reason; the exact figure is in the reason and the tooltip.
 */
function Terrain({ x, y, size, height }: { x: number; y: number; size: number; height: number }) {
  const hills = Math.max(0, Math.min(3, Math.round(height / 8)));
  const w = size * 0.9;
  const total = hills === 0 ? w * 1.6 : w * hills;
  return (
    <g className="terrain" transform={`translate(${x - total / 2} ${y})`} filter="url(#hg-pencil)">
      {hills === 0 ? (
        <path d={`M0 0 H${total}`} />
      ) : (
        Array.from({ length: hills }, (_, i) => (
          <path key={i} d={`M${w * i} 0 Q${w * (i + 0.5)} ${-size * 0.8} ${w * (i + 1)} 0`} />
        ))
      )}
      <title>{`${Math.round(height)} m above the river`}</title>
    </g>
  );
}

/** A small drawn cow, in one ink stroke weight. */
function Cow() {
  return (
    <g className="cow">
      <path d="M3 7 Q3 3 8 3 H17 Q21 3 21 7 V11 Q21 12 20 12 H4 Q3 12 3 11 Z" />
      <path d="M21 5 Q25 3 27 6 Q27 9 24 9 H21" />
      <path d="M6 12 V17 M9 12 V17 M16 12 V17 M19 12 V17" />
      <path d="M24 3.5 L25.5 1.5 M26 4.5 L28 3" />
      <path className="cow-spot" d="M9 5 Q12 4 12 7 Q11 9 8.5 8 Z" />
      <path className="cow-spot" d="M15 8 Q18 7 18.5 9.5 Q16 11 14.5 10 Z" />
      <path d="M3 6 Q0 8 1 11" />
    </g>
  );
}
