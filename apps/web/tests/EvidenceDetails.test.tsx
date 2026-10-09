import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { EvidenceCard } from "@/components/EvidenceDetails";
import type { EvidenceRecord } from "@/lib/types";
import { investigationFixture } from "@/tests/fixture";

describe("EvidenceCard", () => {
  it("keeps uncertainty visible and includes the recorded interval beside an estimate", async () => {
    const record: EvidenceRecord = {
      ...investigationFixture.graph.evidence[0]!,
      uncertainty_measure: "The secondary outcome was not statistically significant.",
      effect_estimate: {
        measure: "Between-group difference",
        value: 9,
        unit: "points",
        interval_low: 0,
        interval_high: 16,
        interval_level: 0.95,
        source_note: "Measured at the recorded follow-up.",
      },
    };
    render(<EvidenceCard record={record} />);
    expect(
      screen.getByText(/The secondary outcome was not statistically significant/),
    ).toBeVisible();
    await userEvent.setup().click(screen.getByText("Study and provenance details"));
    expect(screen.getByText(/95% interval: 0–16/)).toBeVisible();
    expect(screen.getByText(/Between-group difference: 9 points/)).toBeVisible();
  });

  it("does not invent an interval or effect for an evidence record without either", async () => {
    render(<EvidenceCard record={investigationFixture.graph.evidence[0]!} />);
    await userEvent.setup().click(screen.getByText("Study and provenance details"));
    expect(screen.getByText(/Fixture uncertainty/)).toBeVisible();
    expect(screen.queryByText(/interval:/i)).not.toBeInTheDocument();
  });
});
