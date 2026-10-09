"use client";

import { useRef, useState } from "react";
import { API_URL } from "@/lib/api";
import { formatDate, humanize } from "@/lib/presentation";
import { EvidenceDrawer } from "./EvidenceDrawer";
import type {
  ResearchClaim,
  ResearchEvidence,
  UniversalResearchResult,
} from "@/lib/research-types";

export function UniversalResultsView({
  result,
  onDeeper,
  onRetry,
}: {
  result: UniversalResearchResult;
  onDeeper: () => void;
  onRetry: () => void;
}) {
  const [selectedId, setSelectedId] = useState(result.mechanisms[0]?.id ?? "");
  const [expanded, setExpanded] = useState(result.interpretation.depth !== "quick");
  const [advanced, setAdvanced] = useState(result.interpretation.depth === "deep");
  const [citation, setCitation] = useState<{ id: string; claim?: ResearchClaim } | null>(null);
  const focusRef = useRef<HTMLElement>(null);
  const selected = result.mechanisms.find((item) => item.id === selectedId);
  const focusedEdges = result.graph.edges
    .filter((edge) => !selected || edge.subject_id === selected.id)
    .slice(0, 12);
  const hasEvidenceDetail = result.evidence.length > 0 || result.mechanisms.length > 0;
  const hasFocusedPathway = focusedEdges.length > 0 || !!selected?.claims.length;
  const sourceNumbers = new Map(result.evidence.map((record, index) => [record.id, index + 1]));
  const cached = result.evidence.some(
    (record) => record.cache_status === "fresh_cache" || record.cache_status === "stale_cache",
  );
  const offline =
    result.source_runs.some((run) => run.status === "offline") &&
    result.source_runs.every((run) => run.status === "offline" || run.status === "cached");
  const unavailable = result.source_runs.filter((run) => run.status === "unavailable").length;
  const citationRecord = result.evidence.find((record) => record.id === citation?.id);
  const citationClaims = citation?.claim
    ? [citation.claim]
    : [
        ...new Map(
          [
            ...result.direct_answer,
            ...result.mechanisms.flatMap((mechanism) => mechanism.claims),
            ...result.complications,
            ...result.modifiers,
          ]
            .filter((item) => item.evidence_ids.includes(citation?.id ?? ""))
            .map((item) => [item.id, item]),
        ).values(),
      ];
  const contexts = result.evidence.reduce<Record<string, number>>((counts, record) => {
    const context = `${record.organism ?? ""} ${record.study_type ?? ""} ${record.experimental_context ?? ""}`;
    const group = /uniprot/i.test(record.source)
      ? "Database annotation"
      : /computational|in silico/i.test(context)
        ? "Computational"
        : /cell culture|in vitro|cellular/i.test(context)
          ? "Cellular"
          : /^(?:human|homo sapiens)$/i.test(record.organism?.trim() ?? "")
            ? "Human"
            : /\b(?:mouse|mice|rats?|animal|rabbit|zebrafish|murine|rattus|mus musculus)\b/i.test(
                  record.organism ?? "",
                )
              ? "Animal"
              : "Context not recorded";
    counts[group] = (counts[group] ?? 0) + 1;
    return counts;
  }, {});

  function citations(ids: string[], citedClaim?: ResearchClaim) {
    return (
      <sup className="source-citations">
        {ids.map((id) => (
          <button
            key={id}
            className="citation"
            aria-label={`Source ${sourceNumbers.get(id) ?? "record"}`}
            onClick={() => setCitation({ id, claim: citedClaim })}
          >
            {sourceNumbers.get(id) ?? "?"}
          </button>
        ))}
      </sup>
    );
  }
  function claim(item: ResearchClaim) {
    return (
      <div key={item.id} className="research-claim">
        <p>
          {item.text} {citations(item.evidence_ids, item)}
        </p>
        <details className="claim-provenance">
          <summary className="disclosure">Context and limitations</summary>
          <p className="mt-2">
            {item.kind === "source_extract"
              ? "Source extract · preliminary"
              : item.kind === "structured_annotation"
                ? "Database annotation"
                : "Curated explanation"}
          </p>
          <p className="mt-2">{item.uncertainty}</p>
          {item.source_passage && item.source_passage !== item.text && (
            <blockquote className="mt-2 border-l-2 border-[var(--border)] pl-3">
              {item.source_passage}
            </blockquote>
          )}
        </details>
      </div>
    );
  }
  function edgeLabel(relation: ResearchClaim["relation"]) {
    return {
      ASSOCIATED_WITH: "associated with",
      SUPPORTED_BY: "linked to source",
      CONTRADICTED_BY: "challenged by source",
      PARTICIPATES_IN: "part of topic",
    }[relation];
  }

  return (
    <div className="research-brief">
      <header className="brief-header">
        <p className="section-note">
          {result.mode === "EXPLANATORY" ? "Biological explanation" : "Research investigation"}
          {" · "}
          {formatDate(result.created_at)}
        </p>
        <h1>{result.interpretation.question.original_text}</h1>
        <p className="section-note">
          {result.mode === "EXPLANATORY"
            ? "An introduction from the available sources. These annotations and extracts have not been independently reviewed here."
            : "Provisional findings from scientific sources. These extracts have not been reviewed as curated CausalBio evidence."}
        </p>
        {cached && !result.evidence.some((record) => record.cache_status === "fetched") && (
          <p className="section-note">
            Using cached evidence. Each reference retains its retrieval date.
          </p>
        )}
        {offline && (
          <p className="mt-3 text-xs">
            Offline mode — live literature research is unavailable. Available cached and local
            evidence is shown.
          </p>
        )}
        {unavailable > 0 && (
          <p className="section-note" role="status">
            {unavailable} source {unavailable === 1 ? "search was" : "searches were"} unavailable.
            This result uses the evidence that could be retrieved. Retry research to try again.
          </p>
        )}
      </header>
      <section className="prose-section" aria-labelledby="research-overview">
        <h2 id="research-overview">Research summary</h2>
        <div className="mt-5 space-y-5">{result.direct_answer.map(claim)}</div>
        {!result.direct_answer.length && (
          <p className="mt-4 text-sm leading-7">
            We could not retrieve enough evidence to give a supported answer to this question.
            Refine the question, retry research, or explore an available curated investigation.
          </p>
        )}
        {result.notices.map((notice) => (
          <p key={notice} className="section-note mt-4">
            {notice}
          </p>
        ))}
        <div className="mt-5 flex flex-wrap gap-3">
          {result.interpretation.depth !== "deep" && (
            <button className="text-link" onClick={onDeeper}>
              Expand evidence search
            </button>
          )}
          <button className="text-link" onClick={onRetry}>
            Retry research
          </button>
          {result.saved_locally && (
            <a className="text-link" href="#research-report">
              Read or download report
            </a>
          )}
        </div>
      </section>

      <section className="prose-section" aria-labelledby="research-mechanisms">
        <h2 id="research-mechanisms">Possible mechanisms</h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--ink-muted)]">
          {result.mechanisms.length
            ? "Related findings grouped by mechanism. These are starting points for investigation, not established causal explanations or treatment rankings."
            : "The available records do not support a mechanism summary for this question."}
        </p>
        <div className="mechanism-list">
          {result.mechanisms.map((mechanism, index) => (
            <article
              key={mechanism.id}
              className="mechanism-row"
              data-selected={mechanism.id === selectedId}
            >
              <span className="mechanism-number" aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div className="mechanism-content">
                <h3>{mechanism.title}</h3>
                {mechanism.claims[0] && (
                  <div className="mt-3">
                    <p className="line-clamp-2">{mechanism.claims[0].text}</p>
                    <div className="mt-1">
                      {citations(mechanism.claims[0].evidence_ids, mechanism.claims[0])}
                    </div>
                  </div>
                )}
                <button
                  className="text-link mt-3"
                  onClick={() => {
                    setSelectedId(mechanism.id);
                    setExpanded(true);
                    requestAnimationFrame(() => {
                      focusRef.current?.focus();
                      focusRef.current?.scrollIntoView({ block: "start" });
                    });
                  }}
                >
                  Explore mechanism<span className="sr-only">: {mechanism.title}</span>
                </button>
                <details className="claim-provenance mt-2">
                  <summary className="disclosure">Scope and uncertainty</summary>
                  <p className="mt-2">{mechanism.description}</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5">
                    {(mechanism.uncertainties.length
                      ? mechanism.uncertainties
                      : ["Independent review of the source context is needed."]
                    ).map((uncertainty) => (
                      <li key={uncertainty}>{uncertainty}</li>
                    ))}
                  </ul>
                </details>
              </div>
            </article>
          ))}
        </div>
      </section>

      {hasEvidenceDetail && (
        <button
          className="text-link mt-8"
          aria-expanded={expanded}
          aria-controls="research-detail"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "Hide evidence detail" : "Explore pathway, evidence and uncertainty"}
        </button>
      )}
      <div id="research-detail" hidden={hasEvidenceDetail && !expanded}>
        {hasFocusedPathway && (
          <section
            ref={focusRef}
            tabIndex={-1}
            className="prose-section scroll-mt-6"
            aria-labelledby="research-pathway"
          >
            <h2 id="research-pathway">Focused pathway</h2>
            <p className="section-note mt-2">{selected?.title ?? "Available source connections"}</p>
            {!!focusedEdges.length && (
              <figure className="research-figure">
                <figcaption>Figure 1. Sources connected to this mechanism</figcaption>
                <ol className="source-connections" aria-label="Focused research pathway">
                  {focusedEdges.map((edge) => (
                    <li key={edge.id}>
                      <strong>
                        {result.graph.nodes.find((node) => node.id === edge.subject_id)?.name}
                      </strong>
                      <span className="source-connection-label">{edgeLabel(edge.relation)}</span>
                      <strong>
                        {result.graph.nodes.find((node) => node.id === edge.object_id)?.name}
                      </strong>
                      {citations(edge.evidence_ids)}
                    </li>
                  ))}
                </ol>
                <p className="section-note mt-4">
                  Dashed connections link topics to source records; they do not establish causal
                  effects.
                </p>
                <p className="section-note mt-2">{result.graph.notice}</p>
              </figure>
            )}
            {!focusedEdges.length && (
              <p className="mt-4 text-sm">
                No source-supported connections are available for a focused map.
              </p>
            )}
            {!!selected?.claims.length && (
              <div className="mt-6 space-y-5">{selected.claims.map(claim)}</div>
            )}
            {selected && Object.keys(selected.evidence_dimensions).length > 0 && (
              <dl className="metadata mt-5">
                {Object.entries(selected.evidence_dimensions).map(([key, value]) => (
                  <div key={key}>
                    <dt>{humanize(key)}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
            )}
          </section>
        )}

        {result.evidence.length > 0 && (
          <section className="prose-section" aria-labelledby="research-evidence">
            <h2 id="research-evidence">References</h2>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-muted)]">
              Source records retain their reported context. Missing organism, tissue, study design,
              or effect size stays unknown. Counts do not establish independent replication.
              Database annotations are counted separately from studies, even when their protein
              belongs to a human organism.
            </p>
            <ul className="evidence-contexts">
              {[
                "Human",
                "Animal",
                "Cellular",
                "Computational",
                "Database annotation",
                "Context not recorded",
              ].map((name) => (
                <li key={name}>
                  {name}: {contexts[name] ?? 0}
                </li>
              ))}
            </ul>
            <ol className="reference-list">
              {result.evidence.map((record, index) => (
                <li
                  key={record.id}
                  className="reference-entry"
                  id={`research-evidence-${record.id}`}
                >
                  <span className="reference-number" aria-hidden="true">
                    {index + 1}.
                  </span>
                  <div className="reference-body">
                    <h3>
                      <button
                        className="text-link text-left"
                        onClick={() => setCitation({ id: record.id })}
                      >
                        {record.title}
                      </button>
                    </h3>
                    <p className="section-note mt-2">
                      {record.authors.join(", ") || "Authors not recorded"}.{" "}
                      {record.year ?? "Year not recorded"}. {record.source} ·{" "}
                      {sourceCategory(record)}
                    </p>
                    <p className="section-note mt-1">
                      {retrievalLabel(record)} {formatDate(record.retrieved_at)}
                    </p>
                    <details className="mt-3">
                      <summary className="disclosure">Study context and provenance</summary>
                      <EvidenceMetadata record={record} />
                    </details>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        )}

        <section className="prose-section" aria-labelledby="research-complications">
          <h2 id="research-complications">What complicates this explanation?</h2>
          <div className="mt-4 space-y-4">{result.complications.map(claim)}</div>
          {!result.complications.length && (
            <p className="mt-4 text-sm leading-6">
              No opposing finding was identified in the available extracts. This is not evidence
              that contradictions or failed replications do not exist.
            </p>
          )}
          <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6">
            {[...new Set([...result.limitations, ...(selected?.uncertainties ?? [])])].map(
              (text) => (
                <li key={text}>{text}</li>
              ),
            )}
          </ul>
        </section>

        <section className="prose-section" aria-labelledby="research-modifiers">
          <h2 id="research-modifiers">Relevant interventions or modifiers</h2>
          <p className="mt-3 text-sm leading-6 text-[var(--ink-muted)]">
            Research objects only. These records do not provide personal use, dosing, or treatment
            recommendations.
          </p>
          <div className="mt-4 space-y-4">{result.modifiers.map(claim)}</div>
          {!result.modifiers.length && (
            <p className="mt-3 text-sm">
              No intervention-specific claim was established from the retrieved material.
            </p>
          )}
        </section>
      </div>

      <section className="prose-section">
        <button
          className="flex w-full items-center justify-between text-left font-bold"
          aria-expanded={advanced}
          aria-controls="universal-advanced"
          onClick={() => setAdvanced(!advanced)}
        >
          Advanced analysis <span aria-hidden="true">{advanced ? "−" : "+"}</span>
        </button>
        <div id="universal-advanced" hidden={!advanced} className="mt-5 space-y-5">
          <p className="text-sm">
            No executable pathway model is available for this investigation. Source connections
            alone do not justify numerical simulation or Bayesian inference.
          </p>
          <p className="text-sm leading-6 text-[var(--ink-muted)]">{result.synthesis_method}</p>
          <details>
            <summary className="disclosure">Sources searched and availability</summary>
            <ul className="mt-3 space-y-3 text-xs leading-6">
              {result.source_runs.map((run, index) => (
                <li key={`${run.source}-${index}`}>
                  <strong>{run.source}</strong> · {humanize(run.status)} · {run.record_count}{" "}
                  records
                  {run.provider_version && <span> · Adapter {run.provider_version}</span>}
                  <br />
                  Query: {run.query}
                  {run.retrieved_at && (
                    <>
                      <br />
                      Retrieved: {formatDate(run.retrieved_at)}
                    </>
                  )}
                  {run.detail && <p>{run.detail}</p>}
                </li>
              ))}
            </ul>
          </details>
          <details>
            <summary className="disclosure">Explore full evidence map</summary>
            <p className="mt-3 text-xs leading-6">{result.graph.notice}</p>
            <ul className="mt-3 space-y-3 text-sm">
              {result.graph.edges.map((edge) => (
                <li key={edge.id}>
                  {result.graph.nodes.find((node) => node.id === edge.subject_id)?.name} →{" "}
                  {edgeLabel(edge.relation)} →{" "}
                  {result.graph.nodes.find((node) => node.id === edge.object_id)?.name}
                  <div className="mt-1 text-xs">{citations(edge.evidence_ids)}</div>
                </li>
              ))}
            </ul>
          </details>
          <details>
            <summary className="disclosure">Interpretation and reproducibility</summary>
            <p className="mt-3 text-sm">{result.interpretation.question.interpreted_summary}</p>
            <p className="mt-2 text-xs">
              Prepared {formatDate(result.created_at)}.{" "}
              {result.saved_locally
                ? "Saved in the local research service."
                : "This result has not been saved locally."}
            </p>
            <pre className="raw-data mt-3">{JSON.stringify(result, null, 2)}</pre>
          </details>
        </div>
      </section>
      <section id="research-report" className="prose-section scroll-mt-6">
        <h2>Research report</h2>
        <p className="mt-3 text-sm leading-6 text-[var(--ink-muted)]">
          The report preserves the investigation type, evidence status, retrieval dates, source
          failures, citations, and provisional map.
        </p>
        {result.saved_locally ? (
          <div className="mt-4 flex flex-wrap gap-3">
            <a
              className="button-primary"
              href={`${API_URL}/api/v1/research/${result.id}/report/html`}
              target="_blank"
              rel="noreferrer"
            >
              Read HTML report
            </a>
            <a
              className="button-secondary"
              href={`${API_URL}/api/v1/research/${result.id}/report/md`}
              download
            >
              Download Markdown
            </a>
            <a
              className="button-secondary"
              href={`${API_URL}/api/v1/research/${result.id}/report/json`}
              download
            >
              Download research JSON
            </a>
          </div>
        ) : (
          <p className="mt-4 text-sm">
            The local report is unavailable because this result was not saved. Retry research to try
            saving it again.
          </p>
        )}
      </section>
      <p className="section-note mt-6">{result.interpretation.safety_notice.message}</p>
      {citationRecord && (
        <EvidenceDrawer
          title={`Reference ${sourceNumbers.get(citationRecord.id)}`}
          onClose={() => setCitation(null)}
        >
          <h3 className="text-xl leading-snug">{citationRecord.title}</h3>
          <p className="section-note mt-3">
            {citationRecord.authors.join(", ") || "Authors not recorded"} ·{" "}
            {citationRecord.year ?? "Year not recorded"}
          </p>
          <p className="section-note mt-2">
            {citationRecord.source} · {sourceCategory(citationRecord)}
          </p>
          <p className="section-note mt-2">
            {citationRecord.evidence_status === "curated"
              ? "Curated evidence"
              : "Provisional evidence"}
            {" · "}
            {retrievalLabel(citationRecord)} {formatDate(citationRecord.retrieved_at)}
          </p>
          <section className="mt-6">
            <h4>Why this source is cited</h4>
            <p className="section-note mt-2">
              {citation?.claim
                ? "This source supports the selected finding. Its original context and limitations still apply."
                : "This record was retrieved for this investigation. Related findings are listed below when available."}
            </p>
            {citationClaims.map((item) => (
              <div key={item.id} className="mt-4">
                {item.source_passage ? (
                  <blockquote className="border-l-2 border-[var(--border)] pl-4 leading-7">
                    {item.source_passage}
                  </blockquote>
                ) : (
                  <p>{item.text}</p>
                )}
                <p className="section-note mt-2">{item.uncertainty}</p>
              </div>
            ))}
            {!citationClaims.length && (
              <p className="section-note mt-3">
                No finding in this result was extracted from this record.
              </p>
            )}
          </section>
          <EvidenceMetadata record={citationRecord} />
          <a
            className="text-link mt-6 inline-block"
            href={citationRecord.source_url}
            target="_blank"
            rel="noreferrer"
          >
            Read original source ↗
          </a>
        </EvidenceDrawer>
      )}
    </div>
  );
}

function sourceCategory(record: ResearchEvidence) {
  return /uniprot/i.test(record.source)
    ? "Protein database annotation"
    : record.primary_or_review === "unspecified"
      ? "Study category not recorded"
      : humanize(record.primary_or_review);
}

function retrievalLabel(record: ResearchEvidence) {
  return record.cache_status === "stale_cache"
    ? "Cached evidence; freshness has expired. Originally retrieved"
    : record.cache_status === "fresh_cache"
      ? "Cached evidence retrieved"
      : record.cache_status === "local_curated"
        ? "Local curated record retrieved"
        : "Evidence retrieved";
}

function EvidenceMetadata({ record }: { record: ResearchEvidence }) {
  return (
    <>
      <dl className="metadata mt-4">
        {Object.entries({
          Authors: record.authors.join(", ") || null,
          Journal: null,
          Organism: record.organism,
          Population: record.population,
          Tissue: record.tissue,
          "Cell type": record.cell_type,
          "Study design": record.study_type,
          "Experimental context": record.experimental_context,
          "Result direction":
            record.result_direction === "unspecified" ? null : humanize(record.result_direction),
          "Effect estimate": record.effect_estimate,
          "Sample size": record.sample_size,
          PMID: record.pmid,
          DOI: record.doi,
        }).map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{value ?? "Not recorded"}</dd>
          </div>
        ))}
      </dl>
      {!!record.annotation_evidence?.length && (
        <div className="mt-4">
          <h4 className="text-xs font-bold">Annotation evidence references</h4>
          <p className="mt-2 text-xs leading-6 text-[var(--ink-muted)]">
            References and evidence codes supplied by the protein database. An annotation may use
            similarity or other indirect evidence; its organism is not the study population.
          </p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-6">
            {record.annotation_evidence.map((item, index) => (
              <li key={`${item.evidence_code}-${item.identifier}-${index}`}>
                {item.evidence_code ?? "Evidence code not recorded"}
                {item.source && ` · ${item.source}`}
                {item.identifier &&
                  (item.source?.toLowerCase() === "pubmed" && /^\d+$/.test(item.identifier) ? (
                    <>
                      {" · "}
                      <a
                        className="underline underline-offset-2"
                        href={`https://pubmed.ncbi.nlm.nih.gov/${item.identifier}/`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {item.identifier} ↗
                      </a>
                    </>
                  ) : (
                    ` · ${item.identifier}`
                  ))}
              </li>
            ))}
          </ul>
        </div>
      )}
      <ul className="mt-4 list-disc space-y-2 pl-5 text-xs leading-6">
        {record.limitations.map((limitation) => (
          <li key={limitation}>{limitation}</li>
        ))}
      </ul>
    </>
  );
}
