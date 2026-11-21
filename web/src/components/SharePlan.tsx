// Share a storm plan: copy it as plain text (for a text message) or print it.
// Teammate 1 imports this as a default export: <SharePlan plan={result.plan} />

import { useEffect, useState, type CSSProperties } from "react";

export interface SharePlanProps {
  plan: {
    summary: string;
    moves: { time: string; action: string }[];
    checklist: string[];
  };
}

const SAFETY =
  "Official MetService warnings and Civil Defence advice always come first. This is guidance, not a guarantee.";

/** Turn the plan into plain text that reads well in a text message. */
export function planToText(plan: SharePlanProps["plan"]): string {
  const lines: string[] = ["HighGround storm plan", "", plan.summary];
  if (plan.moves.length) {
    lines.push("", "Moves:");
    plan.moves.forEach((m) => lines.push(`- ${m.time}: ${m.action}`));
  }
  if (plan.checklist.length) {
    lines.push("", "Checklist:");
    plan.checklist.forEach((c) => lines.push(`- ${c}`));
  }
  lines.push("", SAFETY);
  return lines.join("\n");
}

/** Copy text, using the Clipboard API when available and a hidden textarea otherwise. */
async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fall through to the older method
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch {
    ok = false;
  }
  document.body.removeChild(area);
  return ok;
}

const button: CSSProperties = {
  fontSize: "1.125rem",
  padding: "0.6rem 1.1rem",
  minHeight: "44px",
  borderRadius: "8px",
  border: "2px solid #333",
  background: "#fff",
  color: "#111",
  cursor: "pointer",
};

export default function SharePlan({ plan }: SharePlanProps) {
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    if (status === "idle") return;
    const t = window.setTimeout(() => setStatus("idle"), 2500);
    return () => window.clearTimeout(t);
  }, [status]);

  const onCopy = async () => setStatus((await copyText(planToText(plan))) ? "copied" : "failed");

  return (
    <div className="hg-share" style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem", alignItems: "center" }}>
      <button type="button" className="hg-share-copy" style={button} onClick={onCopy}>
        Copy as text
      </button>
      <button type="button" className="hg-share-print" style={button} onClick={() => window.print()}>
        Print
      </button>
      <span role="status" aria-live="polite" style={{ fontSize: "1.125rem", fontWeight: 700 }}>
        {status === "copied" && "Copied"}
        {status === "failed" && "Could not copy. Select the plan text and copy it by hand."}
      </span>
    </div>
  );
}
