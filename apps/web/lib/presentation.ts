import type {
  CausalAssertion,
  EvidenceRecord,
  InvestigationResult,
  MechanisticHypothesis,
} from "./types";

export function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatDate(value: string, includeTime = false): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date not recorded"
    : date.toLocaleString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
        timeZone: "UTC",
        ...(includeTime
          ? ({
              hour: "numeric",
              minute: "2-digit",
              second: "2-digit",
              timeZoneName: "short",
            } as const)
          : {}),
      });
}

export function representativePath(hypothesis: MechanisticHypothesis) {
  return [...hypothesis.mechanism_paths].sort(
    (left, right) => (right.score?.display_index ?? -1) - (left.score?.display_index ?? -1),
  )[0];
}

export function mechanismRecords(result: InvestigationResult, hypothesis: MechanisticHypothesis) {
  const ids = new Set(hypothesis.evidence_ids);
  const edgeIds = new Set(representativePath(hypothesis)?.assertion_ids ?? []);
  const edges = result.graph.assertions.filter((edge) => edgeIds.has(edge.id));
  edges.forEach((edge) => edge.supporting_evidence_ids.forEach((id) => ids.add(id)));
  const counterIds = new Set([
    ...hypothesis.contradictory_evidence_ids,
    ...edges.flatMap((edge) => edge.contradictory_evidence_ids),
  ]);
  return {
    supporting: result.graph.evidence.filter((record) => ids.has(record.id)),
    conflicting: result.graph.evidence.filter((record) => counterIds.has(record.id)),
    edges,
  };
}

// Qualitative labels summarize the weakest edge in a complete path, not clinical certainty.
export function evidenceStrength(edges: CausalAssertion[]): string {
  if (!edges.length) return "Not assessed";
  if (
    edges.some(
      (edge) =>
        ["E", "U"].includes(edge.confidence_classification) ||
        edge.causal_status === "hypothesis_only",
    )
  )
    return "Early evidence";
  if (edges.some((edge) => edge.contradictory_evidence_ids.length)) return "Mixed evidence";
  if (edges.every((edge) => ["A", "B"].includes(edge.confidence_classification)))
    return "Stronger support";
  return "Limited support";
}

export function evidenceContext(record: EvidenceRecord): string {
  const species = record.experimental_context.species.toLowerCase();
  const design = record.study.study_type.toLowerCase();
  if (/computational|simulation|in_silico/.test(design)) return "Computational";
  if (/cell|in_vitro/.test(design)) return "Cellular";
  if (/human|homo sapiens/.test(species)) return "Human";
  if (/rat|mouse|mice|rabbit|animal|rodent/.test(species)) return "Animal";
  return "Other / unspecified";
}

export function edgeMeaning(edge: CausalAssertion): string {
  if (edge.causal_status === "hypothesis_only") return "Proposed connection";
  if (edge.causal_status === "computational_prediction") return "Model prediction";
  if (edge.causal_status.includes("association")) return "Association";
  if (edge.polarity === -1) return "Inhibitory connection";
  if (edge.causal_status === "expert_curation") return "Curated interpretation";
  return "Experimental / mechanistic connection";
}
