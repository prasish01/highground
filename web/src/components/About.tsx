// About screen: what HighGround is, the safety statement, and data credits.
// Teammate 1 imports this as a default export with no props.

import type { CSSProperties } from "react";

const SAFETY =
  "Official MetService warnings and Civil Defence advice always come first. This is guidance, not a guarantee.";

const box: CSSProperties = {
  maxWidth: "42rem",
  fontSize: "1.125rem",
  lineHeight: 1.6,
  color: "inherit",
};

const safety: CSSProperties = {
  border: "2px solid #b3261e",
  borderRadius: "8px",
  padding: "0.75rem 1rem",
  margin: "1rem 0",
  fontWeight: 700,
};

export default function About() {
  return (
    <section className="hg-about" aria-labelledby="hg-about-title" style={box}>
      <h2 id="hg-about-title" style={{ fontSize: "1.5rem", marginTop: 0 }}>
        About HighGround
      </h2>

      <p>
        HighGround turns New Zealand severe weather warnings into a plan for each paddock. It
        combines official MetService warnings with paddock height above the river and distance to
        the river, colours each paddock green, amber or red, suggests where to move stock and by
        when, and writes a short storm checklist for farm staff.
      </p>

      <p className="hg-about-safety" role="note" style={safety}>
        {SAFETY}
      </p>

      <h3 style={{ fontSize: "1.25rem" }}>Data and credits</h3>
      <ul style={{ paddingLeft: "1.25rem" }}>
        <li>Severe weather warnings: MetService.</li>
        <li>
          Elevation: Toitū Te Whenua LINZ elevation data, served via Open Topo Data (CC BY 4.0).
        </li>
        <li>River levels: Hawke's Bay Regional Council (CC BY 4.0).</li>
        <li>Map data: © OpenStreetMap contributors.</li>
      </ul>

      <h3 style={{ fontSize: "1.25rem" }}>About the demo</h3>
      <p>
        The demo farm is fictional. Warnings shown in replay mode are saved warnings replayed with
        their times shifted to now, and are always labelled <strong>REPLAY</strong>.
      </p>
    </section>
  );
}
