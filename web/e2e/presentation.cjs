/*
 * HighGround projector checks: Presentation mode at 1366x768, and the phone first screen.
 * Kept apart from demo-path.cjs so the two scripts can change independently.
 *
 *   node web/e2e/presentation.cjs                 # default http://localhost:5173
 *   BASE_URL=http://localhost:4173 SHOTS=/tmp/shots node web/e2e/presentation.cjs
 *
 * Needs the API (:8000) and web app running. Exits 1 if any check fails.
 */
const { chromium } = require("playwright");

const BASE_URL = process.env.BASE_URL || "http://localhost:5173";
const SHOTS = process.env.SHOTS || "";
const SAFETY =
  "Official MetService warnings and Civil Defence advice always come first. This is guidance, not a guarantee.";

let failures = 0;
function check(vp, step, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  [${vp}] ${step}${detail ? ` - ${detail}` : ""}`);
  if (!ok) failures++;
}

async function replay(page) {
  await page.waitForSelector(".farm-map .paddock", { timeout: 15000 });
  await page.getByRole("button", { name: "Replay warning" }).click();
  await page.locator(".banner .move").waitFor({ timeout: 15000 });
  await page.waitForTimeout(300);
}

const svgBox = (page) => page.locator(".farm-svg").boundingBox();
const visible = (page, text) => page.getByText(text, { exact: false }).first().isVisible().catch(() => false);

async function projector(browser) {
  const v = "present-1366";
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));

  // Normal layout first, for a size comparison.
  await page.goto(BASE_URL);
  await replay(page);
  const normal = await svgBox(page);

  // ?present=1 opens straight into presentation mode.
  await page.goto(`${BASE_URL}/?present=1`);
  await replay(page);
  const big = await svgBox(page);
  check(v, "side panel hidden", !(await page.locator(".sheet").isVisible()));
  check(v, "map is much bigger than the normal layout", big && normal && big.height >= normal.height * 1.3,
    `${Math.round(normal?.height)}px -> ${Math.round(big?.height)}px tall`);
  check(v, "banner move shown", /Move the herd to Paddock \d+ by/i.test((await page.locator(".banner .move").textContent()) || ""));
  check(v, "REPLAY label shown", await page.getByText(/^REPLAY$/).first().isVisible());
  check(v, "legend shown", await page.locator(".legend-side").isVisible());
  check(v, "safety line visible", await visible(page, SAFETY));
  const scroll = await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight);
  check(v, "fits one screen, no scrolling", scroll <= 1, `overflow ${scroll}px`);
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${v}-1-replay.png` });

  // Show plan still works, with the safety line.
  await page.getByRole("button", { name: "Show plan" }).click();
  const items = await page.locator(".checklist li").count();
  check(v, "Show plan shows the checklist", items >= 3, `${items} items`);
  check(v, "safety line visible (plan)", await visible(page, SAFETY));
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${v}-2-plan.png` });

  // The button turns it off again and keeps the URL in step.
  const btn = page.getByRole("button", { name: "Presentation" });
  check(v, "Presentation button pressed", (await btn.getAttribute("aria-pressed")) === "true");
  await btn.click();
  check(v, "toggle off brings the side panel back", await page.locator(".sheet").isVisible());
  check(v, "URL drops ?present=1", !page.url().includes("present="), page.url());
  await btn.click();
  check(v, "toggle on adds ?present=1", page.url().includes("present=1"), page.url());
  check(v, "no JavaScript errors", errors.length === 0, errors.join(" | "));
  await page.close();
}

async function phone(browser) {
  const v = "mobile-375";
  const page = await browser.newPage({ viewport: { width: 375, height: 812 } });
  // ?present=1 must not upset the phone layout.
  for (const url of [BASE_URL, `${BASE_URL}/?present=1`]) {
    await page.goto(url);
    await replay(page);
    const tops = await page.$$eval('.farm-map .paddock[data-band="red"]', (els) =>
      els.map((e) => e.getBoundingClientRect().top),
    );
    const first = Math.min(...tops);
    check(v, `MOVE OUT paddocks start in the first screen (${url.includes("present") ? "?present=1" : "plain"})`,
      tops.length > 0 && first < 812 - 60, `top at ${Math.round(first)}px of 812`);
  }
  check(v, "Presentation button hidden on a phone", !(await page.getByRole("button", { name: "Presentation" }).isVisible()));
  check(v, "safety line visible", await visible(page, SAFETY));
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/${v}-replay.png` });
  await page.close();
}

(async () => {
  const browser = await chromium.launch();
  try {
    await projector(browser);
    await phone(browser);
  } finally {
    await browser.close();
  }
  console.log(failures ? `\n${failures} check(s) FAILED` : "\nPresentation checks OK");
  process.exit(failures ? 1 : 0);
})();
