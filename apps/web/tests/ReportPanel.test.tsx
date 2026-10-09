import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReportPanel } from "@/components/report/ReportPanel";
import { generateReport } from "@/lib/api";
import type { ReportResponse } from "@/lib/types";
import { investigationFixture } from "@/tests/fixture";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  generateReport: vi.fn(),
}));

const report: ReportResponse = {
  report_id: "report-one",
  citation_coverage: 1,
  artifacts: [
    {
      filename: "report.html",
      format: "HTML",
      media_type: "text/html",
      download_url: "/report.html",
    },
    {
      filename: "report.md",
      format: "Markdown",
      media_type: "text/markdown",
      download_url: "/report.md",
    },
    {
      filename: "graph.graphml",
      format: "GraphML",
      media_type: "application/graphml+xml",
      download_url: "/graph.graphml",
    },
  ],
};

beforeEach(() => {
  vi.mocked(generateReport).mockReset();
});

describe("ReportPanel", () => {
  it("leads with the readable summary and retains downloads across remounts", async () => {
    const user = userEvent.setup();
    const result = { ...investigationFixture, id: "report-remount" };
    vi.mocked(generateReport).mockResolvedValue(report);
    const view = render(<ReportPanel result={result} />);
    expect(screen.getByRole("heading", { name: "Research summary" })).toBeVisible();
    expect(screen.getByText("Random seed")).not.toBeVisible();
    await user.click(screen.getByRole("button", { name: "Generate research report" }));
    expect(await screen.findByRole("link", { name: "Read HTML report" })).toBeVisible();
    expect(screen.getByText("GraphML ↓")).not.toBeVisible();
    expect(screen.getByText("Source-link coverage: 100%")).not.toBeVisible();
    view.unmount();
    render(<ReportPanel result={result} />);
    expect(screen.getByRole("link", { name: "Read HTML report" })).toBeVisible();
    expect(generateReport).toHaveBeenCalledTimes(1);
    await user.click(screen.getByText("Reproducibility and data exports"));
    expect(screen.getByRole("link", { name: "GraphML ↓" })).toBeVisible();
  });

  it("rejoins an in-flight report without recomputing it", async () => {
    const user = userEvent.setup();
    const result = { ...investigationFixture, id: "report-pending" };
    let complete!: (value: ReportResponse) => void;
    vi.mocked(generateReport).mockReturnValue(
      new Promise((resolve) => {
        complete = resolve;
      }),
    );
    const first = render(<ReportPanel result={result} />);
    await user.click(screen.getByRole("button", { name: "Generate research report" }));
    first.unmount();
    render(<ReportPanel result={result} />);
    expect(screen.getByRole("status")).toHaveTextContent("Preparing your summary");
    await act(async () => {
      complete(report);
    });
    expect(await screen.findByRole("link", { name: "Read HTML report" })).toBeVisible();
    expect(generateReport).toHaveBeenCalledTimes(1);
  });

  it("keeps failures retryable and resets the report for another investigation", async () => {
    const user = userEvent.setup();
    vi.mocked(generateReport).mockRejectedValueOnce(new Error("offline")).mockResolvedValue(report);
    const view = render(<ReportPanel result={{ ...investigationFixture, id: "report-retry" }} />);
    await user.click(screen.getByRole("button", { name: "Generate research report" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Your investigation remains available",
    );
    await user.click(screen.getByRole("button", { name: "Retry report" }));
    await waitFor(() =>
      expect(screen.getByRole("link", { name: "Read HTML report" })).toBeVisible(),
    );
    view.rerender(
      <ReportPanel
        result={{ ...investigationFixture, id: "another-investigation", petri_model: null }}
      />,
    );
    expect(screen.getByRole("button", { name: "Generate research report" })).toBeVisible();
    expect(screen.queryByRole("link", { name: "Read HTML report" })).not.toBeInTheDocument();
    await user.click(screen.getByText("Reproducibility and data exports"));
    expect(screen.getByText(/no executable pathway model to export/)).toBeVisible();
    expect(generateReport).toHaveBeenCalledTimes(2);
  });
});
