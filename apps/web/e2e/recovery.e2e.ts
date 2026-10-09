import { expect, test, startInvestigation } from "./helpers";

test("report failure is retryable and context edits build a distinct result", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  const ids: string[] = [];
  page.on("response", async (response) => {
    if (response.url().endsWith("/api/v1/investigations") && response.status() === 201)
      ids.push((await response.json()).id);
  });
  await startInvestigation(page, /long-term memory retention/i);
  await page.route(
    "**/api/v1/reports",
    (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/problem+json",
        body: JSON.stringify({
          type: "about:blank",
          title: "Temporary service failure",
          status: 503,
          detail: "The local report service is temporarily unavailable.",
          correlation_id: "browser-fixture",
          alternatives: [],
        }),
      }),
    { times: 1 },
  );
  await page.getByRole("button", { name: /Research report ↓/ }).click();
  await page.getByRole("button", { name: "Generate research report" }).click();
  await expect(
    page.getByRole("heading", { name: "We could not prepare your report" }),
  ).toBeVisible();
  await expect(page.getByText(/browser-fixture/)).not.toBeVisible();
  await page.getByRole("button", { name: "Retry report" }).click();
  await expect(page.getByRole("link", { name: "Read HTML report" })).toBeVisible();
  await page.getByRole("button", { name: "Edit question", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Possible mechanisms" })).toHaveCount(0);
  const question = page.getByRole("textbox", { name: /What biological question/ });
  await expect(question).toHaveValue(/long-term memory retention/);
  await page.getByRole("main").getByRole("button", { name: "Investigate", exact: true }).click();
  await page.getByRole("button", { name: "Edit interpretation" }).click();
  await page
    .getByRole("textbox", { name: "Research population context", exact: true })
    .fill("older adults, research context only");
  await page.getByRole("button", { name: /Continue/ }).click();
  await expect(page.getByRole("heading", { name: "Possible mechanisms" })).toBeVisible();
  await expect.poll(() => ids.length).toBe(2);
  expect(ids[1]).not.toBe(ids[0]);
  await page.getByRole("button", { name: /Research report ↓/ }).click();
  await expect(page.getByRole("button", { name: "Generate research report" })).toBeVisible();
  expect(await page.locator("html").evaluate((node) => getComputedStyle(node).scrollBehavior)).toBe(
    "auto",
  );
});
