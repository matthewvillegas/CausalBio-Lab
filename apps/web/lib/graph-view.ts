import type { InvestigationResult } from "./types";
import { representativePath } from "./presentation";

export function initialGraphNodes(result: InvestigationResult, pathId?: string): string[] {
  const hypothesis = result.hypotheses.find((item) => item.id === pathId) ?? result.hypotheses[0];
  const ids = new Set(
    ((hypothesis ? representativePath(hypothesis)?.entity_ids : []) ?? []).slice(0, 12),
  );
  for (const edge of result.graph.assertions) {
    if (ids.size >= 12) break;
    if (ids.has(edge.subject_id) || ids.has(edge.object_id)) {
      ids.add(edge.subject_id);
      if (ids.size < 12) ids.add(edge.object_id);
    }
  }
  return [...ids];
}

export function expandGraphNodes(
  result: InvestigationResult,
  current: string[],
  direction: "upstream" | "downstream",
): string[] {
  const existing = new Set(current);
  const expanded = new Set(current);
  for (const edge of result.graph.assertions) {
    if (direction === "upstream" && existing.has(edge.object_id)) expanded.add(edge.subject_id);
    if (direction === "downstream" && existing.has(edge.subject_id)) expanded.add(edge.object_id);
  }
  return [...expanded];
}
