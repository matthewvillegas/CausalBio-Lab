import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { UniversalResultsView } from "@/components/UniversalResultsView";
import { researchResultFixture } from "./research-fixture";

describe("UniversalResultsView", () => {
  it("keeps unknown study context unknown and makes citations reachable from Quick mode", async () => {
    const user = userEvent.setup();
    render(
      <UniversalResultsView
        result={{
          ...researchResultFixture,
          interpretation: { ...researchResultFixture.interpretation, depth: "quick" },
          evidence: researchResultFixture.evidence.map((item) => ({
            ...item,
            study_type: "Comparative study",
          })),
        }}
        onDeeper={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByRole("heading", { name: "Research summary" })).toBeVisible();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    const sourceButton = screen.getAllByRole("button", { name: "Source 1" })[0]!;
    await user.click(sourceButton);
    const drawer = within(screen.getByRole("dialog", { name: "Reference 1" }));
    expect(
      drawer.getByRole("heading", { name: /Synthetic tendon evidence fixture/ }),
    ).toBeVisible();
    expect(drawer.getByText(researchResultFixture.direct_answer[0]!.source_passage!)).toBeVisible();
    expect(drawer.getByText("Journal").nextElementSibling).toHaveTextContent("Not recorded");
    expect(drawer.getByText("Organism").nextElementSibling).toHaveTextContent("Not recorded");
    expect(drawer.getByRole("link", { name: "Read original source ↗" })).toHaveAttribute(
      "href",
      researchResultFixture.evidence[0]!.source_url,
    );
    await user.click(drawer.getByRole("button", { name: "Close evidence" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(sourceButton).toHaveFocus();
    await user.click(
      screen.getByRole("button", { name: "Explore pathway, evidence and uncertainty" }),
    );
    expect(screen.getByText("Human: 0")).toBeVisible();
    expect(screen.getByText("Animal: 0")).toBeVisible();
    expect(screen.getByText("Context not recorded: 1")).toBeVisible();
    await user.click(screen.getByText("Study context and provenance"));
    expect(screen.getAllByText("Not recorded").length).toBeGreaterThan(5);
    await user.click(screen.getByRole("button", { name: "Advanced analysis" }));
    expect(screen.getByText(/No executable pathway model/)).toBeVisible();
  });
  it("distinguishes online cache hits from offline research and exposes partial failure", () => {
    render(
      <UniversalResultsView
        result={{
          ...researchResultFixture,
          evidence: researchResultFixture.evidence.map((item) => ({
            ...item,
            cache_status: "stale_cache",
          })),
          source_runs: [
            { ...researchResultFixture.source_runs[0]!, status: "cached" },
            {
              ...researchResultFixture.source_runs[0]!,
              source: "pubmed",
              status: "unavailable",
              record_count: 0,
            },
          ],
        }}
        onDeeper={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText(/Using cached evidence/)).toBeVisible();
    expect(screen.queryByText(/Offline mode/)).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("1 source search was unavailable");
    expect(screen.getByText(/freshness has expired/)).toBeVisible();
  });
  it.each(["EXPLANATORY", "LIVE_RESEARCH"] as const)(
    "can expand the evidence search from %s results",
    async (mode) => {
      const user = userEvent.setup();
      const onDeeper = vi.fn();
      render(
        <UniversalResultsView
          result={{ ...researchResultFixture, mode }}
          onDeeper={onDeeper}
          onRetry={vi.fn()}
        />,
      );
      await user.click(screen.getByRole("button", { name: "Expand evidence search" }));
      expect(onDeeper).toHaveBeenCalledOnce();
    },
  );
  it("separates a human protein annotation from human studies and exposes its evidence provenance", async () => {
    const user = userEvent.setup();
    render(
      <UniversalResultsView
        result={{
          ...researchResultFixture,
          evidence: researchResultFixture.evidence.map((item) => ({
            ...item,
            source: "uniprot",
            organism: "Homo sapiens",
            annotation_evidence: [
              { evidence_code: "ECO:0000269", source: "PubMed", identifier: "11111111" },
            ],
          })),
        }}
        onDeeper={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText("Human: 0")).toBeVisible();
    expect(screen.getByText("Database annotation: 1")).toBeVisible();
    expect(screen.getByText(/Protein database annotation/)).toBeVisible();
    await user.click(screen.getByText("Study context and provenance"));
    expect(screen.getByText(/ECO:0000269/, { selector: "li" })).toBeVisible();
    expect(screen.getByRole("link", { name: "11111111 ↗" })).toHaveAttribute(
      "href",
      "https://pubmed.ncbi.nlm.nih.gov/11111111/",
    );
  });
  it.each(["other-claim", researchResultFixture.mechanisms[0]!.claims[0]!.id])(
    "keeps shared evidence and claim %s within its selected mechanism pathway",
    (otherClaimId) => {
      const edge = researchResultFixture.graph.edges[0]!;
      const mechanism = researchResultFixture.mechanisms[0]!;
      render(
        <UniversalResultsView
          result={{
            ...researchResultFixture,
            mechanisms: [
              ...researchResultFixture.mechanisms,
              {
                ...mechanism,
                id: "other-mechanism",
                title: "Another mechanism",
                claims: [{ ...mechanism.claims[0]!, id: otherClaimId }],
              },
            ],
            graph: {
              ...researchResultFixture.graph,
              nodes: [
                ...researchResultFixture.graph.nodes,
                {
                  id: "other-mechanism",
                  name: "Another mechanism",
                  entity_type: "mechanism",
                  identifiers: {},
                },
              ],
              edges: [
                ...researchResultFixture.graph.edges,
                {
                  ...edge,
                  id: "other-edge",
                  subject_id: "other-mechanism",
                  claim_id: otherClaimId,
                },
              ],
            },
          }}
          onDeeper={vi.fn()}
          onRetry={vi.fn()}
        />,
      );
      expect(
        screen.getByRole("list", { name: "Focused research pathway" }).querySelectorAll("li"),
      ).toHaveLength(1);
    },
  );
  it("shows offline evidence gaps and never invents a mechanism or report", () => {
    render(
      <UniversalResultsView
        result={{
          ...researchResultFixture,
          mode: "GENERAL_EVIDENCE_SUMMARY",
          interpretation: { ...researchResultFixture.interpretation, depth: "quick" },
          direct_answer: [],
          mechanisms: [],
          evidence: [],
          graph: { ...researchResultFixture.graph, nodes: [], edges: [] },
          saved_locally: false,
          limitations: ["No source records are available in the offline cache."],
          source_runs: [
            { ...researchResultFixture.source_runs[0]!, status: "offline", record_count: 0 },
          ],
        }}
        onDeeper={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText(/Offline mode/)).toBeVisible();
    expect(screen.getByText(/could not retrieve enough evidence/)).toBeVisible();
    expect(screen.queryByRole("button", { name: /Explore mechanism/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Read HTML report" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Read or download report" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Focused pathway" })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /pathway, evidence and uncertainty/ }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("No source records are available in the offline cache.")).toBeVisible();
  });
});
