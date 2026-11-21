/*
 * HighGround demo-path click-through (owner: Teammate 5, QA).
 *
 * Clicks through the exact path we show judges, at desktop width and at 375px (phone):
 *   load farm -> Replay warning -> >=2 red and >=1 green paddocks, all on screen
 *   -> banner "Move the herd to Paddock N by <time>" + REPLAY tag
 *   -> tap a red paddock: popup shows its reason
 *   -> Show plan: moves + checklist, Copy and Print buttons
 *   -> About: data credits
 * The safety line must be visible at every step.
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
// Must match BAND_COLOUR in web/src/App.tsx.
const RED = "#d9363e";
const GREEN = "#1f8a5b";
const CREDITS = [/MetService/, /LINZ/, /Open Topo Data/, /Hawke.s Bay Regional Council|HBRC/, /OpenStreetMap/];

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
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${vp}-${name}.png`, fullPage: true });
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

  // 1. Load the sample farm
  await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("path.leaflet-interactive", { state: "attached", timeout: 15000 }).catch(() => {});
  const paths = await page.locator("path.leaflet-interactive").count();
  check(v, "farm loads on the map", paths >= 9, `${paths} shapes drawn`);
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

  // Colours come from the SVG fill of each paddock shape.
  await page.waitForTimeout(300); // GeoJSON layer re-mounts with new colours
  // Paddocks are polygons; skip the river (no fill) and the shed (a circle: its path uses arcs).
  const fills = await page.$$eval("path.leaflet-interactive", (els) =>
    els
      .filter((e) => !/a/i.test(e.getAttribute("d") || ""))
      .map((e) => (e.getAttribute("fill") || "").toLowerCase()),
  );
  const reds = fills.filter((f) => f === RED).length;
  const greens = fills.filter((f) => f === GREEN).length;
  check(v, ">= 2 red paddocks", reds >= 2, `${reds} red`);
  check(v, ">= 1 green paddock", greens >= 1, `${greens} green`);

  // Every paddock shape must be at least partly inside the visible map.
  const mapBox = await page.locator(".leaflet-container").boundingBox();
  const boxes = await page.$$eval("path.leaflet-interactive", (els) =>
    els
      .filter((e) => e.getAttribute("fill") && e.getAttribute("fill") !== "none")
      .filter((e) => !/a/i.test(e.getAttribute("d") || ""))
      .map((e) => {
        const r = e.getBoundingClientRect();
        return { x: r.x, y: r.y, w: r.width, h: r.height };
      }),
  );
  const onScreen = boxes.filter(
    (b) =>
      mapBox &&
      b.x + b.w > mapBox.x &&
      b.x < mapBox.x + mapBox.width &&
      b.y + b.h > mapBox.y &&
      b.y < mapBox.y + mapBox.height,
  ).length;
  check(v, "all paddocks visible inside the map", boxes.length > 0 && onScreen === boxes.length, `${onScreen}/${boxes.length} on screen`);
  await shot(page, v, "2-replay");

  // 3. Tap a red paddock: popup shows its reason
  const redPath = page.locator(`path.leaflet-interactive[fill="${RED}"]`).first();
  let popupText = "";
  if ((await redPath.count()) > 0) {
    await redPath.click({ force: true }).catch(() => {});
    popupText = (await page.locator(".leaflet-popup-content").first().textContent({ timeout: 3000 }).catch(() => "")) || "";
  }
  check(v, "paddock popup shows reason", /m (above|from) river/.test(popupText), JSON.stringify(popupText.slice(0, 120)));
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
