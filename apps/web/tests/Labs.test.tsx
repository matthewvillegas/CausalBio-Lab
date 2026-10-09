import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SimulationLab } from "@/components/simulation/SimulationLab";
import { BayesianLab } from "@/components/inference/BayesianLab";
import { KnownPeptideLab } from "@/components/peptides/KnownPeptideLab";
import { analyzeKnownPeptide, compareKnownPeptides, runHMCDemo, simulate } from "@/lib/api";
import type { SimulationRun } from "@/lib/types";
import { investigationFixture } from "@/tests/fixture";
import {
  hmcFixture,
  peptideComparisonFixture,
  peptideFixture,
  simulationFixture,
} from "@/tests/lab-fixtures";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  simulate: vi.fn(),
  runHMCDemo: vi.fn(),
  analyzeKnownPeptide: vi.fn(),
  compareKnownPeptides: vi.fn(),
}));

beforeEach(() => {
  vi.resetAllMocks();
});

describe("Pathway simulation", () => {
  it("uses declared scenarios, keeps the submitted label, and reuses baseline across changes", async () => {
    const user = userEvent.setup();
    vi.mocked(simulate)
      .mockResolvedValueOnce(simulationFixture)
      .mockResolvedValue({ ...simulationFixture, trajectories: { "place-id": [0, 0.17, 0.34] } });
    render(<SimulationLab result={investigationFixture} />);
    expect(screen.queryByRole("option", { name: "Increase feedback" })).not.toBeInTheDocument();
    expect(screen.getByText("Places and initial markings")).not.toBeVisible();
    await user.click(screen.getByRole("button", { name: "Run baseline comparison" }));
    expect(await screen.findByText("Showing: Increase input at 70% strength")).toBeVisible();
    expect(simulate).toHaveBeenNthCalledWith(1, "model-id", "baseline", {}, {});
    expect(simulate).toHaveBeenNthCalledWith(
      2,
      "model-id",
      "increased_activation",
      { "Plasticity input.rate": expect.closeTo(0.17) },
      {},
    );
    expect(screen.getByRole("heading", { name: "What changed?" })).toBeVisible();
    expect(
      screen.getByText(/First sampled differences: Consolidated-state output at model time 1.00/),
    ).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Compare baseline with"), "reduced_input");
    expect(screen.getByText("Showing: Increase input at 70% strength")).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Controls have changed");
    expect(simulate).toHaveBeenCalledTimes(2);
    fireEvent.change(screen.getByRole("slider", { name: "Scenario strength" }), {
      target: { value: "0" },
    });
    await user.click(screen.getByRole("button", { name: "Run baseline comparison" }));
    expect(await screen.findByText("Showing: Reduce input at 0% strength")).toBeVisible();
    expect(simulate).toHaveBeenCalledTimes(3);
    expect(simulate).toHaveBeenLastCalledWith(
      "model-id",
      "reduced_input",
      { "Plasticity input.rate": 0.1 },
      {},
    );
    expect(screen.queryByText(/Controls have changed/)).not.toBeInTheDocument();
    await user.click(screen.getByText("View trajectory values"));
    expect(screen.getByText("0.3400")).toBeVisible();
    await user.click(screen.getByText("View Petri-net model"));
    expect(screen.getByText("Places and initial markings")).toBeVisible();
  });

  it("snapshots settings during execution and clears a failed baseline cache for retry", async () => {
    const user = userEvent.setup();
    let finish!: (value: SimulationRun) => void;
    vi.mocked(simulate)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(simulationFixture);
    render(<SimulationLab result={investigationFixture} />);
    await user.click(screen.getByRole("button", { name: "Run baseline comparison" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Simulation failed");
    vi.mocked(simulate)
      .mockResolvedValueOnce(simulationFixture)
      .mockReturnValueOnce(
        new Promise((resolve) => {
          finish = resolve;
        }),
      );
    await user.click(screen.getByRole("button", { name: "Run baseline comparison" }));
    expect(screen.getByRole("button", { name: "Running model…" })).toBeDisabled();
    await user.selectOptions(screen.getByLabelText("Compare baseline with"), "reduced_input");
    await act(async () => {
      finish(simulationFixture);
    });
    expect(await screen.findByText("Showing: Increase input at 70% strength")).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Controls have changed");
    expect(simulate).toHaveBeenCalledTimes(4);
  });

  it("offers no substitute model when an investigation has no executable model", () => {
    render(<SimulationLab result={{ ...investigationFixture, petri_model: null }} />);
    expect(screen.getByText(/No executable pathway model is curated/)).toBeVisible();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(simulate).not.toHaveBeenCalled();
  });

  it("executes a model without curated scenarios only once for a baseline comparison", async () => {
    const user = userEvent.setup();
    const model = investigationFixture.petri_model!;
    vi.mocked(simulate).mockResolvedValue(simulationFixture);
    render(
      <SimulationLab
        result={{ ...investigationFixture, petri_model: { ...model, scenarios: [] } }}
      />,
    );
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Run baseline comparison" }));
    expect(await screen.findByText("Showing: Baseline")).toBeVisible();
    expect(screen.getByText(/No state differences above/)).toBeVisible();
    expect(simulate).toHaveBeenCalledTimes(1);
  });

  it("changes displayed state without making another scientific request", async () => {
    const user = userEvent.setup();
    const model = investigationFixture.petri_model!;
    const result = {
      ...investigationFixture,
      petri_model: {
        ...model,
        places: [
          ...model.places,
          { ...model.places[0]!, id: "second-place", name: "Another state" },
        ],
      },
    };
    vi.mocked(simulate).mockResolvedValue({
      ...simulationFixture,
      trajectories: { ...simulationFixture.trajectories, "second-place": [0, 1, 2] },
    });
    render(<SimulationLab result={result} />);
    await user.click(screen.getByRole("button", { name: "Run baseline comparison" }));
    await screen.findByText("Showing: Increase input at 70% strength");
    await user.selectOptions(screen.getByLabelText("State to explore"), "second-place");
    expect(screen.getByRole("heading", { name: "Another state" })).toBeVisible();
    expect(simulate).toHaveBeenCalledTimes(2);
    expect(screen.queryByText(/Controls have changed/)).not.toBeInTheDocument();
  });
});

describe("Bayesian uncertainty demonstration", () => {
  it("leads with observations and estimates while keeping diagnostics behind a disclosure", async () => {
    const user = userEvent.setup();
    vi.mocked(runHMCDemo).mockResolvedValue(hmcFixture);
    render(<BayesianLab />);
    expect(screen.getByText(/uses synthetic data and does not estimate biological/)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Run uncertainty demonstration" }));
    expect(
      await screen.findByRole("heading", { name: "Posterior parameter estimates" }),
    ).toBeVisible();
    expect(screen.getByText(/4 generated observations/)).toBeVisible();
    expect(screen.getByText("Rank-normalized R-hat max")).not.toBeVisible();
    await user.click(screen.getByText("Advanced mathematical details"));
    expect(screen.getByText("Rank-normalized R-hat max")).toBeVisible();
    await user.selectOptions(screen.getByRole("combobox", { name: "Parameter" }), "baseline");
    expect(runHMCDemo).toHaveBeenCalledTimes(1);
  });

  it("shows diagnostic warnings before advanced details and never converts missing acceptance to zero", async () => {
    const user = userEvent.setup();
    vi.mocked(runHMCDemo).mockResolvedValue({
      ...hmcFixture,
      state: "DIAGNOSTIC_WARNING",
      diagnostics: {
        ...hmcFixture.diagnostics,
        acceptance_rate: null,
        warnings: ["Chains did not converge."],
      },
    });
    render(<BayesianLab />);
    await user.click(screen.getByRole("button", { name: "Run uncertainty demonstration" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Chains did not converge.");
    expect(screen.queryByText("Sampling checks passed")).not.toBeInTheDocument();
    await user.click(screen.getByText("Advanced mathematical details"));
    expect(screen.getByText("Unavailable")).toBeVisible();
    expect(screen.queryByText("0.0%")).not.toBeInTheDocument();
  });

  it("allows retry after an API failure", async () => {
    const user = userEvent.setup();
    vi.mocked(runHMCDemo).mockRejectedValueOnce(new Error("offline")).mockResolvedValue(hmcFixture);
    render(<BayesianLab />);
    await user.click(screen.getByRole("button", { name: "Run uncertainty demonstration" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("HMC demonstration failed");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(
      await screen.findByRole("heading", { name: "Posterior parameter estimates" }),
    ).toBeVisible();
    expect(runHMCDemo).toHaveBeenCalledTimes(2);
  });
});

describe("Known peptide research", () => {
  beforeEach(() => {
    vi.mocked(analyzeKnownPeptide).mockResolvedValue(peptideFixture);
    vi.mocked(compareKnownPeptides).mockResolvedValue(peptideComparisonFixture);
  });

  it("leads with the published role and target, preserves the submitted record, and reveals calculations on request", async () => {
    const user = userEvent.setup();
    render(<KnownPeptideLab />);
    await user.click(screen.getByRole("button", { name: "Analyze known record" }));
    expect(
      await screen.findByRole("heading", { name: "Biological role and research context" }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "TACR1" })).toHaveAttribute(
      "href",
      "https://www.uniprot.org/uniprotkb/P25103/entry",
    );
    expect(screen.getByText("Approx. molecular weight")).not.toBeVisible();
    expect(analyzeKnownPeptide).toHaveBeenCalledWith("substance-p", 7.4);
    await user.selectOptions(screen.getByLabelText("Known peptide"), "neurokinin-a");
    expect(screen.getByRole("status")).toHaveTextContent("Analyze again");
    expect(screen.getByRole("heading", { name: "Substance P" })).toBeVisible();
    expect(analyzeKnownPeptide).toHaveBeenCalledTimes(1);
    await user.click(screen.getByText("Advanced peptide properties"));
    expect(screen.getByText("Approx. molecular weight")).toBeVisible();
    expect(screen.getByText(/No measured properties are bundled/)).toBeVisible();
    expect(screen.getByText("Estimated charge at pH 7.4")).toBeVisible();
    expect(screen.getByText("β-strand hydrophobic moment")).toBeVisible();
  });

  it("rejects missing or out-of-range pH without a request and marks existing calculations stale", async () => {
    const user = userEvent.setup();
    render(<KnownPeptideLab />);
    await user.click(screen.getByRole("button", { name: "Analyze known record" }));
    await screen.findByRole("heading", { name: "Biological role and research context" });
    await user.click(screen.getByText("Calculation settings"));
    const input = screen.getByLabelText("Charge estimate pH");
    await user.clear(input);
    expect(screen.getByRole("button", { name: "Analyze known record" })).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a pH from 0 to 14.");
    await user.type(input, "15");
    expect(screen.getByRole("button", { name: "Analyze known record" })).toBeDisabled();
    await user.clear(input);
    await user.type(input, "7");
    expect(screen.getByRole("button", { name: "Analyze known record" })).toBeEnabled();
    expect(screen.getByRole("status")).toHaveTextContent("settings have changed");
    expect(analyzeKnownPeptide).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "Analyze known record" }));
    await waitFor(() => expect(analyzeKnownPeptide).toHaveBeenLastCalledWith("substance-p", 7));
  });
});
