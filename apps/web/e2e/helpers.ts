import { expect, test, type Page } from "@playwright/test";

export async function startInvestigation(page: Page, example: RegExp) {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Investigate biological mechanisms" }),
  ).toBeVisible();
  await page.getByRole("button", { name: example }).click();
  await expect(
    page.getByRole("heading", { name: "We interpreted your question as:" }),
  ).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(0);
  await page.getByRole("button", { name: /Continue/ }).click();
  await expect(page.getByRole("heading", { name: "Possible mechanisms" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Explore mechanism/ })).toHaveCount(3);
}

export function watchErrors(page: Page) {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error" || message.type() === "warning")
      errors.push(`${message.type()}: ${message.text()}`);
  });
  return errors;
}

export async function inspectMechanism(page: Page) {
  await page
    .getByRole("button", { name: /Explore mechanism/ })
    .first()
    .click();
  const path = page.getByRole("list", { name: "Focused biological pathway" });
  expect(await path.locator("li").count()).toBeLessThanOrEqual(12);
  await expect(page.getByRole("heading", { name: "What argues against this?" })).toBeVisible();
  await page.getByRole("button", { name: "View supporting evidence" }).click();
  await expect(page.locator("#mechanism-title")).toBeVisible();
  await page.getByRole("button", { name: "View conflicting evidence" }).click();
  await path
    .getByRole("button", { name: /Why this connection/ })
    .first()
    .click();
  await expect(page.getByRole("region", { name: "Connection evidence" })).toBeVisible();
  await expect(page.locator("#connection-detail")).toBeFocused();
  await expect(page.getByRole("heading", { name: "Relevant intervention research" })).toBeVisible();
}

// Keep helpers outside *.e2e.ts so they are not collected as tests.
export { expect, test };
