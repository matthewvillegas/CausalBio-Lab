import { expect, test, watchErrors } from "./helpers";
import { researchInterpretationFixture, researchResultFixture } from "../tests/research-fixture";

// These fixtures test UI contracts and safe routing. Live scientific output is
// checked separately by the research validation script, not simulated here.
test("broad tendon research exposes citations, partial retrieval, saved sessions and reports", async ({
  page,
}) => {
  const errors = watchErrors(page);
  const payloads: { question: string; depth: string; online: boolean }[] = [];
  const interpretation = { ...researchInterpretationFixture, depth: "quick" };
  const result = {
    ...researchResultFixture,
    interpretation,
    source_runs: [
      ...researchResultFixture.source_runs,
      {
        ...researchResultFixture.source_runs[0]!,
        source: "pubmed",
        status: "unavailable",
        record_count: 0,
        detail: "Synthetic provider timeout.",
      },
    ],
  };
  await page.route("**/api/v1/research/interpret", (route) =>
    route.fulfill({ json: interpretation }),
  );
  await page.route("**/api/v1/research", (route) => {
    payloads.push(route.request().postDataJSON());
    return route.fulfill({ json: result });
  });
  await page.route("**/api/v1/research/sessions", (route) =>
    route.fulfill({
      json: [
        {
          id: result.id,
          question: interpretation.question.original_text,
          mode: result.mode,
          created_at: result.created_at,
        },
      ],
    }),
  );
  await page.route(`**/api/v1/research/${result.id}`, (route) => route.fulfill({ json: result }));
  await page.context().route(`**/api/v1/research/${result.id}/report/html`, (route) =>
    route.fulfill({
      contentType: "text/html",
      body: "<!doctype html><title>Saved research report</title><h1>Synthetic saved research report</h1><p>Provisional evidence and retrieval dates retained.</p>",
    }),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.getByText("Research options", { exact: true }).click();
  await page.getByLabel("Search scope").selectOption("quick");
  await page
    .getByRole("button", { name: "What mechanisms influence tendon recovery?", exact: true })
    .click();
  await page.getByRole("button", { name: /Continue/ }).click();
  await expect(page.getByRole("heading", { name: "Research summary" })).toBeVisible();
  await expect(page.getByRole("status")).toContainText("1 source search was unavailable");
  await expect(page.getByRole("heading", { name: "References", exact: true })).not.toBeVisible();
  const citation = page.getByRole("button", { name: "Source 1", exact: true }).first();
  await citation.click();
  const drawer = page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  await expect(drawer).toContainText("Synthetic tendon evidence fixture");
  await page.keyboard.press("Escape");
  await expect(drawer).not.toBeVisible();
  await expect(citation).toBeFocused();
  await page.getByRole("button", { name: "Explore pathway, evidence and uncertainty" }).click();
  await expect(page.getByRole("heading", { name: "References", exact: true })).toBeVisible();
  await page.getByText("Study context and provenance", { exact: true }).click();
  await expect(page.getByText("Context not recorded: 1")).toBeVisible();
  await expect(page.getByText("Human: 0")).toBeVisible();
  const path = page.getByRole("list", { name: "Focused research pathway" });
  expect(await path.locator("li").count()).toBeLessThanOrEqual(12);
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole("button", { name: "Advanced analysis", exact: true }).click();
  await expect(page.getByText(/No executable pathway model/)).toBeVisible();
  const popupPromise = page.waitForEvent("popup");
  await page.getByRole("link", { name: "Read HTML report" }).click();
  const popup = await popupPromise;
  await expect(
    popup.getByRole("heading", { name: "Synthetic saved research report" }),
  ).toBeVisible();
  await popup.close();
  await page.getByRole("button", { name: "Library", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Curated investigations" })).toBeVisible();
  await page
    .getByRole("button", { name: /What mechanisms influence tendon recovery\? Saved/ })
    .click();
  await expect(page.getByRole("heading", { name: "Research summary" })).toBeVisible();
  expect(payloads).toHaveLength(1);
  expect(payloads[0]).toMatchObject({ depth: "quick", online: true });
  expect(errors).toEqual([]);
});

test("BDNF explanation is direct and deeper research offers an editable interpretation", async ({
  page,
}) => {
  const errors = watchErrors(page);
  const question = "What does BDNF do?";
  await page.route("**/api/v1/research/interpret", (route) =>
    route.fulfill({
      json: {
        ...researchInterpretationFixture,
        mode: "EXPLANATORY",
        depth: route.request().postDataJSON().depth,
        question: { ...researchInterpretationFixture.question, original_text: question },
      },
    }),
  );
  await page.route("**/api/v1/research", (route) =>
    route.fulfill({
      json: {
        ...researchResultFixture,
        mode: "EXPLANATORY",
        interpretation: {
          ...researchInterpretationFixture,
          mode: "EXPLANATORY",
          question: { ...researchInterpretationFixture.question, original_text: question },
        },
      },
    }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: question, exact: true }).click();
  await expect(page.getByRole("heading", { name: "Research summary" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "We interpreted your question as:" })).toHaveCount(
    0,
  );
  await page.getByRole("button", { name: "Expand evidence search" }).click();
  await expect(
    page.getByRole("heading", { name: "We interpreted your question as:" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit interpretation" }).click();
  await expect(page.getByRole("textbox", { name: "Outcome", exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("restricted question needs an explicit safe-research click before any retrieval", async ({
  page,
}) => {
  const safeQuestion = "What biological mechanisms involve insulin?";
  const retrieved: string[] = [];
  const interpreted: string[] = [];
  await page.route("**/api/v1/research/interpret", (route) => {
    const question = route.request().postDataJSON().question;
    interpreted.push(question);
    return route.fulfill({
      json: {
        ...researchInterpretationFixture,
        mode: question === safeQuestion ? "LIVE_RESEARCH" : "RESTRICTED_WITH_SAFE_ALTERNATIVE",
        safe_research_question: question === safeQuestion ? null : safeQuestion,
        notice:
          "I cannot provide personal dosing, but can investigate published biological mechanisms.",
      },
    });
  });
  await page.route("**/api/v1/research", (route) => {
    retrieved.push(route.request().postDataJSON().question);
    return route.fulfill({ json: researchResultFixture });
  });
  await page.goto("/");
  await page
    .getByRole("textbox", { name: /What biological question/ })
    .fill("How much insulin should I take?");
  await page.getByRole("main").getByRole("button", { name: "Investigate", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "I can help with the science, but not that action" }),
  ).toBeVisible();
  expect(retrieved).toEqual([]);
  expect(interpreted).toHaveLength(1);
  await page.getByRole("button", { name: "Investigate the biology" }).click();
  await page.getByRole("button", { name: /Continue/ }).click();
  await expect(page.getByRole("heading", { name: "Research summary" })).toBeVisible();
  expect(retrieved).toEqual([safeQuestion]);
});

test("offline research preserves its query and explains missing cached evidence", async ({
  page,
}) => {
  const errors = watchErrors(page);
  const requests: { online: boolean; question: string }[] = [];
  await page.route("**/api/v1/research/interpret", (route) => {
    requests.push(route.request().postDataJSON());
    return route.fulfill({ json: researchInterpretationFixture });
  });
  await page.route("**/api/v1/research", (route) => {
    requests.push(route.request().postDataJSON());
    return route.fulfill({
      json: {
        ...researchResultFixture,
        mode: "GENERAL_EVIDENCE_SUMMARY",
        direct_answer: [],
        mechanisms: [],
        evidence: [],
        graph: { ...researchResultFixture.graph, nodes: [], edges: [] },
        source_runs: [
          { ...researchResultFixture.source_runs[0]!, status: "offline", record_count: 0 },
        ],
        saved_locally: false,
      },
    });
  });
  await page.goto("/");
  await page.getByText("Research options", { exact: true }).click();
  await page
    .getByRole("checkbox", { name: "Use live scientific sources when available" })
    .uncheck();
  await expect(
    page.getByText("Offline — using cached/curated evidence", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "What mechanisms influence tendon recovery?", exact: true })
    .click();
  await page.getByRole("button", { name: /Continue/ }).click();
  await expect(
    page.getByText(/Offline mode — live literature research is unavailable/),
  ).toBeVisible();
  await expect(page.getByText(/could not retrieve enough evidence/)).toBeVisible();
  await expect(page.getByRole("button", { name: /Explore mechanism/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Read HTML report" })).toHaveCount(0);
  expect(requests).toHaveLength(2);
  expect(
    requests.every(
      (payload) =>
        !payload.online && payload.question === "What mechanisms influence tendon recovery?",
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Edit question", exact: true }).click();
  await expect(page.getByRole("textbox", { name: /What biological question/ })).toHaveValue(
    "What mechanisms influence tendon recovery?",
  );
  expect(errors).toEqual([]);
});
