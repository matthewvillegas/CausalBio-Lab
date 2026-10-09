"use client";

import { useState } from "react";

import { analyzeKnownPeptide, ApiError, compareKnownPeptides } from "@/lib/api";
import type { KnownPeptideAnalysis, PeptideSequenceComparison, ProblemDetail } from "@/lib/types";

const PEPTIDES = [
  ["substance-p", "Substance P"],
  ["neurokinin-a", "Neurokinin A"],
] as const;

type Workflow =
  | { state: "READY" }
  | { state: "RUNNING" }
  | {
      state: "COMPLETE";
      analysis: KnownPeptideAnalysis;
      comparison: PeptideSequenceComparison;
      submitted: { slug: string; ph: number };
    }
  | { state: "FAILED"; problem: ProblemDetail };

export function KnownPeptideLab() {
  const [slug, setSlug] = useState<string>(PEPTIDES[0][0]);
  const [phInput, setPhInput] = useState("7.4");
  const ph = Number.parseFloat(phInput);
  const [workflow, setWorkflow] = useState<Workflow>({ state: "READY" });
  const validPh = Number.isFinite(ph) && ph >= 0 && ph <= 14;
  const stale =
    workflow.state === "COMPLETE" &&
    (workflow.submitted.slug !== slug || workflow.submitted.ph !== ph);

  async function analyze() {
    if (!validPh || workflow.state === "RUNNING") return;
    const submitted = { slug, ph };
    setWorkflow({ state: "RUNNING" });
    const comparisonSlug = slug === "substance-p" ? "neurokinin-a" : "substance-p";
    try {
      const [analysis, comparison] = await Promise.all([
        analyzeKnownPeptide(slug, ph),
        compareKnownPeptides(slug, comparisonSlug),
      ]);
      setWorkflow({ state: "COMPLETE", analysis, comparison, submitted });
    } catch (error) {
      setWorkflow({
        state: "FAILED",
        problem:
          error instanceof ApiError
            ? error.problem
            : {
                type: "about:blank",
                title: "Known-peptide analysis failed",
                status: 0,
                detail:
                  "The curated record could not be calculated. Check the local API and retry.",
                correlation_id: "unavailable",
                alternatives: [],
              },
      });
    }
  }

  return (
    <div id="panel-peptides" role="tabpanel">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Known published sequences only</p>
          <h2 className="mt-2">Known peptide research</h2>
          <p className="mt-3 max-w-4xl text-sm leading-6 text-[var(--ink-muted)]">
            Explore the biological roles and known targets of published peptides. Each record
            identifies its evidence and limitations; sequence calculations are optional.
          </p>
        </div>
        <span className="badge" data-tone="amber">
          No design · synthesis · dosing
        </span>
      </div>

      <section className="mt-6 grid gap-5 border-y border-[var(--border)] py-5 lg:grid-cols-[minmax(0,1fr)_180px_auto] lg:items-end">
        <label>
          <span className="mb-1.5 block text-xs font-bold text-[var(--ink-muted)]">
            Known peptide
          </span>
          <select
            className="field text-sm"
            value={slug}
            onChange={(event) => setSlug(event.target.value)}
          >
            {PEPTIDES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <details>
          <summary className="cursor-pointer text-xs font-bold">Calculation settings</summary>
          <label className="mt-3 block">
            <span className="mb-1.5 block text-xs font-bold text-[var(--ink-muted)]">
              Charge estimate pH
            </span>
            <input
              className="field text-sm"
              type="number"
              min="0"
              max="14"
              step="0.1"
              value={phInput}
              aria-invalid={!validPh}
              aria-describedby={!validPh ? "peptide-ph-error" : undefined}
              onChange={(event) => setPhInput(event.target.value)}
            />
          </label>
          {!validPh ? (
            <p id="peptide-ph-error" role="alert" className="mt-2 text-xs text-[var(--red)]">
              Enter a pH from 0 to 14.
            </p>
          ) : null}
          <p className="mt-2 text-xs text-[var(--ink-muted)]">
            Used only for the optional charge calculation.
          </p>
        </details>
        <button
          type="button"
          className="button-primary"
          onClick={() => void analyze()}
          disabled={workflow.state === "RUNNING" || !validPh}
        >
          {workflow.state === "RUNNING" ? "Calculating…" : "Analyze known record"}
        </button>
      </section>

      {workflow.state === "RUNNING" ? (
        <p role="status" className="mt-5 text-sm">
          Loading the published record and calculating descriptive properties…
        </p>
      ) : null}
      {stale ? (
        <p
          role="status"
          className="mt-5 border-l-2 border-[var(--amber)] pl-4 text-sm text-[var(--amber)]"
        >
          Selection or calculation settings have changed. Analyze again to update the record below.
        </p>
      ) : null}

      {workflow.state === "READY" ? (
        <div className="mt-5 text-sm leading-6 text-[var(--ink-muted)]">
          Choose a published peptide to explore its biological context, targets, and evidence.
        </div>
      ) : null}
      {workflow.state === "FAILED" ? (
        <div role="alert" className="mt-5 border-l-2 border-[var(--red)] pl-4">
          <h3 className="font-extrabold text-[var(--red)]">{workflow.problem.title}</h3>
          <p className="mt-2 text-xs">{workflow.problem.detail}</p>
        </div>
      ) : null}
      {workflow.state === "COMPLETE" ? (
        <PeptideResults analysis={workflow.analysis} comparison={workflow.comparison} />
      ) : null}
    </div>
  );
}

function PeptideResults({
  analysis,
  comparison,
}: {
  analysis: KnownPeptideAnalysis;
  comparison: PeptideSequenceComparison;
}) {
  const properties = analysis.calculated_properties;
  return (
    <div className="mt-5 space-y-5">
      <section className="max-w-3xl">
        <div className="flex flex-wrap gap-2">
          <span className="badge" data-tone="green">
            Curated record
          </span>
          <span className="badge">{analysis.peptide.organism}</span>
        </div>
        <h3 className="mt-4 text-xl font-medium">{analysis.peptide.name}</h3>
        <h4 className="mt-5 text-sm font-bold">Biological role and research context</h4>
        <ul className="mt-3 space-y-2 text-sm leading-6">
          {analysis.peptide.reported_biological_context.map((context) => (
            <li key={context}>{context}</li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-[var(--ink-muted)]">
          Precursor: {analysis.peptide.precursor}.
        </p>
      </section>
      <section className="grid gap-5 lg:grid-cols-2">
        <div className="border-t border-[var(--border)] pt-5">
          <h3 className="font-extrabold">Known biological targets</h3>
          <ul className="mt-3 space-y-4 text-sm leading-6">
            {analysis.peptide.known_targets.map((target) => (
              <li key={target.identifier}>
                <a
                  className="font-bold text-[var(--accent)] hover:underline"
                  href={target.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {target.name}
                </a>
                <p className="text-xs text-[var(--ink-muted)]">
                  {target.relationship} · {target.identifier}
                </p>
              </li>
            ))}
          </ul>
          {!analysis.peptide.known_targets.length ? (
            <p className="mt-3 text-sm">No target annotation is bundled.</p>
          ) : null}
        </div>
        <div className="border-t border-[var(--border)] pt-5">
          <h3 className="font-extrabold">Evidence and uncertainty</h3>
          <p className="mt-3 text-sm leading-6">{analysis.peptide.evidence_stage}</p>
          <ul className="mt-3 space-y-2 text-xs leading-5 text-[var(--ink-muted)]">
            {analysis.peptide.annotation_limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
          <a
            className="mt-4 inline-block text-xs font-bold text-[var(--accent)] hover:underline"
            href={analysis.peptide.source_url}
            target="_blank"
            rel="noreferrer"
          >
            View source annotation
          </a>
        </div>
      </section>
      <details className="border-t border-[var(--border)] pt-5">
        <summary className="cursor-pointer text-sm font-extrabold">
          Advanced peptide properties
        </summary>
        <div className="mt-4 border-l-2 border-[var(--border-strong)] pl-4">
          <p className="text-xs font-bold">Published mature sequence</p>
          <p className="mt-2 break-all font-mono text-lg">{analysis.peptide.sequence}</p>
          <p className="mt-2 text-xs">{analysis.peptide.terminal_modifications.join(", ")}</p>
        </div>
        <p className="mt-4 text-xs leading-5 text-[var(--ink-muted)]">
          These are calculations from a known sequence. They do not predict biological activity,
          efficacy, or safety.
        </p>
        <dl className="mt-4 divide-y divide-[var(--border)]">
          <Property label="Length" value={`${properties.sequence_length} aa`} />
          <Property
            label="Approx. molecular weight"
            value={`${properties.approximate_molecular_weight_da.toFixed(2)} Da`}
          />
          <Property
            label={`Estimated charge at pH ${properties.charge_pH}`}
            value={signed(properties.estimated_net_charge, 3)}
          />
          <Property
            label="Estimated pI"
            value={properties.estimated_isoelectric_point?.toFixed(3) ?? "No finite root"}
          />
          <Property
            label="Mean hydrophobicity"
            value={properties.mean_kyte_doolittle_hydrophobicity.toFixed(3)}
          />
          <Property
            label="Absolute charge density"
            value={properties.absolute_charge_density.toFixed(3)}
          />
          <Property
            label="Signed charge density"
            value={signed(properties.signed_charge_density, 3)}
          />
          <Property
            label="α-helix hydrophobic moment"
            value={properties.alpha_helix_hydrophobic_moment.toFixed(3)}
          />
          <Property
            label="β-strand hydrophobic moment"
            value={properties.beta_strand_hydrophobic_moment.toFixed(3)}
          />
          <Property
            label="Normalized sequence entropy"
            value={properties.normalized_sequence_entropy.toFixed(3)}
          />
        </dl>
        <h4 className="mt-5 text-sm font-bold">Amino-acid composition</h4>
        <div className="mt-3 overflow-x-auto">
          <table className="scientific-table">
            <thead>
              <tr>
                <th>Residue</th>
                <th>Count</th>
                <th>Fraction</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(properties.amino_acid_composition.counts).map(([residue, count]) => (
                <tr key={residue}>
                  <td>{residue}</td>
                  <td>{count}</td>
                  <td>
                    {properties.amino_acid_composition.fractions[residue]?.toFixed(3) ??
                      "Unavailable"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h4 className="mt-5 text-sm font-bold">Measured properties</h4>
        {Object.keys(analysis.measured_properties).length ? (
          <dl className="mt-3 space-y-2 text-xs">
            {Object.entries(analysis.measured_properties).map(([name, value]) => (
              <div key={name}>
                <dt className="font-bold">{name}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="mt-2 text-xs leading-5">
            No measured properties are bundled. Calculations remain separate from measurements.
          </p>
        )}
        <h4 className="mt-5 text-sm font-bold">Model heuristic: amphipathicity indicator</h4>
        <p className="mt-2 text-sm capitalize">
          {analysis.model_predictions.amphipathicity_indicator}
        </p>
        <p className="mt-2 text-xs leading-5">
          {analysis.model_predictions.rule} No activity prediction.
        </p>
        <details className="mt-5">
          <summary className="cursor-pointer text-xs font-bold">
            Calculation notes and unsupported assumptions
          </summary>
          <ul className="mt-3 space-y-2 text-xs leading-5">
            {[...analysis.calculation_notes, ...analysis.unsupported_assumptions].map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </details>
      </details>
      <details className="border-t border-[var(--border)] pt-5">
        <summary className="cursor-pointer text-sm font-extrabold">
          Structures and sequence comparison
        </summary>
        <h4 className="mt-4 text-sm font-bold">Curated structures</h4>
        <ul className="mt-3 space-y-3 text-xs leading-5">
          {analysis.peptide.available_structures.map((structure) => (
            <li key={structure.identifier}>
              <a
                className="font-bold text-[var(--accent)] hover:underline"
                href={structure.source_url}
                target="_blank"
                rel="noreferrer"
              >
                {structure.identifier}
              </a>{" "}
              · {structure.description}
            </li>
          ))}
        </ul>
        {!analysis.peptide.available_structures.length ? (
          <p className="mt-3 text-xs">No structure is curated in this record.</p>
        ) : null}
        <h4 className="mt-5 text-sm font-bold">
          Descriptive comparison with the other bundled peptide
        </h4>
        <div className="mt-3 overflow-x-auto border-l-2 border-[var(--border-strong)] pl-4 font-mono text-sm leading-7">
          <div>{comparison.aligned_a}</div>
          <div>{comparison.aligned_b}</div>
        </div>
        <p className="mt-3 text-xs leading-5">
          {(comparison.sequence_identity * 100).toFixed(1)}% global identity. Conserved residues:{" "}
          {comparison.conserved_positions.map((item) => item.residue).join(", ")}.
        </p>
        <p className="mt-2 text-xs leading-5 text-[var(--ink-muted)]">
          {comparison.interpretation}
        </p>
      </details>
      <p className="border-l-2 border-[var(--amber)] pl-4 text-sm leading-6 text-[var(--amber)]">
        {analysis.safety_notice}
      </p>
    </div>
  );
}

function Property({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-4 py-3 text-sm">
      <dt className="text-[var(--ink-muted)]">{label}</dt>
      <dd className="font-mono">{value}</dd>
    </div>
  );
}

function signed(value: number, decimals: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(decimals)}`;
}
