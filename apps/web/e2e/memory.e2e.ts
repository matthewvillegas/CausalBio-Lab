import { expect, test, startInvestigation, inspectMechanism, watchErrors } from "./helpers";

test("memory: beginner mechanism journey, advanced graph, models, and readable report", async ({
  page,
  request,
}) => {
  const errors = watchErrors(page);
  const scientific: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().includes("/api/v1/")) scientific.push(r.url());
  });
  await startInvestigation(page, /long-term memory retention/i);
  expect(await page.locator("main").innerText()).not.toMatch(
    /HMC|R-hat|ESS|Petri marking|Graph projection|RDF/,
  );
  await inspectMechanism(page);
  await expect(
    page.getByRole("heading", { name: /Sleep-related/, exact: false }).last(),
  ).toBeVisible();
  await page.getByRole("button", { name: /Explore full evidence map/ }).click();
  const graph = page.getByRole("img", { name: /Interactive causal graph/ });
  await expect(graph).toBeVisible();
  const nodes = Number((await graph.getAttribute("aria-label"))?.match(/with (\d+)/)?.[1]);
  expect(nodes).toBeLessThanOrEqual(15);
  const before = scientific.length;
  await page.getByRole("button", { name: "Show full research graph" }).click();
  await page.getByLabel("Inspect a relationship").selectOption({
    label: "NREM slow-oscillation activity → CONTRIBUTES TO → Declarative-memory consolidation",
  });
  await expect(page.getByText(/larger crossover study found no effect/i)).toBeVisible();
  await page.getByRole("button", { name: "Fit to view", exact: true }).click();
  expect(scientific.length).toBe(before);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export current view" }).click();
  expect((await download).suggestedFilename()).toMatch(/visible-graph.json/);
  await page.getByRole("button", { name: "Pathway simulation", exact: true }).click();
  await page.getByRole("button", { name: "Run baseline comparison" }).click();
  await expect(page.getByRole("heading", { name: "What changed?" })).toBeVisible();
  await page.getByRole("button", { name: "Uncertainty analysis", exact: true }).click();
  await expect(page.getByText(/For this investigation:/)).toBeVisible();
  await page.getByRole("button", { name: "Run uncertainty demonstration" }).click();
  await expect(page.getByText("Posterior parameter estimates")).toBeVisible();
  await expect(page.getByText("Rank-normalized R-hat max")).not.toBeVisible();
  await page.getByText("Advanced mathematical details", { exact: true }).click();
  await expect(page.getByText("Rank-normalized R-hat max")).toBeVisible();
  await expect(page.getByLabel("Trace plot for condition_effect")).toBeVisible();
  await page.getByRole("button", { name: "Known peptides", exact: true }).click();
  await page.getByRole("button", { name: "Analyze known record" }).click();
  await expect(page.getByRole("heading", { name: "Substance P", exact: true })).toBeVisible();
  await expect(page.getByText("RPKPQQFFGLM", { exact: true }).first()).not.toBeVisible();
  await page.getByText("Advanced peptide properties", { exact: true }).click();
  await expect(page.getByText("RPKPQQFFGLM", { exact: true }).first()).toBeVisible();
  const afterRuns = scientific.length;
  await page.getByRole("button", { name: "Pathway simulation", exact: true }).click();
  await expect(page.getByRole("heading", { name: "What changed?" })).toBeVisible();
  expect(scientific.length).toBe(afterRuns);
  await page.getByRole("button", { name: /Research report ↓/ }).click();
  await page.getByRole("button", { name: "Generate research report" }).click();
  const report = page.getByRole("link", { name: /Read.*HTML|HTML.*report/i });
  await expect(report).toBeVisible();
  const response = await request.get((await report.getAttribute("href"))!);
  expect(response.status()).toBe(200);
  expect(await response.text()).toContain("Research summary");
  expect(errors).toEqual([]);
});

test("ambiguous, broad, invalid and restricted questions explain the next step", async ({
  page,
}) => {
  await page.goto("/");
  const question = page.getByRole("textbox", { name: /What biological question/ });
  const submit = page.getByRole("main").getByRole("button", { name: "Investigate", exact: true });
  await expect(submit).toBeDisabled();
  await question.fill("  ");
  await expect(submit).toBeDisabled();
  for (const [value, title] of [
    ["How do memory and knee pain mechanisms interact?", "More information needed"],
    ["How is insulin sensitivity regulated?", "We interpreted your question as:"],
    [
      "What peptide dose should I inject myself for memory?",
      "I can help with the science, but not that action",
    ],
  ]) {
    await question.fill(value!);
    await submit.click();
    await expect(page.getByRole("heading", { name: title!, exact: true })).toBeVisible();
    await expect(page.getByText(/Correlation ID:/)).not.toBeVisible();
    await page.getByRole("button", { name: "Return to CausalBio Lab home" }).click();
  }
});
