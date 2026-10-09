"use client";

import { useState } from "react";
import { AssertionEvidence, EvidenceCard } from "@/components/EvidenceDetails";
import {
  edgeMeaning,
  evidenceContext,
  evidenceStrength,
  humanize,
  mechanismRecords,
  representativePath,
} from "@/lib/presentation";
import type { CausalAssertion, InvestigationResult, MechanisticHypothesis } from "@/lib/types";

export function MechanismDetail({
  result,
  hypothesis,
  onExpand,
  onModel,
}: {
  result: InvestigationResult;
  hypothesis: MechanisticHypothesis;
  onExpand: () => void;
  onModel: () => void;
}) {
  const [nodeId, setNodeId] = useState<string | null>(null);
  const [edgeId, setEdgeId] = useState<string | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [conflictOpen, setConflictOpen] = useState(false);
  const [compareId, setCompareId] = useState("");
  const [highlighted, setHighlighted] = useState<string[]>([]);
  const [expanded, setExpanded] = useState(false);
  const { supporting, conflicting, edges } = mechanismRecords(result, hypothesis);
  const path = representativePath(hypothesis);
  const nodeIds = expanded ? (path?.entity_ids ?? []) : (path?.entity_ids ?? []).slice(0, 12);
  const node = result.graph.entities.find((item) => item.id === nodeId);
  const edge = result.graph.assertions.find((item) => item.id === edgeId);
  const lookup = (id: string) =>
    result.graph.entities.find((item) => item.id === id)?.preferred_name ?? "Unresolved entity";
  const describeEdge = (item?: CausalAssertion) =>
    item ? `${lookup(item.subject_id)} → ${lookup(item.object_id)}` : "Not assessed";
  const rankedEdges = (path?.assertion_ids ?? [])
    .flatMap((id, index) => {
      const assertion = edges.find((item) => item.id === id);
      const support = path?.score?.edge_support_values?.[index];
      return assertion && support !== undefined ? [{ assertion, support }] : [];
    })
    .sort((left, right) => left.support - right.support);
  const weakest = rankedEdges[0]?.assertion;
  const strongest = rankedEdges.at(-1)?.assertion;
  const components = path?.score?.edge_components ?? [];
  const maxExtrapolation = Math.max(0, ...components.map((item) => item.extrapolation_penalty));
  const extrapolationId =
    path?.assertion_ids[
      components.findIndex((item) => item.extrapolation_penalty === maxExtrapolation)
    ];
  const relevantInterventions = result.interventions.filter((item) =>
    hypothesis.intervention_ids.includes(item.id),
  );
  const classes = [...new Set(relevantInterventions.map((item) => item.intervention_class))];
  const comparison = result.hypotheses.find((item) => item.id === compareId);
  function inspectEdge(id: string) {
    setEdgeId(id);
    setNodeId(null);
    requestAnimationFrame(() => {
      const detail = document.getElementById("connection-detail");
      detail?.focus();
      detail?.scrollIntoView({ block: "nearest" });
    });
  }

  return (
    <section className="mechanism-detail" aria-labelledby="mechanism-title">
      <header className="border-b border-[var(--border)] py-5">
        <p className="eyebrow">Mechanism</p>
        <h2 id="mechanism-title" className="mt-2 text-2xl font-bold tracking-tight">
          {hypothesis.title}
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--ink-muted)]">
          {hypothesis.plain_language_summary}
        </p>
      </header>
      <div className="space-y-8 py-5">
        <section>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-lg font-bold">Biological pathway</h3>
            <button className="button-quiet" onClick={onExpand}>
              Explore full evidence map ↗
            </button>
          </div>
          <p className="mt-2 text-xs leading-5 text-[var(--ink-muted)]">
            Follow the path from the first factor to the outcome. Select a step for context or a
            connection for its evidence. Proposed and associative links remain labeled.
          </p>
          {!nodeIds.length && (
            <p className="mt-5">No complete pathway is recorded for this mechanism.</p>
          )}
          <figure className="research-figure">
            <figcaption className="text-sm text-[var(--ink-muted)]">
              Figure 1. Proposed pathway from the curated evidence. Each connection retains its
              evidence status.
            </figcaption>
            <ol className="focused-path mt-5" aria-label="Focused biological pathway">
              {nodeIds.map((id, index) => {
                const connectionId = path?.assertion_ids[index];
                const connection = result.graph.assertions.find((item) => item.id === connectionId);
                return (
                  <li key={`${id}-${index}`} className="path-step">
                    <button
                      className="path-node"
                      data-highlighted={highlighted.includes(id)}
                      aria-expanded={nodeId === id}
                      onClick={() => {
                        setNodeId(nodeId === id ? null : id);
                        setEdgeId(null);
                      }}
                    >
                      <span className="path-number" aria-hidden="true">
                        {index + 1}
                      </span>
                      <span>{lookup(id)}</span>
                    </button>
                    {connection && index < nodeIds.length - 1 && (
                      <button
                        className="path-edge"
                        data-kind={connection.causal_status}
                        onClick={() => inspectEdge(connection.id)}
                        aria-label={`Why this connection: ${lookup(connection.subject_id)} to ${lookup(connection.object_id)}`}
                      >
                        <span aria-hidden="true">
                          {connection.polarity < 0
                            ? "⊣"
                            : connection.causal_status === "hypothesis_only"
                              ? "⇢ ?"
                              : "↓"}
                        </span>
                        <span>
                          {edgeMeaning(connection)}
                          {connection.contradictory_evidence_ids.length
                            ? " · conflicting evidence"
                            : ""}
                        </span>
                      </button>
                    )}
                  </li>
                );
              })}
            </ol>
            <p className="text-sm text-[var(--ink-muted)]">
              Arrow labels distinguish causal support, association, and proposed connections. Select
              a connection to inspect its sources and missing links.
            </p>
          </figure>
          {(path?.entity_ids.length ?? 0) > 12 && !expanded && (
            <button className="button-secondary mt-4" onClick={() => setExpanded(true)}>
              Expand pathway
            </button>
          )}
          {node && (
            <aside className="mt-4 rounded bg-[var(--surface-muted)] p-5" aria-live="polite">
              <h4 className="font-bold">{node.preferred_name}</h4>
              <p className="mt-2 text-sm leading-6">{node.description}</p>
              <p className="mt-2 text-xs text-[var(--ink-muted)]">
                {humanize(node.entity_type)} · {node.aliases.join(", ")}
              </p>
            </aside>
          )}
          <div id="connection-detail" tabIndex={-1} className="mt-4">
            {edge && <AssertionEvidence result={result} assertion={edge} />}
          </div>
        </section>
        <section>
          <h3 className="text-lg font-bold">Why this mechanism matters</h3>
          <p className="mt-3 text-sm leading-6">{hypothesis.plain_language_summary}</p>
          <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
            {hypothesis.context_requirements.join(" ")}
          </p>
        </section>
        <section>
          <h3 className="text-lg font-bold">Evidence</h3>
          <p className="mt-2 text-sm leading-6">{hypothesis.evidence_label}</p>
          <div className="evidence-counts mt-4">
            {["Human", "Animal", "Cellular", "Computational"].map((kind) => {
              const records = supporting.filter((record) => evidenceContext(record) === kind);
              return (
                <div className="border-l border-[var(--border)] pl-4" key={kind}>
                  <p className="text-xs font-bold">{kind} evidence</p>
                  <p className="mt-2 text-sm">
                    {records.length
                      ? `${records.length} source record${records.length === 1 ? "" : "s"}`
                      : "None linked"}
                  </p>
                </div>
              );
            })}
          </div>
          <p className="mt-3 text-xs text-[var(--ink-muted)]">
            Counts describe linked sources, not independent replications. Reviews may summarize
            several species or study designs; inspect their notes.
          </p>
          <button
            className="button-secondary mt-4"
            aria-expanded={evidenceOpen}
            onClick={() => setEvidenceOpen(!evidenceOpen)}
          >
            View supporting evidence
          </button>
          {evidenceOpen && (
            <div className="mt-4 space-y-3">
              {supporting.length ? (
                supporting.map((record) => <EvidenceCard key={record.id} record={record} />)
              ) : (
                <p>No supporting source is recorded.</p>
              )}
            </div>
          )}
        </section>
        <section className="limitation-section">
          <h3 className="text-lg font-bold">What argues against this?</h3>
          <ul className="mt-3 space-y-2 text-sm leading-6">
            {[...hypothesis.uncertainty, ...hypothesis.missing_links].map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="mt-3 text-sm">
            {conflicting.length
              ? `${conflicting.length} conflicting or limiting source record(s) are linked.`
              : "No conflicting study is linked in this small pack. Absence here does not mean the mechanism is established."}
          </p>
          <button
            className="button-secondary mt-4"
            aria-expanded={conflictOpen}
            onClick={() => setConflictOpen(!conflictOpen)}
          >
            View conflicting evidence
          </button>
          {conflictOpen && (
            <div className="mt-4 space-y-3">
              {conflicting.map((record) => (
                <EvidenceCard key={record.id} record={record} />
              ))}
              {!conflicting.length && (
                <p className="text-sm">
                  Review the missing links and competing mechanisms above; a broader literature
                  search is still needed.
                </p>
              )}
            </div>
          )}
        </section>
        <section>
          <h3 className="text-lg font-bold">Where the argument is strongest and weakest</h3>
          <dl className="metadata mt-4">
            <dt>Strongest-supported edge</dt>
            <dd>{describeEdge(strongest)} (under the recorded evidence rubric)</dd>
            <dt>Weakest-supported edge</dt>
            <dd>{describeEdge(weakest)}</dd>
            <dt>Largest extrapolation</dt>
            <dd>
              {maxExtrapolation > 0
                ? describeEdge(edges.find((item) => item.id === extrapolationId))
                : "No extrapolation penalty recorded; this does not establish generalizability."}
            </dd>
            <dt>Uncertain assumption</dt>
            <dd>{hypothesis.missing_links[0] ?? hypothesis.uncertainty[0] ?? "Not assessed"}</dd>
          </dl>
        </section>
        <section>
          <h3 className="text-lg font-bold">Relevant intervention research</h3>
          <p className="mt-2 text-sm text-[var(--ink-muted)]">
            Research objects for understanding this pathway. These are not personal recommendations.
          </p>
          {!classes.length && (
            <p className="mt-4 text-sm">No intervention research is linked to this mechanism.</p>
          )}
          {classes.map((group) => (
            <div key={group} className="mt-5">
              <h4 className="text-sm font-bold">{humanize(group)}</h4>
              <div className="mt-3 space-y-3">
                {relevantInterventions
                  .filter((item) => item.intervention_class === group)
                  .map((item) => (
                    <article className="border-t border-[var(--border)] py-5" key={item.id}>
                      <span className="badge">
                        {item.addresses === "symptom"
                          ? "Symptom-focused"
                          : item.addresses === "multiple"
                            ? "Mechanism- and symptom-focused"
                            : "Mechanism-focused"}
                      </span>
                      <h5 className="mt-3 font-bold">{item.name}</h5>
                      <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
                        {item.description}
                      </p>
                      <dl className="metadata mt-4">
                        <dt>Targets / pathway position</dt>
                        <dd>{item.target_entity_ids.map(lookup).join(", ") || "Not mapped"}</dd>
                        <dt>Evidence maturity</dt>
                        <dd>{item.maturity}</dd>
                        <dt>Human relevance</dt>
                        <dd>
                          {[
                            ...new Set(
                              result.graph.evidence
                                .filter((record) => item.evidence_ids.includes(record.id))
                                .map(evidenceContext),
                            ),
                          ].join(", ") || "No source context recorded"}
                          . Study context does not establish an individual benefit.
                        </dd>
                        <dt>Directness</dt>
                        <dd>
                          {item.downstream_assertion_ids.length} linked downstream connection(s);{" "}
                          {item.unsupported_assumptions[0] ??
                            "Read the source contexts to assess the path to the outcome."}
                        </dd>
                        <dt>Main uncertainty</dt>
                        <dd>{item.uncertainty[0] ?? "Not recorded"}</dd>
                      </dl>
                      <details className="mt-3">
                        <summary className="disclosure">Why is this relevant?</summary>
                        <p className="mt-3 text-sm leading-6">
                          This intervention is linked to this mechanism in the curated pack and
                          targets {item.target_entity_ids.map(lookup).join(", ")}.{" "}
                          {item.evidence_ids.length} source record(s) are attached.{" "}
                          {item.unsupported_assumptions.join(" ")}
                        </p>
                        {result.graph.evidence
                          .filter((record) => item.evidence_ids.includes(record.id))
                          .map((record) => (
                            <a
                              className="source-link mt-2 block text-xs"
                              href={record.study.source_url}
                              key={record.id}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {record.study.title} ↗
                            </a>
                          ))}
                        <p className="mt-3 text-xs text-[var(--amber)]">
                          {item.major_safety_concerns.join(" ")}
                        </p>
                      </details>
                      <button
                        className="button-secondary mt-4"
                        onClick={() => {
                          setHighlighted(item.target_entity_ids);
                          document
                            .getElementById("mechanism-title")
                            ?.scrollIntoView({ block: "start" });
                        }}
                      >
                        Show pathway
                      </button>
                      {highlighted.some((id) => item.target_entity_ids.includes(id)) && (
                        <p className="mt-2 text-xs">
                          Targets are outlined in the focused pathway where present. Other targets
                          appear in the full map.
                        </p>
                      )}
                    </article>
                  ))}
              </div>
            </div>
          ))}
        </section>
        {result.hypotheses.length > 1 && (
          <section>
            <label className="block max-w-xl">
              <span className="mb-2 block text-lg font-bold">Compare another mechanism</span>
              <select
                className="field"
                value={compareId}
                onChange={(event) => setCompareId(event.target.value)}
              >
                <option value="">Choose a mechanism</option>
                {result.hypotheses
                  .filter((item) => item.id !== hypothesis.id)
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.title}
                    </option>
                  ))}
              </select>
            </label>
            {comparison && (
              <div className="mt-4 overflow-x-auto">
                <table className="scientific-table">
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th>{hypothesis.title}</th>
                      <th>{comparison.title}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      "Evidence context",
                      "Human sources",
                      "Path length",
                      "Counterevidence",
                      "Weakest connection",
                      "Missing link",
                      "Overall support",
                    ].map((label, index) => (
                      <tr key={label}>
                        <th>{label}</th>
                        {[hypothesis, comparison].map((item) => {
                          const profile = mechanismRecords(result, item);
                          const comparedPath = representativePath(item);
                          const support = comparedPath?.score?.edge_support_values ?? [];
                          const weakId = support.length
                            ? comparedPath?.assertion_ids[support.indexOf(Math.min(...support))]
                            : undefined;
                          const values = [
                            item.evidence_label,
                            profile.supporting.filter(
                              (record) => evidenceContext(record) === "Human",
                            ).length,
                            `${representativePath(item)?.assertion_ids.length ?? 0} connections`,
                            `${profile.conflicting.length} linked sources`,
                            describeEdge(profile.edges.find((edge) => edge.id === weakId)),
                            item.missing_links[0] ?? "Not assessed",
                            evidenceStrength(profile.edges),
                          ];
                          return <td key={item.id}>{values[index]}</td>;
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
        <div className="rounded bg-[var(--surface-muted)] p-5">
          <h3 className="font-bold">Explore how a model changes over time</h3>
          <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
            {result.petri_model
              ? "This evidence pack includes an educational pathway model. Its assumptions and scope may cover only part of this mechanism; it does not automatically simulate the selected path."
              : "This mechanism does not yet have an executable pathway model."}
          </p>
          <button className="button-secondary mt-4" onClick={onModel}>
            Model pathway
          </button>
        </div>
      </div>
    </section>
  );
}
