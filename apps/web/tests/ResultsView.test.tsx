import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ResultsView } from "@/components/ResultsView";
import { investigationFixture } from "@/tests/fixture";

vi.mock("@/components/graph/CausalGraph", () => ({
  CausalGraph: () => <div>Interactive graph test projection</div>,
}));
vi.mock("@/components/simulation/SimulationLab", () => ({
  SimulationLab: () => <div>Curated simulation test panel</div>,
}));
vi.mock("@/components/inference/BayesianLab", () => ({
  BayesianLab: () => <div>Audited HMC test panel</div>,
}));
vi.mock("@/components/peptides/KnownPeptideLab", () => ({
  KnownPeptideLab: () => <div>Known peptide test panel</div>,
}));
vi.mock("@/components/report/ReportPanel", () => ({
  ReportPanel: () => <div>Evidence-linked report test panel</div>,
}));

describe("ResultsView", () => {
  it("keeps unstable ranking visible before mathematical details", () => {
    render(
      <ResultsView
        result={{
          ...investigationFixture,
          ranking_sensitivity: {
            relative_change: 0.2,
            tested_configurations: 18,
            changed_configurations: 2,
            stable: false,
            ranks: [],
            method: "Local sensitivity",
            limitation: "Not calibration",
          },
        }}
      />,
    );
    expect(screen.getByText(/order changes when evidence weights shift modestly/)).toBeVisible();
    expect(screen.queryByText(/tested configurations/)).not.toBeInTheDocument();
  });
  it("starts with mechanism summaries and keeps technical tools out of the beginner view", async () => {
    const user = userEvent.setup();
    render(<ResultsView result={investigationFixture} />);
    expect(screen.getByRole("heading", { name: "Possible mechanisms" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Plasticity pathway" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Uncertainty analysis" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Plausibility index:/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Explore mechanism/ }));
    expect(screen.getByRole("list", { name: "Focused biological pathway" }).children).toHaveLength(
      3,
    );
    await user.click(screen.getByRole("button", { name: /Why this connection: Learning/ }));
    expect(screen.getByRole("region", { name: "Connection evidence" })).toBeVisible();
    expect(screen.getByText("The trigger activates a mediator in this fixture.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "View conflicting evidence" }));
    expect(screen.getByRole("heading", { name: "What argues against this?" })).toBeVisible();
    expect(screen.getAllByText("Direct human mediation is missing.")[0]).toBeVisible();
    expect(screen.getByText("Research intervention class")).toBeVisible();
    expect(screen.getByText("Mechanism-focused")).toBeVisible();
  });

  it("preserves access to every advanced tool and reproducibility", async () => {
    const user = userEvent.setup();
    render(<ResultsView result={investigationFixture} />);
    await user.click(screen.getByRole("button", { name: /Advanced analysis/ }));
    expect(await screen.findByText("Interactive graph test projection")).toBeVisible();
    for (const [name, content] of [
      ["Pathway simulation", "Curated simulation test panel"],
      ["Uncertainty analysis", "Audited HMC test panel"],
      ["Known peptides", "Known peptide test panel"],
    ]) {
      await user.click(screen.getByRole("button", { name }));
      expect(await screen.findByText(content!)).toBeVisible();
    }
    await user.click(screen.getByRole("button", { name: "Scoring & reproducibility" }));
    expect(screen.getByText("investigation-id")).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Research report ↓/ }));
    expect(await screen.findByText("Evidence-linked report test panel")).toBeVisible();
    await user.click(screen.getByRole("button", { name: /Advanced analysis/ }));
    expect(screen.queryByRole("button", { name: "Uncertainty analysis" })).not.toBeInTheDocument();
  });

  it("uses one reference number per source across mechanism summaries and opens its provenance", async () => {
    const original = investigationFixture.graph.evidence[0]!;
    const second = {
      ...original,
      id: "second-source",
      study: { ...original.study, id: "second-study", title: "A distinct tissue study" },
    };
    const hypothesis = investigationFixture.hypotheses[0]!;
    render(
      <ResultsView
        result={{
          ...investigationFixture,
          graph: { ...investigationFixture.graph, evidence: [original, second] },
          hypotheses: [
            hypothesis,
            {
              ...hypothesis,
              id: "second-mechanism",
              title: "Tissue mechanism",
              evidence_ids: [second.id],
            },
          ],
        }}
      />,
    );
    const user = userEvent.setup();
    const source = screen.getByRole("button", { name: "Source 2" });
    await user.click(source);
    const drawer = within(screen.getByRole("dialog", { name: "Reference 2" }));
    expect(drawer.getByRole("link", { name: /A distinct tissue study/ })).toHaveAttribute(
      "href",
      second.study.source_url,
    );
    expect(drawer.getByText(second.evidence_note)).toBeVisible();
    await user.click(drawer.getByText("Study and provenance details"));
    expect(drawer.getByText(second.source_adapter)).toBeVisible();
    await user.click(drawer.getByRole("button", { name: "Close evidence" }));
    expect(source).toHaveFocus();
  });

  it("does not invent evidence or pathways for an empty pack", () => {
    render(<ResultsView result={{ ...investigationFixture, hypotheses: [], petri_model: null }} />);
    expect(screen.getByText(/no complete mechanism path/i)).toBeVisible();
    expect(screen.queryByRole("button", { name: /Explore mechanism/ })).not.toBeInTheDocument();
  });
});
