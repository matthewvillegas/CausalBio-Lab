import { expect, test, startInvestigation, inspectMechanism, watchErrors } from "./helpers";

test("knee: mechanism, evidence, simulation, and report at narrow width in dark mode", async ({
  page,
}) => {
  const errors = watchErrors(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await startInvestigation(page, /activity-related knee pain/i);
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await inspectMechanism(page);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole("button", { name: "Model pathway", exact: true }).click();
  await page.getByRole("button", { name: "Run baseline comparison" }).click();
  await expect(page.getByRole("heading", { name: "What changed?" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole("button", { name: /Research report ↓/ }).click();
  await page.getByRole("button", { name: "Generate research report" }).click();
  await expect(page.getByRole("link", { name: /Read.*HTML|HTML.*report/i })).toBeVisible();
  expect(errors).toEqual([]);
});

test("keyboard navigation and unavailable simulation remain usable", async ({ page }) => {
  await page.route("**/api/v1/investigations", async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    json.petri_model = null;
    await route.fulfill({ response, json });
  });
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to investigation" })).toBeFocused();
  await page.keyboard.press("Enter");
  await page
    .getByRole("textbox", { name: /What biological question/ })
    .fill("What mechanisms support long-term memory retention?");
  await page.getByRole("textbox", { name: /What biological question/ }).press("Tab");
  await expect(
    page.getByRole("main").getByRole("button", { name: "Investigate", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: /Continue/ }).click();
  await page
    .getByRole("button", { name: /Explore mechanism/ })
    .first()
    .click();
  await page.getByRole("button", { name: "Model pathway", exact: true }).click();
  await expect(
    page.getByText(/does not yet have an executable pathway model/).last(),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Run baseline comparison" })).toHaveCount(0);
});
