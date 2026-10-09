"use client";

import dynamic from "next/dynamic";
import { useRef, useState } from "react";
import { EvidenceDrawer } from "@/components/EvidenceDrawer";
import { EvidenceCard } from "@/components/EvidenceDetails";
import { MechanismDetail } from "@/components/MechanismDetail";
import { evidenceStrength, mechanismRecords } from "@/lib/presentation";
import type { InvestigationResult } from "@/lib/types";

const loading = () => (
  <p role="status" className="p-5">
    Opening analysis tools…
  </p>
);
const CausalGraph = dynamic(
  () => import("@/components/graph/CausalGraph").then((m) => m.CausalGraph),
  { ssr: false, loading },
);
const SimulationLab = dynamic(
  () => import("@/components/simulation/SimulationLab").then((m) => m.SimulationLab),
  { ssr: false, loading },
);
const BayesianLab = dynamic(
  () => import("@/components/inference/BayesianLab").then((m) => m.BayesianLab),
  { ssr: false, loading },
);
const KnownPeptideLab = dynamic(
  () => import("@/components/peptides/KnownPeptideLab").then((m) => m.KnownPeptideLab),
  { ssr: false, loading },
);
const ReportPanel = dynamic(
  () => import("@/components/report/ReportPanel").then((m) => m.ReportPanel),
  { loading },
);

const TOOLS = [
  ["graph", "Full causal graph"],
  ["evidence", "Raw evidence"],
  ["simulation", "Pathway simulation"],
  ["bayesian", "Uncertainty analysis"],
  ["peptides", "Known peptides"],
  ["methods", "Scoring & reproducibility"],
] as const;
type Tool = (typeof TOOLS)[number][0];

export function ResultsView({ result }: { result: InvestigationResult }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [tool, setTool] = useState<Tool>("graph");
  const [visited, setVisited] = useState<Tool[]>([]);
  const [reportOpen, setReportOpen] = useState(false);
  const [citationId, setCitationId] = useState<string | null>(null);
  const citation = result.graph.evidence.find((record) => record.id === citationId);
  const sourceNumbers = new Map(
    result.graph.evidence.map((record, index) => [record.id, index + 1]),
  );
  const detailRef = useRef<HTMLDivElement>(null);
  const advancedRef = useRef<HTMLElement>(null);
  const selected = result.hypotheses.find((item) => item.id === selectedId);

  function explore(id: string) {
    setSelectedId(id);
    requestAnimationFrame(() => {
      detailRef.current?.focus();
      detailRef.current?.scrollIntoView({ block: "start" });
    });
  }
  function openTool(next: Tool) {
    setAdvancedOpen(true);
    setTool(next);
    setVisited((current) => (current.includes(next) ? current : [...current, next]));
    requestAnimationFrame(() => {
      advancedRef.current?.scrollIntoView({ block: "start" });
    });
  }

  return (
    <div className="research-brief curated-brief">
      <div className="brief-header flex flex-wrap items-center justify-between gap-4">
        <div className="max-w-3xl">
          <p className="eyebrow">Curated investigation</p>
          <h1 className="mt-3 text-2xl font-bold leading-tight tracking-tight sm:text-3xl">
            {result.question.original_text}
          </h1>
          <p className="mt-3 text-sm text-[var(--ink-muted)]">
            This topic has a reviewed CausalBio evidence pack. Outcome:{" "}
            {result.question.context.requested_outcome}
          </p>
        </div>
        <button
          className="button-secondary"
          onClick={() => {
            setReportOpen(true);
            requestAnimationFrame(() =>
              document.getElementById("research-report")?.scrollIntoView({ block: "start" }),
            );
          }}
        >
          Research report ↓
        </button>
      </div>
      <section className="prose-section" aria-labelledby="curated-overview">
        <h2 id="curated-overview" className="mt-2 text-2xl font-bold">
          Research summary
        </h2>
        {result.hypotheses.slice(0, 2).map((hypothesis) => (
          <p key={hypothesis.id} className="mt-4 text-sm leading-7">
            {hypothesis.plain_language_summary}{" "}
            <sup className="source-citations">
              {result.graph.evidence
                .filter((record) => hypothesis.evidence_ids.includes(record.id))
                .slice(0, 3)
                .map((record) => (
                  <button
                    key={record.id}
                    className="citation"
                    aria-label={`Source ${sourceNumbers.get(record.id)}`}
                    onClick={() => setCitationId(record.id)}
                  >
                    {sourceNumbers.get(record.id)}
                  </button>
                ))}
            </sup>
          </p>
        ))}
        <p className="mt-3 text-xs leading-6 text-[var(--ink-muted)]">
          These are possible mechanisms, not diagnoses or predictions for an individual. Explore
          each explanation to inspect its missing links and conflicting evidence.
        </p>
        <a href="#mechanisms-title" className="button-secondary mt-4">
          Explore mechanisms ↓
        </a>
      </section>
      <section className="prose-section" aria-labelledby="mechanisms-title">
        <h2 id="mechanisms-title" className="mt-2 text-2xl font-bold tracking-tight">
          Possible mechanisms
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--ink-muted)]">
          {result.hypotheses.length
            ? `We found ${result.hypotheses.length} plausible mechanism families in the curated evidence. More than one may contribute. Choose one to see how the pieces connect.`
            : "This evidence pack has no complete mechanism path. Review the available evidence or try another question."}
        </p>
        <p className="mt-2 text-xs leading-5 text-[var(--ink-muted)]">
          Ordered by evidence quality, context, and missing or conflicting links. A higher position
          does not establish a mechanism or predict an individual outcome.
        </p>
        {result.ranking_sensitivity && !result.ranking_sensitivity.stable && (
          <p className="section-note mt-3 text-[var(--amber)]">
            The order changes when evidence weights shift modestly. Compare the mechanisms and their
            weak links; their exact positions are sensitive to the ranking policy.
          </p>
        )}
        <div className="mechanism-list">
          {result.hypotheses.map((hypothesis, index) => {
            const { edges } = mechanismRecords(result, hypothesis);
            return (
              <article
                key={hypothesis.id}
                className="mechanism-row"
                data-selected={selectedId === hypothesis.id}
              >
                <span className="mechanism-number">0{index + 1}</span>
                <div className="mechanism-content">
                  <h3>{hypothesis.title}</h3>
                  <p className="mt-1 text-sm text-[var(--amber)]">{evidenceStrength(edges)}</p>
                  <p className="mt-3 text-sm leading-6 text-[var(--ink-muted)]">
                    {hypothesis.plain_language_summary}
                  </p>
                  <p className="mt-4 text-xs leading-5">
                    <strong>Evidence context:</strong> {hypothesis.evidence_label}
                  </p>
                  <p className="mt-3 text-xs leading-5 text-[var(--ink-muted)]">
                    <strong className="text-[var(--ink)]">Main uncertainty:</strong>{" "}
                    {hypothesis.uncertainty[0] ?? "No uncertainty assessment recorded."}
                  </p>

                  <button className="text-link mt-4" onClick={() => explore(hypothesis.id)}>
                    Explore mechanism<span className="sr-only">: {hypothesis.title}</span>
                    <span aria-hidden="true">→</span>
                  </button>
                  <details className="mt-3 text-xs leading-5">
                    <summary className="disclosure">Why is this ranked here?</summary>
                    <p className="mt-3 text-xs leading-5 text-[var(--ink-muted)]">
                      <strong className="text-[var(--ink)]">Relevance:</strong> path to{" "}
                      {result.graph.entities.find((entity) => entity.id === hypothesis.outcome_id)
                        ?.preferred_name ?? result.question.context.requested_outcome}
                      . {hypothesis.context_requirements[0]}
                    </p>
                    <p className="mt-3">
                      {edges.length} pathway connections; {new Set(hypothesis.evidence_ids).size}{" "}
                      linked source records;{" "}
                      {edges.filter((edge) => edge.contradictory_evidence_ids.length).length}{" "}
                      connections have counterevidence.{" "}
                      {hypothesis.missing_links[0] ?? "No missing-link assessment is recorded."}
                    </p>
                    <p className="mt-2">
                      {hypothesis.evidence_label}. The complete-path evidence label follows the
                      weakest connection; study counts do not prove independent replication. Inspect
                      Scoring &amp; reproducibility for the weighted calculation.
                    </p>
                  </details>
                </div>
              </article>
            );
          })}
        </div>
      </section>
      <div
        ref={detailRef}
        tabIndex={-1}
        className="scroll-mt-6 mt-10"
        aria-label="Selected mechanism"
      >
        {selected ? (
          <MechanismDetail
            key={selected.id}
            result={result}
            hypothesis={selected}
            onExpand={() => openTool("graph")}
            onModel={() => openTool("simulation")}
          />
        ) : (
          <p className="section-note py-5">Select a mechanism to explore its biological pathway.</p>
        )}
      </div>
      <section className="prose-section" aria-labelledby="curated-references">
        <h2 id="curated-references">References</h2>
        <ol className="reference-list">
          {result.graph.evidence.map((record, index) => (
            <li className="reference-entry flex gap-3" key={record.id}>
              <span className="text-sm text-[var(--ink-muted)]">{index + 1}.</span>
              <div>
                <button className="text-link text-left" onClick={() => setCitationId(record.id)}>
                  {record.study.title}
                </button>
                <p className="text-sm text-[var(--ink-muted)]">
                  {record.study.authors.join(", ")} · {record.study.journal},{" "}
                  {record.study.publication_year}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </section>
      <section ref={advancedRef} className="analysis-workbench scroll-mt-6 mt-8">
        <button
          className="flex w-full items-center justify-between gap-4 p-5 text-left"
          aria-expanded={advancedOpen}
          aria-controls="advanced-analysis"
          onClick={() => {
            setAdvancedOpen(!advancedOpen);
            if (!visited.length) setVisited([tool]);
          }}
        >
          <span>
            <span className="block font-bold">Advanced analysis</span>
            <span className="mt-1 block text-xs text-[var(--ink-muted)]">
              Inspect the full evidence map, model selected pathways, or explore mathematical
              uncertainty.
            </span>
          </span>
          <span aria-hidden="true">{advancedOpen ? "−" : "+"}</span>
        </button>
        <div
          id="advanced-analysis"
          hidden={!advancedOpen}
          className="border-t border-[var(--border)] py-5"
        >
          <nav className="analysis-navigation" aria-label="Advanced tools">
            {TOOLS.map(([id, label]) => (
              <button
                className="button-quiet"
                key={id}
                aria-pressed={tool === id}
                onClick={() => openTool(id)}
              >
                {label}
              </button>
            ))}
          </nav>
          {visited.map((id) => (
            <div key={id} hidden={tool !== id}>
              {id === "graph" && (
                <CausalGraph
                  key={selectedId ?? "default"}
                  result={result}
                  initialHypothesisId={selectedId ?? undefined}
                />
              )}
              {id === "evidence" && (
                <section className="space-y-4">
                  <h2 className="text-xl font-bold">Evidence records</h2>
                  <p className="text-sm text-[var(--ink-muted)]">
                    {result.graph.evidence.length} curated source records. Review status describes
                    this pack’s workflow, not independent scientific validation.
                  </p>
                  {result.graph.evidence.map((record) => (
                    <EvidenceCard key={record.id} record={record} />
                  ))}
                </section>
              )}
              {id === "simulation" && <SimulationLab result={result} />}
              {id === "bayesian" && (
                <>
                  <aside className="section-note mb-6 text-[var(--amber)]">
                    <strong>For this investigation:</strong>{" "}
                    {result.inference_eligibility.explanation} The teaching demonstration below is
                    separate from your biological question.
                  </aside>
                  <BayesianLab />
                </>
              )}
              {id === "peptides" && <KnownPeptideLab />}
              {id === "methods" && (
                <section className="space-y-4">
                  <h2 className="text-xl font-bold">Scoring &amp; reproducibility</h2>
                  {result.ranking_sensitivity && (
                    <details className="border-t border-[var(--border)] py-4">
                      <summary className="disclosure">How sensitive is the ranking?</summary>
                      <p className="mt-3 text-sm leading-6">
                        Changing each weight by ±{result.ranking_sensitivity.relative_change * 100}%
                        changed ranks in {result.ranking_sensitivity.changed_configurations} of{" "}
                        {result.ranking_sensitivity.tested_configurations} tested configurations.{" "}
                        {result.ranking_sensitivity.method} {result.ranking_sensitivity.limitation}
                      </p>
                      <ul className="mt-3 space-y-2 text-sm">
                        {result.ranking_sensitivity.ranks.map((rank) => (
                          <li key={rank.hypothesis_id}>
                            {
                              result.hypotheses.find((item) => item.id === rank.hypothesis_id)
                                ?.title
                            }
                            : rank {rank.best_rank}–{rank.worst_rank} (default {rank.baseline_rank})
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                  <p className="text-sm">
                    The plausibility index is a comparison heuristic, not a probability. Evidence
                    labels describe complete paths; a strong individual study does not establish
                    every downstream connection.
                  </p>
                  {result.hypotheses.map((hypothesis) => (
                    <details className="border-t border-[var(--border)] py-4" key={hypothesis.id}>
                      <summary className="disclosure">{hypothesis.title}</summary>
                      {hypothesis.mechanism_paths.map((path) => (
                        <div key={path.id} className="mt-4">
                          <p>
                            Plausibility index:{" "}
                            {path.score?.display_index.toFixed(1) ?? "Unavailable"} / 100
                          </p>
                          <ul className="mt-3 text-xs leading-6">
                            {path.score?.explanation.map((line) => (
                              <li key={line}>{line}</li>
                            ))}
                          </ul>
                          <pre className="raw-data mt-3">{JSON.stringify(path, null, 2)}</pre>
                        </div>
                      ))}
                    </details>
                  ))}
                  <dl className="metadata">
                    <dt>Investigation</dt>
                    <dd>{result.id}</dd>
                    <dt>Software</dt>
                    <dd>{result.software_version}</dd>
                    <dt>Graph</dt>
                    <dd>{result.graph_version}</dd>
                    <dt>Evidence rubric</dt>
                    <dd>{result.evidence_rubric_version}</dd>
                    <dt>Seed</dt>
                    <dd>{result.random_seed}</dd>
                    <dt>Completed</dt>
                    <dd>{result.completed_at}</dd>
                  </dl>
                  <details>
                    <summary className="disclosure">Raw investigation JSON</summary>
                    <pre className="raw-data mt-3">{JSON.stringify(result, null, 2)}</pre>
                  </details>
                </section>
              )}
            </div>
          ))}
        </div>
      </section>
      <section id="research-report" className="report-section scroll-mt-6 mt-6 py-5">
        <button
          className="flex w-full items-center justify-between text-left font-bold"
          aria-expanded={reportOpen}
          aria-controls="report-content"
          onClick={() => setReportOpen(!reportOpen)}
        >
          Research report <span aria-hidden="true">{reportOpen ? "−" : "+"}</span>
        </button>
        <div id="report-content" hidden={!reportOpen} className="pt-5">
          {reportOpen && <ReportPanel result={result} />}
        </div>
      </section>
      {citation && (
        <EvidenceDrawer
          title={`Reference ${sourceNumbers.get(citation.id)}`}
          onClose={() => setCitationId(null)}
        >
          <p className="section-note mb-4">
            Curated evidence cited for the mechanism summaries in this investigation. Its context
            and limitations remain part of the explanation.
          </p>
          <EvidenceCard record={citation} />
        </EvidenceDrawer>
      )}
      <p className="mt-6 text-xs leading-5 text-[var(--ink-muted)]">
        {result.safety_notice.message} Curated examples are educational and incomplete.
      </p>
    </div>
  );
}
