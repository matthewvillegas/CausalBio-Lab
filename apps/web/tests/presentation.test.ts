import { describe, expect, it } from "vitest";
import { initialGraphNodes, expandGraphNodes } from "@/lib/graph-view";
import {
  evidenceStrength,
  formatDate,
  mechanismRecords,
  representativePath,
} from "@/lib/presentation";
import { investigationFixture } from "@/tests/fixture";

describe("mechanism projections", () => {
  it("selects the best scored path consistently without mutating the scientific result", () => {
    const hypothesis = investigationFixture.hypotheses[0]!;
    const original = hypothesis.mechanism_paths[0]!;
    const alternate = {
      ...original,
      id: "alternate",
      entity_ids: ["entity-mediator", "entity-outcome"],
      assertion_ids: ["assertion-2"],
      score: { ...original.score!, display_index: 90, edge_support_values: [0.7] },
    };
    const family = { ...hypothesis, mechanism_paths: [original, alternate] };
    expect(representativePath(family)?.id).toBe("alternate");
    expect(mechanismRecords(investigationFixture, family).edges.map((edge) => edge.id)).toEqual([
      "assertion-2",
    ]);
    expect(family.mechanism_paths[0]?.id).toBe(original.id);
  });
  it.each([3, 17])(
    "bounds a 17-node connected graph with %i nodes in the representative path",
    (pathLength) => {
      const hypothesis = investigationFixture.hypotheses[0]!;
      const nodeIds = Array.from({ length: 17 }, (_, index) => `entity-${index}`);
      const result = {
        ...investigationFixture,
        hypotheses: [
          {
            ...hypothesis,
            mechanism_paths: [
              {
                ...hypothesis.mechanism_paths[0]!,
                entity_ids: nodeIds.slice(0, pathLength),
              },
            ],
          },
        ],
        graph: {
          ...investigationFixture.graph,
          entities: nodeIds.map((id) => ({ ...investigationFixture.graph.entities[0]!, id })),
          assertions: nodeIds.slice(1).map((id, index) => ({
            ...investigationFixture.graph.assertions[0]!,
            id: `edge-${index}`,
            subject_id: nodeIds[index]!,
            object_id: id,
          })),
        },
      };
      const scope = initialGraphNodes(result);
      expect(scope).toHaveLength(12);
      expect(new Set(scope).size).toBe(12);
      expect(scope).toEqual(nodeIds.slice(0, 12));
    },
  );
  it("expands only in the requested direction", () => {
    expect(expandGraphNodes(investigationFixture, ["entity-mediator"], "upstream")).toEqual([
      "entity-mediator",
      "entity-trigger",
    ]);
    expect(expandGraphNodes(investigationFixture, ["entity-mediator"], "downstream")).toEqual([
      "entity-mediator",
      "entity-outcome",
    ]);
  });
  it("does not turn a strongly graded upstream study into a strong complete mechanism", () => {
    const edges = investigationFixture.graph.assertions.map((edge) => ({
      ...edge,
      confidence_classification: "A" as const,
      contradictory_evidence_ids: [],
    }));
    expect(evidenceStrength(edges)).toBe("Stronger support");
    expect(
      evidenceStrength([
        ...edges,
        { ...edges[0]!, confidence_classification: "U", causal_status: "hypothesis_only" },
      ]),
    ).toBe("Early evidence");
    expect(evidenceStrength([])).toBe("Not assessed");
  });
});

describe("research dates", () => {
  it.each(["", "not-a-date"])("marks an unparseable date as unrecorded: %j", (value) => {
    expect(formatDate(value)).toBe("Date not recorded");
  });
  it("uses the UTC calendar date across offset boundaries", () => {
    expect(formatDate("2026-10-03T23:30:00-05:00")).toBe("October 4, 2026");
    expect(formatDate("2026-10-04T00:30:00+02:00")).toBe("October 3, 2026");
    expect(formatDate("2026-10-03")).toBe("October 3, 2026");
    expect(formatDate("2026-10-03T23:30:12-05:00", true)).toBe("October 4, 2026 at 4:30:12 AM UTC");
  });
});
