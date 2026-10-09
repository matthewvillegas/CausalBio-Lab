import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium, expect } from "@playwright/test";

const workspace = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const output = resolve(workspace, process.env.CAUSALBIO_DESIGN_OUTPUT ?? "docs/assets/design");
const baseURL = process.env.CAUSALBIO_SCREENSHOT_URL ?? "http://127.0.0.1:3000";
const viewports = [
  { width: 1440, height: 1000 },
  { width: 1024, height: 768 },
  { width: 390, height: 844 },
];
const tendonQuestion = "What mechanisms influence tendon recovery?";
const captures = [];
const issues = [];
const checks = [];
const results = [];
const contrast = [];
const metrics = {};
let phase = "real production workflow";
let tendonResult;
let completed = false;

await mkdir(output, { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: viewports[0], deviceScaleFactor: 1 });
await context.addInitScript(() => {
  window.__reviewCLS = 0;
  window.__reviewLongTasks = [];
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (!entry.hadRecentInput) window.__reviewCLS += entry.value;
    }
  }).observe({ type: "layout-shift", buffered: true });
  if (PerformanceObserver.supportedEntryTypes.includes("longtask")) {
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        window.__reviewLongTasks.push({ start: entry.startTime, duration: entry.duration });
      }
    }).observe({ type: "longtask", buffered: true });
  }
});

function observe(page) {
  page.setDefaultTimeout(45_000);
  page.on("pageerror", (error) =>
    issues.push({ phase, type: "pageerror", message: error.message }),
  );
  page.on("console", (message) => {
    if (["warning", "error"].includes(message.type())) {
      issues.push({ phase, type: message.type(), message: message.text() });
    }
  });
}

const page = await context.newPage();
observe(page);

async function measure(target = page) {
  return target.evaluate(() => ({
    cls: window.__reviewCLS,
    navigation: performance.getEntriesByType("navigation").map((entry) => ({
      domContentLoaded: entry.domContentLoadedEventEnd,
      load: entry.loadEventEnd,
      response: entry.responseEnd,
    })),
    paints: performance.getEntriesByType("paint").map((entry) => ({
      name: entry.name,
      time: entry.startTime,
    })),
    resources: performance.getEntriesByType("resource").map((entry) => ({
      name: entry.name,
      kind: entry.initiatorType,
      transfer: entry.transferSize,
      encoded: entry.encodedBodySize,
      decoded: entry.decodedBodySize,
      duration: entry.duration,
    })),
    fonts: [...document.fonts].map((font) => ({ family: font.family, status: font.status })),
    bodyFont: getComputedStyle(document.body).fontFamily,
    headingFont: document.querySelector("h1")
      ? getComputedStyle(document.querySelector("h1")).fontFamily
      : null,
    longTasks: window.__reviewLongTasks,
  }));
}

async function capture(name, anchor, target = page) {
  for (const viewport of viewports) {
    await target.setViewportSize(viewport);
    await target.evaluate(() => document.fonts.ready);
    if (anchor) {
      await anchor.evaluate((element) =>
        element.scrollIntoView({ behavior: "instant", block: "start" }),
      );
    } else {
      await target.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    }
    await target.locator("dialog[open]").evaluateAll((dialogs) => {
      for (const dialog of dialogs) dialog.scrollTo({ top: 0, behavior: "instant" });
    });
    await target.waitForTimeout(220);
    const geometry = await target.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: innerWidth,
      scrollContainers: [...document.querySelectorAll("main *")]
        .filter((element) => {
          const { overflowX } = getComputedStyle(element);
          return (
            ["auto", "scroll"].includes(overflowX) && element.scrollWidth > element.clientWidth
          );
        })
        .map((element) => ({
          tag: element.tagName,
          label: element.getAttribute("aria-label"),
          width: element.clientWidth,
          contentWidth: element.scrollWidth,
          keyboardFocusable: element.tabIndex >= 0,
        })),
    }));
    const filename = `${name}-${viewport.width}.png`;
    await target.screenshot({ path: resolve(output, filename), fullPage: false });
    captures.push({ name, filename, viewport, phase, ...geometry });
    expect(geometry.documentWidth, `${filename}: document overflow`).toBeLessThanOrEqual(
      viewport.width,
    );
  }
  await target.setViewportSize(viewports[0]);
  console.log(`Captured ${name} at all three sizes.`);
}

async function sampleContrast(name, target = page) {
  const samples = await target.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 1;
    const drawing = canvas.getContext("2d", { willReadFrequently: true });
    function rgba(color) {
      drawing.clearRect(0, 0, 1, 1);
      drawing.fillStyle = color;
      drawing.fillRect(0, 0, 1, 1);
      return [...drawing.getImageData(0, 0, 1, 1).data].map((value, index) =>
        index === 3 ? value / 255 : value,
      );
    }
    function over(foreground, background) {
      return foreground
        .slice(0, 3)
        .map((channel, index) => channel * foreground[3] + background[index] * (1 - foreground[3]));
    }
    function luminance(color) {
      const linear = color.slice(0, 3).map((channel) => {
        const value = channel / 255;
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
      });
      return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
    }
    const visibleRoot = document.querySelector("dialog[open]") ?? document;
    return [...visibleRoot.querySelectorAll("h1,h2,h3,p,a,button,label,dt,dd,summary,figcaption")]
      .filter((element) => {
        const rect = element.getBoundingClientRect();
        return (
          rect.width > 0 &&
          rect.height > 0 &&
          rect.bottom > 0 &&
          rect.top < innerHeight &&
          !element.closest("[hidden]")
        );
      })
      .slice(0, 120)
      .map((element) => {
        const style = getComputedStyle(element);
        const ancestors = [];
        for (let current = element; current; current = current.parentElement)
          ancestors.unshift(current);
        let background = [255, 255, 255];
        const unsupported = ancestors.some((parent) => {
          const computed = getComputedStyle(parent);
          return computed.backgroundImage !== "none" || Number(computed.opacity) < 1;
        });
        for (const parent of ancestors)
          background = over(rgba(getComputedStyle(parent).backgroundColor), background);
        const foreground = over(rgba(style.color), background);
        const first = luminance(foreground);
        const second = luminance(background);
        const ratio = (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
        const large =
          parseFloat(style.fontSize) >= 24 ||
          (parseFloat(style.fontSize) >= 18.66 && Number(style.fontWeight) >= 700);
        return {
          tag: element.tagName,
          text: element.textContent.trim().replace(/\s+/g, " ").slice(0, 90),
          color: style.color,
          background,
          fontSize: style.fontSize,
          ratio: Number(ratio.toFixed(2)),
          required: large ? 3 : 4.5,
          excluded: element.matches(":disabled")
            ? "disabled control"
            : unsupported
              ? "background image or opacity requires visual review"
              : null,
        };
      });
  });
  contrast.push({
    name,
    samples,
    failures: samples.filter((sample) => !sample.excluded && sample.ratio < sample.required),
  });
}

async function home() {
  await page.goto(baseURL, { waitUntil: "networkidle" });
  await expect(page.getByRole("textbox", { name: /What biological question/ })).toBeVisible();
  await expect(
    page.getByRole("button", { name: /long-term memory retention/i }).first(),
  ).toBeVisible();
  await expect(page.locator(".service-status")).not.toContainText("status unavailable");
  await page.evaluate(() => document.fonts.ready);
}

async function submit(question) {
  await page.getByRole("textbox", { name: /What biological question/ }).fill(question);
  await page.getByRole("main").getByRole("button", { name: "Investigate", exact: true }).click();
}

async function research(question, interpretationCapture) {
  const response = page.waitForResponse(
    (item) => item.url().endsWith("/api/v1/research") && item.request().method() === "POST",
  );
  await submit(question);
  await expect(
    page.getByRole("heading", { name: "We interpreted your question as:" }),
  ).toBeVisible();
  if (interpretationCapture) await capture(interpretationCapture);
  await page.getByRole("button", { name: /Continue/ }).click();
  const result = await (await response).json();
  await expect(
    page.getByRole("heading", { name: "Research summary", exact: true }).first(),
  ).toBeVisible();
  return result;
}

function recordResult(result) {
  results.push({
    id: result.id,
    question: result.interpretation.question.original_text,
    mode: result.mode,
    saved_locally: result.saved_locally,
    evidence_count: result.evidence.length,
    mechanism_count: result.mechanisms.length,
    sources: result.source_runs,
    evidence: result.evidence.map(
      ({ id, source, source_record_id, retrieved_at, cache_status }) => ({
        id,
        source,
        source_record_id,
        retrieved_at,
        cache_status,
      }),
    ),
  });
}

async function reportCapture(name, link) {
  const reportPage = await context.newPage();
  observe(reportPage);
  try {
    await reportPage.goto(await link.getAttribute("href"), { waitUntil: "networkidle" });
    await expect(reportPage.locator("h1")).toBeVisible();
    await capture(name, null, reportPage);
  } finally {
    await reportPage.close();
  }
}

try {
  await home();
  metrics.landing = await measure();
  await capture("landing");
  await sampleContrast("landing-light");
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await capture("landing-dark");
  await sampleContrast("landing-dark");
  await page.getByRole("button", { name: "Switch to light mode" }).click();

  tendonResult = await research(tendonQuestion, "live-interpretation");
  recordResult(tendonResult);
  expect(tendonResult.evidence.length).toBeGreaterThan(0);
  await capture("live-summary");
  await sampleContrast("live-summary-light");
  await capture(
    "live-mechanisms",
    page.getByRole("heading", { name: "Possible mechanisms", exact: true }),
  );
  await page
    .getByRole("button", { name: /Explore mechanism/ })
    .first()
    .click();
  await capture(
    "live-pathway",
    page.getByRole("heading", { name: "Focused pathway", exact: true }),
  );

  const citation = page.getByRole("button", { name: /^Source \d+$/ }).first();
  await citation.focus();
  await page.keyboard.press("Enter");
  const drawer = page.getByRole("dialog");
  await expect(drawer).toBeVisible();
  expect(await drawer.evaluate((element) => element.contains(document.activeElement))).toBe(true);
  const controls = await drawer
    .locator("button,a[href],input,select,textarea,[tabindex='0']")
    .count();
  for (let index = 0; index < controls + 2; index += 1) {
    await page.keyboard.press("Tab");
    // Chromium permits browser-chrome focus while the page behind a modal remains inert.
    expect(
      await drawer.evaluate(
        (element) => !document.hasFocus() || element.contains(document.activeElement),
      ),
    ).toBe(true);
  }
  await capture("citation-drawer");
  await sampleContrast("citation-drawer-light");
  await page.keyboard.press("Escape");
  await expect(drawer).toHaveCount(0);
  await expect(citation).toBeFocused();
  checks.push(
    "Citation opens with Enter; Tab stays in the dialog whenever the document has focus (native Chromium can visit browser chrome); Escape closes it and restores the citation's focus.",
  );
  await capture("live-references", page.getByRole("heading", { name: "References", exact: true }));
  await reportCapture("live-html-report", page.getByRole("link", { name: "Read HTML report" }));
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await capture("live-summary-dark");
  await sampleContrast("live-summary-dark");
  await page.getByRole("button", { name: "Switch to light mode" }).click();

  await home();
  await page
    .getByRole("button", { name: /long-term memory retention/i })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "We interpreted your question as:" }),
  ).toBeVisible();
  await capture("curated-interpretation");
  await page.getByRole("button", { name: /Continue/ }).click();
  await expect(
    page.getByRole("heading", { name: "Possible mechanisms", exact: true }),
  ).toBeVisible();
  await capture("curated-summary");
  await capture(
    "curated-mechanisms",
    page.getByRole("heading", { name: "Possible mechanisms", exact: true }),
  );
  await page
    .getByRole("button", { name: /Explore mechanism/ })
    .first()
    .click();
  await capture("curated-pathway", page.locator("#mechanism-title"));
  await page
    .getByRole("list", { name: "Focused biological pathway" })
    .getByRole("button", { name: /Why this connection/ })
    .first()
    .click();
  await capture("curated-evidence", page.getByRole("region", { name: "Connection evidence" }));
  metrics.beforeGraph = await measure();
  const graphStart = Date.now();
  await page.getByRole("button", { name: /Explore full (?:causal|evidence) map/ }).click();
  const graph = page.getByRole("img", { name: /Interactive causal graph/ });
  await expect(graph).toBeVisible();
  await expect(graph.locator("canvas").first()).toBeVisible();
  metrics.graphOpenToCanvasMs = Date.now() - graphStart;
  metrics.afterGraph = await measure();
  await page.getByRole("button", { name: "Show full research graph" }).click();
  await page.getByRole("button", { name: "Fit to view", exact: true }).click();
  await capture("full-graph", graph);
  await page.getByLabel("Inspect a relationship").selectOption({
    label: "NREM slow-oscillation activity → CONTRIBUTES TO → Declarative-memory consolidation",
  });
  await expect(page.getByText(/larger crossover study found no effect/i)).toBeVisible();
  checks.push("Full graph retains keyboard relationship inspection and conflicting evidence.");
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await capture("full-graph-dark", graph);
  await page.getByRole("button", { name: "Switch to light mode" }).click();

  await page.getByRole("button", { name: "Pathway simulation", exact: true }).click();
  await page.getByRole("button", { name: "Run baseline comparison" }).click();
  const changed = page.getByRole("heading", { name: "What changed?" });
  await expect(changed).toBeVisible();
  await capture(
    "simulation",
    page.getByRole("heading", { name: "Pathway simulation", exact: true }),
  );
  await capture("simulation-trajectory", page.getByLabel("Simulation trajectory chart"));
  await page.getByRole("button", { name: "Uncertainty analysis", exact: true }).click();
  await page.getByRole("button", { name: "Run uncertainty demonstration" }).click();
  const posterior = page.getByText("Posterior parameter estimates");
  await expect(posterior).toBeVisible();
  await capture("bayesian", posterior);
  await page.getByRole("button", { name: /Research report ↓/ }).click();
  await page.getByRole("button", { name: "Generate research report" }).click();
  const curatedReport = page.getByRole("link", { name: "Read HTML report" });
  await expect(curatedReport).toBeVisible();
  await capture("report-panel", page.locator("#panel-report"));
  await reportCapture("curated-html-report", curatedReport);

  await page.getByRole("button", { name: "Library", exact: true }).click();
  await expect(
    page.getByRole("button", { name: /What mechanisms influence tendon recovery\? Saved/ }).first(),
  ).toBeVisible();
  await capture("library");
  await capture(
    "saved-investigations",
    page.getByRole("heading", { name: "Recent investigations" }),
  );
  await page
    .getByRole("button", { name: /What mechanisms influence tendon recovery\? Saved/ })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Research summary", exact: true }).first(),
  ).toBeVisible();
  checks.push("Saved tendon research reopens through the production session endpoint.");
  await page.getByRole("button", { name: "About", exact: true }).click();
  await capture("about");

  await home();
  const explanation = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/research") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "What does BDNF do?", exact: true }).click();
  recordResult(await (await explanation).json());
  await expect(
    page.getByRole("heading", { name: "Research summary", exact: true }).first(),
  ).toBeVisible();
  await capture("bdnf-explanation");
  await page.getByRole("button", { name: "Expand evidence search" }).click();
  await expect(
    page.getByRole("heading", { name: "We interpreted your question as:" }),
  ).toBeVisible();
  checks.push("Explanation opens directly; expanded search exposes editable interpretation.");

  await home();
  let restrictedRetrievals = 0;
  const countRetrieval = (request) => {
    if (request.url().endsWith("/api/v1/research") && request.method() === "POST")
      restrictedRetrievals += 1;
  };
  page.on("request", countRetrieval);
  await submit("How much selegiline should I take for memory?");
  await expect(
    page.getByRole("heading", { name: "I can help with the science, but not that action" }),
  ).toBeVisible();
  await capture("safety-alternative");
  expect(restrictedRetrievals).toBe(0);
  await page.getByRole("button", { name: "Investigate the biology" }).click();
  await expect(
    page
      .getByRole("heading", { name: "We interpreted your question as:" })
      .or(page.getByRole("heading", { name: "Research summary", exact: true }).first()),
  ).toBeVisible();
  expect(restrictedRetrievals).toBeLessThanOrEqual(1);
  page.off("request", countRetrieval);
  checks.push(
    "Restricted request makes no retrieval; the explicit safe-research click starts the offered scientific question.",
  );
  await home();
  await submit("retention");
  await expect(page.getByRole("heading", { name: "More information needed" })).toBeVisible();
  await capture("clarification");

  phase = "controlled UI fixture: delayed real result snapshot";
  let releaseLoading;
  const loadingGate = new Promise((resolveGate) => {
    releaseLoading = resolveGate;
  });
  await page.route("**/api/v1/research", async (route) => {
    await loadingGate;
    await route.fulfill({ json: tendonResult });
  });
  await home();
  await submit(tendonQuestion);
  await page.getByRole("button", { name: /Continue/ }).click();
  await expect(page.getByRole("heading", { name: "Researching your question" })).toBeVisible();
  await capture("loading");
  releaseLoading();
  await expect(
    page.getByRole("heading", { name: "Research summary", exact: true }).first(),
  ).toBeVisible();
  await page.unroute("**/api/v1/research");

  phase = "controlled UI fixture: partial provider availability";
  const partial = structuredClone(tendonResult);
  partial.source_runs.push({
    source: "pubmed",
    provider_version: null,
    query: tendonQuestion,
    status: "unavailable",
    record_count: 0,
    retrieved_at: null,
    detail:
      "UI review fixture: provider timeout; retained evidence is from the real captured result.",
  });
  partial.saved_locally = false;
  await page.route("**/api/v1/research", (route) => route.fulfill({ json: partial }));
  await home();
  await research(tendonQuestion);
  await expect(
    page.getByRole("status").filter({ hasText: /source search.*unavailable/ }),
  ).toBeVisible();
  await capture("partial-result");
  await page.unroute("**/api/v1/research");

  phase = "controlled UI fixture: offline without cached evidence";
  const empty = {
    ...structuredClone(tendonResult),
    direct_answer: [],
    mechanisms: [],
    evidence: [],
    graph: { ...tendonResult.graph, nodes: [], edges: [] },
    complications: [],
    modifiers: [],
    notices: ["No cached evidence is available for this question."],
    saved_locally: false,
    source_runs: [
      {
        source: "europe_pmc",
        provider_version: null,
        query: tendonQuestion,
        status: "offline",
        record_count: 0,
        retrieved_at: null,
        detail: "UI review fixture: no cached records.",
      },
    ],
  };
  await page.route("**/api/v1/research", (route) => route.fulfill({ json: empty }));
  await home();
  await page.getByText("Research options", { exact: true }).click();
  await page
    .getByRole("checkbox", { name: "Use live scientific sources when available" })
    .uncheck();
  await research(tendonQuestion);
  await expect(page.getByText(/could not retrieve enough evidence/)).toBeVisible();
  await capture("empty-offline-result");
  await page.unroute("**/api/v1/research");

  phase = "controlled UI fixture: unavailable interpretation API";
  await page.route("**/api/v1/research/interpret", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/problem+json",
      json: {
        type: "about:blank",
        title: "Research service unavailable",
        status: 503,
        detail:
          "The research service could not be reached. Your question has been kept so you can try again.",
        correlation_id: "design-review-fixture",
        alternatives: [],
      },
    }),
  );
  await home();
  await submit(tendonQuestion);
  await expect(
    page.getByRole("alert").getByRole("heading", { name: "Research service unavailable" }),
  ).toBeVisible();
  await capture("network-error");
  await page.unroute("**/api/v1/research/interpret");

  phase = "controlled UI fixture: empty saved investigations";
  await page.route("**/api/v1/research/sessions", (route) => route.fulfill({ json: [] }));
  await home();
  await page.getByRole("button", { name: "Library", exact: true }).click();
  await expect(page.getByText("Your locally saved research will appear here.")).toBeVisible();
  await capture("empty-library");
  await page.unroute("**/api/v1/research/sessions");

  await page.emulateMedia({ reducedMotion: "reduce" });
  metrics.reducedMotion = await page.evaluate(() => ({
    matches: matchMedia("(prefers-reduced-motion: reduce)").matches,
    scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
    buttonTransition: getComputedStyle(document.querySelector("button")).transitionDuration,
  }));
  expect(metrics.reducedMotion.matches).toBe(true);
  expect(metrics.reducedMotion.scrollBehavior).toBe("auto");
  checks.push("Reduced-motion preference is active and page scrolling is not animated.");
  let baseline;
  try {
    baseline = JSON.parse(
      await readFile(resolve(workspace, "artifacts/design-before/baseline.json"), "utf8"),
    );
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  const summarize = (measurement) => ({
    cls: measurement.cls,
    javascriptEncodedBytes: measurement.resources
      .filter((resource) => /\.js(?:\?|$)/.test(resource.name))
      .reduce((total, resource) => total + resource.encoded, 0),
    fontEncodedBytes: measurement.resources
      .filter((resource) => /\.(?:woff2?|ttf)(?:\?|$)/.test(resource.name))
      .reduce((total, resource) => total + resource.encoded, 0),
  });
  metrics.comparison = {
    baseline: baseline ? summarize(baseline.landing) : null,
    current: summarize(metrics.landing),
    limitation:
      "Single local samples on an unthrottled production server; not a field performance benchmark.",
  };
  const unexpected = issues.filter(
    (issue) =>
      !(
        issue.phase === "controlled UI fixture: unavailable interpretation API" &&
        issue.type === "error" &&
        issue.message.includes("503")
      ),
  );
  expect(unexpected).toEqual([]);
  completed = true;
} finally {
  await writeFile(
    resolve(output, "review-record.json"),
    JSON.stringify(
      {
        captured_at: new Date().toISOString(),
        completed,
        baseURL,
        viewports,
        captures,
        checks,
        results,
        issues,
        metrics,
        contrast,
        limitations: [
          "Screenshots require visual review; their existence does not establish design quality.",
          "Contrast samples cover visible rendered text with solid backgrounds, not all WCAG criteria or all UI states.",
          "Injected loading/error/partial/empty states are explicitly labeled; they are not observations of provider availability.",
          "Production research can reuse provider cache; source statuses and retrieval timestamps are retained above.",
        ],
      },
      null,
      2,
    ) + "\n",
  );
  await browser.close();
}
console.log(`Saved ${captures.length} production design captures and review-record.json.`);
