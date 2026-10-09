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
const results = [];
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(45_000);
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) errors.push(message.text());
  });
  page.on("response", async (response) => {
    if (response.url().endsWith("/api/v1/research") && response.request().method() === "POST") {
      const result = await response.json();
      results.push({
        id: result.id,
        question: result.interpretation.question.original_text,
        mode: result.mode,
        records: result.evidence.length,
        groups: result.mechanisms.length,
        sources: result.source_runs.map(({ source, status }) => ({ source, status })),
      });
    }
  });
  async function capture(filename, anchor) {
    if (anchor) await anchor.scrollIntoViewIfNeeded();
    else await page.evaluate(() => window.scrollTo(0, 0));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({ path: resolve(output, filename), fullPage: false });
    captures.push(filename);
  }
  await page.goto("http://127.0.0.1:3000");
  await page
    .getByRole("button", { name: "What mechanisms influence tendon recovery?", exact: true })
    .click();
  await page.getByRole("button", { name: /Continue/ }).click();
  await expect(page.getByRole("heading", { name: "Research summary", exact: true })).toBeVisible({
    timeout: 45_000,
  });
  expect(
    await page.getByRole("button", { name: /Explore mechanism/ }).count(),
  ).toBeGreaterThanOrEqual(3);
  await capture("live-tendon-overview.png");
  await page
    .getByRole("button", { name: /Explore mechanism/ })
    .first()
    .click();
  await capture("live-tendon-evidence.png", page.getByRole("heading", { name: "Focused pathway" }));
  await page
    .getByRole("button", { name: /Source \d/ })
    .first()
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Close evidence" }).click();
  await expect(page.getByRole("heading", { name: "References", exact: true })).toBeVisible();
  const popupPromise = page.waitForEvent("popup");
  await page.getByRole("link", { name: "Read HTML report" }).click();
  const popup = await popupPromise;
  await popup.waitForLoadState();
  await expect(popup.locator("body")).toContainText("provisional");
  await popup.close();
  await page.getByRole("button", { name: /New investigation/ }).click();
  await page.getByRole("button", { name: "What does BDNF do?", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Research summary", exact: true })).toBeVisible({
    timeout: 45_000,
  });
  await expect(page.getByRole("button", { name: "Expand evidence search" })).toBeVisible();
  await capture("bdnf-explanation.png");
  await page.getByRole("button", { name: "Expand evidence search" }).click();
  await expect(
    page.getByRole("heading", { name: "We interpreted your question as:" }),
  ).toBeVisible();
  await page.goto("http://127.0.0.1:3000");
  await page
    .getByRole("textbox", { name: /What biological question/ })
    .fill("How much selegiline should I take for memory?");
  await page.getByRole("main").getByRole("button", { name: "Investigate", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "I can help with the science, but not that action" }),
  ).toBeVisible();
  expect(results).toHaveLength(2);
  await capture("safe-research-alternative.png");
  await page.getByRole("button", { name: "Investigate the biology" }).click();
  await expect(page.getByRole("heading", { name: "Research summary", exact: true })).toBeVisible({
    timeout: 45_000,
  });
  expect(results).toHaveLength(3);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await capture("live-research-narrow-dark.png");
  expect(errors).toEqual([]);
  await writeFile(
    resolve(output, "live-capture-record.json"),
    JSON.stringify(
      {
        captured_at: new Date().toISOString(),
        sources_mocked: false,
        captures,
        results,
        browser_warnings_or_errors: errors,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(JSON.stringify({ captures, results, errors }, null, 2));
} finally {
  await browser.close();
}
