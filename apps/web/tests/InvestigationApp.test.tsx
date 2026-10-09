import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { InvestigationApp } from "@/components/InvestigationApp";
import { interpretationFixture, investigationFixture } from "@/tests/fixture";
import { researchInterpretationFixture, researchResultFixture } from "@/tests/research-fixture";
function response(body: object, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}
const library = [
  {
    slug: "memory",
    title: "Memory retention",
    description: "Curated example",
    example_questions: [investigationFixture.question.original_text],
  },
];
function mockService(replies: Response[]) {
  const scientific = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.endsWith("/demo-cases")) return response(library);
      if (url.endsWith("/research/status"))
        return response({
          live_enabled: true,
          status_label: "Live research enabled",
          sources: ["europe_pmc"],
        });
      if (url.endsWith("/research/sessions")) return response([]);
      scientific(url);
      return replies.shift() ?? response({}, 500);
    }),
  );
  return scientific;
}

describe("InvestigationApp", () => {
  afterEach(() => vi.unstubAllGlobals());
  it("has one obvious action and shows the server-provided library without technical settings", async () => {
    mockService([]);
    render(<InvestigationApp />);
    expect(
      screen.getByRole("heading", { name: "Investigate biological mechanisms" }),
    ).toBeVisible();
    expect(
      within(screen.getByRole("main")).getByRole("button", { name: "Investigate" }),
    ).toBeDisabled();
    expect(await screen.findByRole("button", { name: /Memory retention/ })).toBeEnabled();
    expect(screen.queryByText(/Petri|HMC|R-hat/)).not.toBeInTheDocument();
  });
  it("confirms a plain interpretation, supports edits, then builds mechanism cards", async () => {
    const scientific = mockService([
      response({ ...researchInterpretationFixture, ...interpretationFixture, mode: "CURATED" }),
      response(investigationFixture, 201),
    ]);
    const user = userEvent.setup();
    render(<InvestigationApp />);
    await user.click(await screen.findByRole("button", { name: /Memory retention/ }));
    expect(
      await screen.findByRole("heading", { name: "We interpreted your question as:" }),
    ).toBeVisible();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Edit interpretation" }));
    expect(screen.getByLabelText("Outcome")).toHaveValue("long-term memory persistence");
    await user.click(screen.getByRole("button", { name: /Continue/ }));
    expect(await screen.findByRole("heading", { name: "Possible mechanisms" })).toBeVisible();
    expect(scientific).toHaveBeenCalledTimes(2);
  });
  it("keeps a broad question in the research workflow and shows provisional evidence", async () => {
    const scientific = mockService([
      response(researchInterpretationFixture),
      response(researchResultFixture),
    ]);
    const user = userEvent.setup();
    render(<InvestigationApp />);
    await user.click(
      screen.getByRole("button", { name: "What mechanisms influence tendon recovery?" }),
    );
    expect(
      await screen.findByRole("heading", { name: "We interpreted your question as:" }),
    ).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Continue/ }));
    expect(await screen.findByRole("heading", { name: "Research summary" })).toBeVisible();
    expect(screen.getByText(/not been reviewed as curated CausalBio evidence/)).toBeVisible();
    expect(screen.getByRole("link", { name: "Read HTML report" })).toHaveAttribute(
      "href",
      expect.stringContaining(`/research/${researchResultFixture.id}/report/html`),
    );
    expect(scientific.mock.calls.map(([url]) => url)).toEqual([
      expect.stringContaining("/research/interpret"),
      expect.stringMatching(/\/research$/),
    ]);
  });
  it("shows an explanation without context confirmation and offers deeper investigation", async () => {
    const interpretation = {
      ...researchInterpretationFixture,
      mode: "EXPLANATORY",
      question: { ...researchInterpretationFixture.question, original_text: "What does BDNF do?" },
    };
    mockService([
      response(interpretation),
      response({ ...researchResultFixture, mode: "EXPLANATORY", interpretation }),
      response({ ...interpretation, depth: "deep" }),
    ]);
    const user = userEvent.setup();
    render(<InvestigationApp />);
    await user.click(screen.getByRole("button", { name: "What does BDNF do?" }));
    expect(await screen.findByRole("heading", { name: "Research summary" })).toBeVisible();
    expect(screen.queryByText("We interpreted your question as:")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Expand evidence search" }));
    expect(
      await screen.findByRole("heading", { name: "We interpreted your question as:" }),
    ).toBeVisible();
  });
  it("waits for the user before investigating a restricted request's safe alternative", async () => {
    const scientific = mockService([
      response({
        ...researchInterpretationFixture,
        mode: "RESTRICTED_WITH_SAFE_ALTERNATIVE",
        safe_research_question: "What mechanisms involve insulin?",
        notice: "I cannot provide personal dosing. I can investigate published mechanisms.",
      }),
      response(researchInterpretationFixture),
    ]);
    const user = userEvent.setup();
    render(<InvestigationApp />);
    await user.type(
      screen.getByLabelText(/What biological question/),
      "How much insulin should I take?",
    );
    await user.click(within(screen.getByRole("main")).getByRole("button", { name: "Investigate" }));
    expect(await screen.findByRole("button", { name: "Investigate the biology" })).toBeEnabled();
    expect(scientific).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "Investigate the biology" }));
    expect(
      await screen.findByRole("heading", { name: "We interpreted your question as:" }),
    ).toBeVisible();
    expect(scientific).toHaveBeenCalledTimes(2);
  });
  it("offers recovery for ambiguous input and hides technical details", async () => {
    mockService([
      response(
        {
          type: "about:blank",
          title: "The question needs clarification",
          status: 422,
          detail: "Retention needs an outcome.",
          correlation_id: "test-id",
          alternatives: ["long-term memory retention"],
        },
        422,
      ),
    ]);
    const user = userEvent.setup();
    render(<InvestigationApp />);
    await user.type(screen.getByLabelText(/What biological question/), "retention");
    await user.click(within(screen.getByRole("main")).getByRole("button", { name: "Investigate" }));
    expect(
      await screen.findByRole("heading", { name: "The question needs clarification" }),
    ).toBeVisible();
    expect(screen.getByRole("button", { name: "long-term memory retention" })).toBeEnabled();
    expect(screen.getByText(/Correlation ID:/)).not.toBeVisible();
    await user.click(screen.getByText("Technical details"));
    expect(screen.getByText(/Correlation ID: test-id/)).toBeVisible();
  });
});
