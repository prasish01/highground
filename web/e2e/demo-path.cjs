/*
 * HighGround demo-path click-through (owner: Teammate 5, QA).
 *
 * Clicks through the exact path we show judges, at desktop width and at 375px (phone):
 *   load farm -> Replay warning -> >=2 red and >=1 green paddocks, all on screen
 *   -> banner "Move the herd to Paddock N by <time>" + REPLAY tag
 *   -> tap a red paddock: popup/card shows its reason
 *   -> Show plan: moves + checklist, Copy and Print buttons
 *   -> About: data credits
 * The safety line must be visible at every step.
 *
 * Works with either map: the Leaflet map, or the hand-drawn SVG map (FarmMap.tsx, PR #19).
 * It detects which one is on the page.
 *
 * Needs the API (:8000) and web app (:5173) running. Uses the Playwright that is installed
 * globally (not a package.json dependency), so the demo laptop needs nothing extra.
 *
 *   node web/e2e/demo-path.cjs                    # default http://localhost:5173
 *   BASE_URL=http://localhost:4173 SHOTS=/tmp/shots node web/e2e/demo-path.cjs
 *
 * Exits 1 if any step fails. Map tiles are NOT required (the demo must work offline).
 */
const { chromium } = require("playwright");

const BASE_URL = process.env.BASE_URL || "http://localhost:5173";
const SHOTS = process.env.SHOTS || ""; // folder for screenshots; empty = none
const SAFETY =
  "Official MetService warnings and Civil Defence advice always come first. This is guidance, not a guarantee.";
const CREDITS = [/MetService/, /LINZ/, /Open Topo Data/, /Hawke.s Bay Regional Council|HBRC/, /OpenStreetMap/];

// --- the two maps ---------------------------------------------------------------------------
// Leaflet: paddocks are SVG paths coloured with BAND_COLOUR from App.tsx; the shed is a circle
// (its path uses arcs) and the river has no fill.
const LEAFLET_FILL = { red: "#d9363e", amber: "#e0a526", green: "#1f8a5b" };
// Drawn map: each paddock is <g class="paddock" data-band="…" data-id="…"> with a .paddock-wash.
const DRAWN = ".farm-map .paddock";

const MAPS = {
  leaflet: {
    container: ".leaflet-container",
    any: "path.leaflet-interactive",
    popup: ".leaflet-popup-content",
    redShape: `path.leaflet-interactive[fill="${LEAFLET_FILL.red}"]`,
    bands: (page) =>
      page.$$eval(
        "path.leaflet-interactive",
        (els, fills) =>
          els
            .filter((e) => !/a/i.test(e.getAttribute("d") || "")) // not the shed circle
            .map((e) => (e.getAttribute("fill") || "").toLowerCase())
            .filter((f) => f && f !== "none") // not the river
            .map((f) => Object.keys(fills).find((b) => fills[b] === f) || f),
        LEAFLET_FILL,
      ),
    boxes: (page) =>
      page.$$eval("path.leaflet-interactive", (els) =>
        els
          .filter((e) => e.getAttribute("fill") && e.getAttribute("fill") !== "none")
          .filter((e) => !/a/i.test(e.getAttribute("d") || ""))
          .map((e) => e.getBoundingClientRect().toJSON()),
      ),
  },
  drawn: {
    container: ".farm-map",
    any: DRAWN,
    popup: ".paddock-card",
    redShape: `${DRAWN}[data-band="red"]`,
    bands: (page) => page.$$eval(DRAWN, (els) => els.map((e) => e.getAttribute("data-band"))),
    boxes: (page) =>
      page.$$eval(`${DRAWN} .paddock-line`, (els) => els.map((e) => e.getBoundingClientRect().toJSON())),
  },
};

const VIEWPORTS = [
  { name: "desktop", width: 1366, height: 768 }, // common projector resolution
  { name: "mobile-375", width: 375, height: 812 },
];

let failures = 0;
function check(vp, step, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  [${vp}] ${step}${detail ? ` - ${detail}` : ""}`);
  if (!ok) failures++;
  return ok;
}

async function safetyVisible(page) {
  const el = page.getByText(SAFETY, { exact: false }).first();
  return el.isVisible().catch(() => false);
}

async function shot(page, vp, name) {
  if (!SHOTS) return;
  await page.screenshot({ path: `${SHOTS}/${vp}-${name}.png`, fullPage: true });
  // A full-page screenshot briefly resizes the viewport, and the Leaflet map re-fits on resize.
  // Let that finish so the next click doesn't land on a moving map.
  await page.waitForTimeout(800);
}

async function run(browser, vp) {
  const context = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    permissions: ["clipboard-read", "clipboard-write"],
  });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("pageerror", (e) => consoleErrors.push(String(e)));
  const v = vp.name;

  // 1. Load the sample farm (and find out which map this build uses)
  await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
  await page
    .waitForSelector(`${MAPS.leaflet.any}, ${MAPS.drawn.any}`, { state: "attached", timeout: 15000 })
    .catch(() => {});
  const kind = (await page.locator(MAPS.drawn.any).count()) > 0 ? "drawn" : "leaflet";
  const map = MAPS[kind];
  const paddocks = (await map.bands(page)).length;
  check(v, `farm loads on the map (${kind})`, paddocks >= 9, `${paddocks} paddocks drawn`);
  check(v, "safety line visible (calm)", await safetyVisible(page));
  await shot(page, v, "1-calm");

  // 2. Replay warning
  await page.getByRole("button", { name: "Replay warning" }).click();
  const banner = page.locator(".banner .move");
  await banner.waitFor({ timeout: 15000 }).catch(() => {});
  await page.getByText(/^REPLAY$/).first().waitFor({ timeout: 5000 }).catch(() => {});
  const bannerText = (await banner.first().textContent().catch(() => "")) || "";
  check(
    v,
    'banner says "Move the herd to Paddock N by <time>"',
    /Move the herd to Paddock \d+ by \d{1,2}(:\d{2})?\s?(am|pm)/i.test(bannerText),
    JSON.stringify(bannerText),
  );
  check(v, "REPLAY label shown", await page.getByText(/^REPLAY$/).first().isVisible().catch(() => false));
  check(v, "safety line visible (replay)", await safetyVisible(page));

  // The map redraws with the new bands: wait until a paddock is red, then a moment more so we
  // never read or click shapes while they're being swapped or animated in.
  await page.waitForSelector(map.redShape, { state: "attached", timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(kind === "drawn" ? 1500 : 500);
  const bands = await map.bands(page);
  const reds = bands.filter((b) => b === "red").length;
  const greens = bands.filter((b) => b === "green").length;
  check(v, ">= 2 red paddocks", reds >= 2, `${reds} red`);
  check(v, ">= 1 green paddock", greens >= 1, `${greens} green`);

  if (kind === "drawn") {
    // Independent of the map's own markup: bands must match the API, paddock by paddock...
    const api = await page.evaluate(async () =>
      (await (await fetch("/api/assess?mode=replay")).json()).paddocks.map((p) => [p.paddock_id, p.band]),
    );
    const apiBand = Object.fromEntries(api);
    const drawn = await page.$$eval(DRAWN, (els) => els.map((e) => [e.getAttribute("data-id"), e.getAttribute("data-band")]));
    const wrong = drawn.filter(([id, b]) => apiBand[id] !== b);
    check(v, "map bands match /api/assess", wrong.length === 0, wrong.length ? JSON.stringify(wrong) : "");
    // ...and a red paddock must actually be painted red, a green one green.
    const paint = await page.$$eval(DRAWN, (els) =>
      els.map((e) => {
        const m = getComputedStyle(e.querySelector(".paddock-wash")).fill.match(/\d+/g) || [];
        return [e.getAttribute("data-band"), m.slice(0, 3).map(Number)];
      }),
    );
    const badPaint = paint.filter(
      ([b, [r, g]]) => (b === "red" && !(r > g + 40)) || (b === "green" && !(g > r + 20)),
    );
    check(v, "red paddocks look red, green look green", badPaint.length === 0, badPaint.length ? JSON.stringify(badPaint) : "");
  }

  // Every paddock shape must be at least partly inside the visible map.
  const mapBox = await page.locator(map.container).boundingBox();
  const boxes = await map.boxes(page);
  const onScreen = boxes.filter(
    (b) =>
      mapBox &&
      b.x + b.width > mapBox.x &&
      b.x < mapBox.x + mapBox.width &&
      b.y + b.height > mapBox.y &&
      b.y < mapBox.y + mapBox.height,
  ).length;
  check(v, "all paddocks visible inside the map", boxes.length > 0 && onScreen === boxes.length, `${onScreen}/${boxes.length} on screen`);
  await shot(page, v, "2-replay");

  // 3. Tap a red paddock: popup/card shows its reason. Up to 3 tries, because a click during a
  // redraw can land on a shape that is being replaced. A FAIL after 3 tries is a real bug.
  const redShape = page.locator(map.redShape).first();
  const REASON = /m (above|below|from) river|at river level/;
  let popupText = "";
  for (let attempt = 1; attempt <= 3 && !REASON.test(popupText); attempt++) {
    if ((await redShape.count()) === 0) break;
    await redShape.click({ force: true }).catch(() => {});
    popupText = (await page.locator(map.popup).first().textContent({ timeout: 2000 }).catch(() => "")) || "";
    if (attempt > 1) console.log(`      (popup needed click attempt ${attempt})`);
  }
  check(v, "paddock popup shows reason", REASON.test(popupText), JSON.stringify(popupText.slice(0, 120)));
  await shot(page, v, "3-popup");
  await page.keyboard.press("Escape").catch(() => {});

  // 4. Show plan
  await page.getByRole("button", { name: "Show plan" }).click();
  const moves = await page.locator(".moves li").count();
  const items = await page.locator(".checklist li").count();
  check(v, "plan shows moves", moves >= 1, `${moves} moves`);
  check(v, "plan shows checklist", items >= 3, `${items} items`);
  const copyBtn = page.getByRole("button", { name: /copy/i }).first();
  const printBtn = page.getByRole("button", { name: /print/i }).first();
  check(v, "Copy button present", await copyBtn.isVisible().catch(() => false));
  check(v, "Print button present", await printBtn.isVisible().catch(() => false));
  if (await copyBtn.isVisible().catch(() => false)) {
    await copyBtn.click();
    const clip = await page.evaluate(() => navigator.clipboard.readText()).catch(() => "");
    check(v, "copied text has REPLAY label and safety line", /REPLAY/.test(clip) && clip.includes("Civil Defence"), `${clip.length} chars`);
  }
  check(v, "safety line visible (plan)", await safetyVisible(page));
  await shot(page, v, "4-plan");

  // 5. About shows credits
  await page.getByRole("button", { name: "About" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.waitFor({ timeout: 3000 }).catch(() => {});
  const aboutText = (await dialog.textContent().catch(() => "")) || "";
  const missing = CREDITS.filter((re) => !re.test(aboutText)).map(String);
  check(v, "About credits MetService, LINZ, Open Topo Data, HBRC, OSM", missing.length === 0, missing.length ? `missing ${missing.join(", ")}` : "");
  check(v, "safety line visible (About)", aboutText.includes(SAFETY) || (await safetyVisible(page)));
  await shot(page, v, "5-about");

  // 6. No horizontal scroll on phone width
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  check(v, "no horizontal page scroll", overflow <= 1, `overflow ${overflow}px`);
  check(v, "no JavaScript errors", consoleErrors.length === 0, consoleErrors.join(" | "));
  await context.close();
}

(async () => {
  const browser = await chromium.launch();
  try {
    for (const vp of VIEWPORTS) await run(browser, vp);
  } finally {
    await browser.close();
  }
  console.log(failures ? `\n${failures} check(s) FAILED` : "\nDemo path OK");
  process.exit(failures ? 1 : 0);
})();
