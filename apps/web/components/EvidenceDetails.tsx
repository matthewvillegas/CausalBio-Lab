import type { CausalAssertion, EvidenceRecord, InvestigationResult } from "@/lib/types";
import { edgeMeaning, evidenceContext, humanize, formatDate } from "@/lib/presentation";

export function EvidenceCard({ record }: { record: EvidenceRecord }) {
  return (
    <article className="reference-entry">
      <p className="section-note">
        {evidenceContext(record)} evidence ·{" "}
        <span
          className={record.result_direction === "supports" ? undefined : "text-[var(--amber)]"}
        >
          {humanize(record.result_direction)}
        </span>{" "}
        · Species: {record.experimental_context.species}
      </p>
      <h4 className="mt-3 font-bold leading-6">
        <a className="source-link" href={record.study.source_url} target="_blank" rel="noreferrer">
          {record.study.title} ↗
        </a>
      </h4>
      <p className="mt-1 text-xs text-[var(--ink-muted)]">
        {record.study.authors.join(", ")} · {record.study.publication_year} · {record.study.journal}
      </p>
      <p className="mt-3 text-sm leading-6">{record.evidence_note}</p>
      {record.uncertainty_measure && (
        <p className="mt-3 text-xs leading-5 text-[var(--ink-muted)]">
          <strong>Reported uncertainty:</strong> {record.uncertainty_measure}
        </p>
      )}
      <p className="mt-3 text-xs leading-5 text-[var(--ink-muted)]">
        {record.experimental_context.population} ·{" "}
        {record.experimental_context.tissue ?? "Tissue not specified"} ·{" "}
        {record.experimental_context.condition ?? "Condition not specified"}
      </p>
      <ul className="mt-3 space-y-1 text-xs leading-5 text-[var(--amber)]">
        {record.limitations.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <details className="mt-4 text-xs">
        <summary className="disclosure">Study and provenance details</summary>
        <dl className="metadata mt-3">
          <dt>Study design</dt>
          <dd>{humanize(record.study.study_type)}</dd>
          <dt>Sample size</dt>
          <dd>{record.study.population.sample_size ?? "Not recorded"}</dd>
          <dt>Evidence grade</dt>
          <dd>{record.evidence_grade} (project rubric)</dd>
          <dt>Review state</dt>
          <dd>{record.curation_status}</dd>
          <dt>Retrieved</dt>
          <dd>{formatDate(record.retrieved_at)}</dd>
          <dt>Source adapter</dt>
          <dd>{record.source_adapter}</dd>
          {record.study.identifiers.map((id) => (
            <div className="contents" key={id.namespace + id.value}>
              <dt>{id.namespace}</dt>
              <dd>{id.value}</dd>
            </div>
          ))}
        </dl>
        {record.effect_estimate && (
          <p className="mt-3">
            {record.effect_estimate.measure}: {record.effect_estimate.value}{" "}
            {record.effect_estimate.unit}.
            {record.effect_estimate.interval_low !== null &&
              record.effect_estimate.interval_high !== null && (
                <span>
                  {" "}
                  {record.effect_estimate.interval_level !== null
                    ? `${Number((record.effect_estimate.interval_level * 100).toFixed(2))}% interval`
                    : "Reported interval"}
                  : {record.effect_estimate.interval_low}–{record.effect_estimate.interval_high}.
                </span>
              )}{" "}
            {record.effect_estimate.source_note}
          </p>
        )}
      </details>
    </article>
  );
}

export function AssertionEvidence({
  result,
  assertion,
}: {
  result: InvestigationResult;
  assertion: CausalAssertion;
}) {
  const name = (id: string) =>
    result.graph.entities.find((entity) => entity.id === id)?.preferred_name ?? "Unresolved entity";
  return (
    <section className="connection-evidence space-y-4 py-5" aria-label="Connection evidence">
      <p className="eyebrow">Why this connection?</p>
      <h3 className="font-bold">
        {name(assertion.subject_id)} → {name(assertion.object_id)}
      </h3>
      <span className="badge">{edgeMeaning(assertion)}</span>
      <p className="text-sm leading-6">{assertion.interpretation}</p>
      <p className="text-xs leading-5 text-[var(--ink-muted)]">
        Context: {assertion.biological_context.species} ·{" "}
        {assertion.biological_context.tissue ?? "Tissue not specified"} ·{" "}
        {assertion.biological_context.population}
      </p>
      <h4 className="font-bold">Supporting evidence</h4>
      {assertion.supporting_evidence_ids.length ? (
        result.graph.evidence
          .filter((record) => assertion.supporting_evidence_ids.includes(record.id))
          .map((record) => <EvidenceCard key={record.id} record={record} />)
      ) : (
        <p>No supporting study is recorded for this connection.</p>
      )}
      <h4 className="font-bold">Conflicting evidence</h4>
      {assertion.contradictory_evidence_ids.length ? (
        result.graph.evidence
          .filter((record) => assertion.contradictory_evidence_ids.includes(record.id))
          .map((record) => <EvidenceCard key={record.id} record={record} />)
      ) : (
        <p className="text-sm text-[var(--ink-muted)]">
          No conflicting study is linked in this pack. This is not evidence that none exists.
        </p>
      )}
      <ul className="space-y-1 text-sm text-[var(--amber)]">
        {assertion.limitations.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <details>
        <summary className="disclosure">Assertion provenance</summary>
        <dl className="metadata mt-3">
          <dt>Assertion ID</dt>
          <dd>{assertion.id}</dd>
          <dt>Relation</dt>
          <dd>{assertion.relation}</dd>
          <dt>Causal status</dt>
          <dd>{humanize(assertion.causal_status)}</dd>
          <dt>Confidence</dt>
          <dd>{assertion.confidence_classification}</dd>
          <dt>Curator</dt>
          <dd>{assertion.curator}</dd>
          <dt>Review state</dt>
          <dd>{assertion.review_status}</dd>
          <dt>Retrieved</dt>
          <dd>{assertion.retrieval_date}</dd>
          <dt>Extraction</dt>
          <dd>{assertion.extraction_method}</dd>
          <dt>Source</dt>
          <dd>{assertion.source}</dd>
        </dl>
      </details>
    </section>
  );
}
