import { mkdir, writeFile, rename } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, expect } from "@playwright/test";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const output = resolve(root, "artifacts/demo");
await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  recordVideo: { dir: output, size: { width: 1440, height: 1000 } },
});
const page = await context.newPage();
page.setDefaultTimeout(30_000);
const issues = [];
page.on("pageerror", (error) => issues.push(error.message));
const stages = [];
const start = Date.now();
async function caption(text, seconds) {
  stages.push({ second: (Date.now() - start) / 1000, text });
  await page.evaluate((message) => {
    let element = document.getElementById("recording-caption");
    if (!element) {
      element = document.createElement("div");
      element.id = "recording-caption";
      element.style.cssText =
        "position:fixed;bottom:0;left:0;right:0;padding:12px 32px;background:#20201d;color:#fcfbf8;font:16px/1.4 sans-serif;z-index:10000;pointer-events:none";
      document.body.append(element);
    }
    element.textContent = message;
  }, text);
  if (seconds) await page.waitForTimeout(seconds * 1000);
}
try {
  await page.goto(process.env.CAUSALBIO_SCREENSHOT_URL ?? "http://127.0.0.1:3000");
  await page.evaluate(() => document.fonts.ready);
  await expect(page.getByRole("button", { name: /Long-term memory retention/i })).toBeVisible();
  await caption(
    "CausalBio Lab · scripted walkthrough · cached research · unedited timing · no audio",
    3,
  );
  await page
    .getByRole("textbox", { name: /What biological question/ })
    .fill("What mechanisms influence tendon recovery?");
  await page.getByText("Research options", { exact: true }).click();
  await page.getByRole("checkbox", { name: /Use live scientific sources/ }).uncheck();
  await caption(
    "This recording uses previously retrieved evidence, with original retrieval dates.",
    3,
  );
  await page.getByRole("main").getByRole("button", { name: "Investigate", exact: true }).click();
  await page.getByRole("button", { name: /Continue/ }).click();
  await expect(page.getByRole("heading", { name: "Research summary", exact: true })).toBeVisible();
  const mechanisms = page.getByRole("button", { name: /Explore mechanism/ });
  expect(await mechanisms.count()).toBeGreaterThan(0);
  await caption("A provisional research brief keeps source claims and uncertainties visible.", 7);
  await page
    .getByRole("heading", { name: "Possible mechanisms", exact: true })
    .scrollIntoViewIfNeeded();
  await caption(
    "Related findings are grouped into possible mechanisms, not established treatment rankings.",
    6,
  );
  await mechanisms.first().click();
  await page
    .getByRole("heading", { name: "Focused pathway", exact: true })
    .scrollIntoViewIfNeeded();
  await caption(
    "The provisional map connects topics to sources. It does not discover causal biology.",
    7,
  );
  await page
    .getByRole("button", { name: /Source \d/ })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await caption(
    "Numbered citations preserve the passage, publication, context and retrieval date.",
    7,
  );
  await page.getByRole("button", { name: "Close evidence" }).click();
  await page.getByRole("button", { name: /New investigation/ }).click();
  await page.getByRole("button", { name: /Long-term memory retention/i }).click();
  await page.getByRole("button", { name: /Continue/ }).click();
  await expect(
    page.getByRole("heading", { name: "Possible mechanisms", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: /Explore mechanism/ })
    .first()
    .click();
  await page.locator("#mechanism-title").scrollIntoViewIfNeeded();
  await caption(
    "Curated examples retain explicit relationships, counterevidence and limitations.",
    7,
  );
  await page.getByRole("button", { name: /Explore full evidence map/ }).click();
  await page.getByRole("button", { name: "Pathway simulation", exact: true }).click();
  await page.getByRole("button", { name: "Run baseline comparison" }).click();
  await expect(page.getByRole("heading", { name: "What changed?", exact: true })).toBeVisible();
  await page.getByLabel("Simulation trajectory chart").scrollIntoViewIfNeeded();
  await caption(
    "An educational model compares declared scenarios. Software tests are not clinical validation.",
    8,
  );
  const remaining = Math.max(0, 64 - (Date.now() - start) / 1000);
  await caption(
    "Question → evidence → structure → modeling → uncertainty. Methods and validation are documented.",
    remaining,
  );
  expect(issues).toEqual([]);
} finally {
  await context.close();
  const video = await page.video().path();
  await rename(video, resolve(output, "walkthrough.webm"));
  await writeFile(
    resolve(output, "record.json"),
    JSON.stringify(
      {
        recorded_at: new Date().toISOString(),
        duration_seconds: (Date.now() - start) / 1000,
        live_sources: false,
        edited: false,
        audio: false,
        stages,
        issues,
      },
      null,
      2,
    ) + "\n",
  );
  await browser.close();
}
console.log("Recorded artifacts/demo/walkthrough.webm; review before publication.");
