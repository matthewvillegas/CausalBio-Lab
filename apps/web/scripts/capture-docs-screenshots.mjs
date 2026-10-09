import { mkdir, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium, expect } from "@playwright/test";

const workspace = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const output = resolve(workspace, "docs/assets");
await mkdir(output, { recursive: true });

const browser = await chromium.launch();
const errors = [];
const captures = [];
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
  });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) errors.push(message.text());
  });
  async function capture(filename, anchor) {
    if (anchor) await anchor.scrollIntoViewIfNeeded();
    else await page.evaluate(() => window.scrollTo(0, 0));
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
      .toBe(true);
    await page.screenshot({ path: resolve(output, filename), fullPage: false });
    captures.push(filename);
  }
  await page.goto(process.env.CAUSALBIO_SCREENSHOT_URL ?? "http://127.0.0.1:3000", {
    waitUntil: "networkidle",
  });
  const example = page.getByRole("button", { name: /long-term memory retention/i });
  await expect(example).toBeVisible();
  await capture("landing.png");
  await example.click();
  await expect(
    page.getByRole("heading", { name: "We interpreted your question as:" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Continue/ }).click();
  await expect(
    page.getByRole("heading", { name: "Possible mechanisms", exact: true }),
  ).toBeVisible();
  await capture(
    "investigation-overview.png",
    page.getByRole("heading", { name: "Possible mechanisms", exact: true }),
  );
  await page
    .getByRole("button", { name: /Explore mechanism/ })
    .first()
    .click();
  const path = page.getByRole("list", { name: "Focused biological pathway" });
  await capture("focused-pathway.png", page.locator("#mechanism-title"));
  await path
    .getByRole("button", { name: /Why this connection/ })
    .first()
    .click();
  await capture("evidence-detail.png", page.getByRole("region", { name: "Connection evidence" }));
  await page.getByRole("button", { name: /Explore full evidence map/ }).click();
  const graph = page.getByRole("img", { name: /Interactive causal graph/ });
  await expect(graph).toBeVisible();
  await page.getByRole("button", { name: "Show full research graph" }).click();
  await page.getByRole("button", { name: "Fit to view", exact: true }).click();
  await capture("causal-graph.png", graph);
  await page.getByRole("button", { name: "Pathway simulation", exact: true }).click();
  await page.getByRole("button", { name: "Run baseline comparison" }).click();
  const changed = page.getByRole("heading", { name: "What changed?" });
  await expect(changed).toBeVisible();
  await capture("pathway-simulation.png", changed);
  await page.getByRole("button", { name: "Uncertainty analysis", exact: true }).click();
  await page.getByRole("button", { name: "Run uncertainty demonstration" }).click();
  const posterior = page.getByText("Posterior parameter estimates");
  await expect(posterior).toBeVisible();
  await capture("bayesian-demonstration.png", posterior);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: /New investigation/ }).click();
  await page.getByRole("button", { name: /dark mode/i }).click();
  await page.getByRole("button", { name: /Activity-related knee pain/i }).click();
  await page.getByRole("button", { name: /Continue/ }).click();
  await expect(
    page.getByRole("heading", { name: "Possible mechanisms", exact: true }),
  ).toBeVisible();
  await capture(
    "narrow-dark-mechanisms.png",
    page.getByRole("heading", { name: "Possible mechanisms", exact: true }),
  );
  expect(errors).toEqual([]);
  await writeFile(
    resolve(output, "capture-record.json"),
    JSON.stringify(
      {
        captured_at: new Date().toISOString(),
        viewports: [
          { width: 1440, height: 1000 },
          { width: 390, height: 844 },
        ],
        captures,
        browser_warnings_or_errors: errors,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    `Captured ${captures.length} current screenshots without horizontal overflow or browser warnings.`,
  );
} finally {
  await browser.close();
}
