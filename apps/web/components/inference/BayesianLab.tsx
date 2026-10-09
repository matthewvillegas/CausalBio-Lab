"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";

import { ApiError, runHMCDemo } from "@/lib/api";
import { ChartFrame } from "@/components/charts/ChartFrame";
import { humanize } from "@/lib/presentation";
import type { HMCInferenceRun, ProblemDetail } from "@/lib/types";

type HMCWorkflow =
  | { state: "READY" }
  | { state: "RUNNING" }
  | { state: "COMPLETE"; run: HMCInferenceRun }
  | { state: "FAILED"; problem: ProblemDetail };

const CHAIN_COLORS = ["var(--accent)", "var(--blue)", "var(--amber)", "var(--red)"];

export function BayesianLab() {
  const [workflow, setWorkflow] = useState<HMCWorkflow>({ state: "READY" });
  const [traceParameter, setTraceParameter] = useState("condition_effect");

  async function execute() {
    setWorkflow({ state: "RUNNING" });
    try {
      setWorkflow({ state: "COMPLETE", run: await runHMCDemo() });
    } catch (error) {
      const problem =
        error instanceof ApiError
          ? error.problem
          : {
              type: "about:blank",
              title: "HMC demonstration failed",
              status: 0,
              detail: "The local sampler could not complete. Check the API and retry.",
              correlation_id: "unavailable",
              alternatives: [],
            };
      setWorkflow({ state: "FAILED", problem });
    }
  }

  const traceData = useMemo(() => {
    if (workflow.state !== "COMPLETE") return [];
    const chains = workflow.run.posterior_draws[traceParameter] ?? [];
    const drawCount = chains[0]?.length ?? 0;
    const stride = Math.max(1, Math.floor(drawCount / 240));
    const points: Array<Record<string, number>> = [];
    for (let draw = 0; draw < drawCount; draw += stride) {
      const point: Record<string, number> = { draw };
      chains.forEach((chain, index) => {
        point[`chain_${index + 1}`] = chain[draw] ?? 0;
      });
      points.push(point);
    }
    return points;
  }, [traceParameter, workflow]);

  return (
    <div id="panel-bayesian" role="tabpanel">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Statistical teaching model</p>
          <h2 className="mt-2">Bayesian uncertainty demonstration</h2>
          <p className="mt-3 max-w-4xl text-sm leading-6 text-[var(--ink-muted)]">
            This demonstration estimates uncertain parameters when numerical observations, priors,
            and a likelihood are available. It uses synthetic data and does not estimate biological
            treatment effects. The investigation graph itself is not eligible for this analysis.
          </p>
        </div>
        <span className="badge" data-tone="amber">
          Synthetic · no biological claim
        </span>
      </div>

      {workflow.state === "READY" ? (
        <section className="mt-6 grid gap-5 border-t border-[var(--border)] pt-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
          <div>
            <h3 className="text-sm font-extrabold">
              Estimate a baseline and a difference between two synthetic groups
            </h3>
            <p className="mt-2 text-xs leading-5 text-[var(--ink-muted)]">
              Start with a prior belief centered on zero for each parameter (Normal with standard
              deviation 1). Then use 40 generated observations to estimate the baseline and group
              difference, with an interval describing uncertainty. The known noise standard
              deviation is 0.25. These numbers belong to a teaching example.
            </p>
          </div>
          <button type="button" className="button-primary" onClick={() => void execute()}>
            Run uncertainty demonstration
          </button>
        </section>
      ) : null}

      {workflow.state === "RUNNING" ? (
        <section role="status" className="mt-6 border-t border-[var(--border)] py-6">
          <div>
            <h3 className="font-semibold">Estimating parameters from synthetic observations</h3>
            <p className="mt-2 text-xs text-[var(--ink-muted)]">
              The sampler and checks are running locally.
            </p>
          </div>
        </section>
      ) : null}

      {workflow.state === "FAILED" ? (
        <section role="alert" className="mt-6 border-l-2 border-[var(--red)] pl-4">
          <h3 className="font-extrabold text-[var(--red)]">{workflow.problem.title}</h3>
          <p className="mt-2 text-xs leading-5">{workflow.problem.detail}</p>
          <button type="button" className="button-secondary mt-4" onClick={() => void execute()}>
            Retry
          </button>
        </section>
      ) : null}

      {workflow.state === "COMPLETE" ? (
        <HMCResults
          run={workflow.run}
          traceParameter={traceParameter}
          setTraceParameter={setTraceParameter}
          traceData={traceData}
        />
      ) : null}
    </div>
  );
}

function HMCResults({
  run,
  traceParameter,
  setTraceParameter,
  traceData,
}: {
  run: HMCInferenceRun;
  traceParameter: string;
  setTraceParameter: (value: string) => void;
  traceData: Array<Record<string, number>>;
}) {
  const clean = run.state === "COMPLETE" && run.diagnostics.warnings.length === 0;
  return (
    <div className="mt-6 space-y-5">
      {!clean ? (
        <section role="alert" className="border-l-2 border-[var(--amber)] pl-4">
          <h3 className="font-bold">
            {run.state === "FAILED" ? "Sampling failed" : "Sampling checks need attention"}
          </h3>
          <p className="mt-2 text-sm">
            Treat these estimates as provisional. The sampler did not provide a clean validation
            result.
          </p>
          <ul className="mt-2 space-y-2 text-xs">
            {run.diagnostics.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      ) : null}
      <section className="border-t border-[var(--border)] pt-5">
        <p className="eyebrow">Synthetic observations</p>
        <h3 className="mt-2 font-bold">{run.dataset.name}</h3>
        <p className="mt-2 text-sm leading-6">{run.dataset.description}</p>
        <p className="mt-2 text-xs text-[var(--ink-muted)]">
          {run.dataset.outcome.length} generated observations · known noise standard deviation{" "}
          {run.dataset.known_sigma}.
        </p>
        <p className="mt-3 text-xs leading-5">
          Observed synthetic group difference:{" "}
          {run.posterior_predictive.observed_group_difference.toFixed(3)}.
        </p>
        <p className="mt-3 text-xs leading-5 text-[var(--ink-muted)]">{run.dataset.provenance}</p>
        <details className="mt-4">
          <summary className="cursor-pointer text-xs font-bold">
            View generated observations
          </summary>
          <div className="mt-3 max-h-56 overflow-auto">
            <table className="scientific-table">
              <thead>
                <tr>
                  <th>Observation</th>
                  <th>Group</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {run.dataset.outcome.map((value, index) => (
                  <tr key={index}>
                    <td>{index + 1}</td>
                    <td>{run.dataset.predictor[index]}</td>
                    <td>{value.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>
      <section className="border-t border-[var(--border)] pt-5">
        <div className="pb-5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="badge" data-tone={clean ? "green" : "amber"}>
              {clean ? "Sampling checks passed" : "Provisional estimates"}
            </span>
          </div>
          <h3 id="posterior-estimates-title" className="mt-4 font-extrabold">
            Posterior parameter estimates
          </h3>
          <p className="mt-2 text-xs leading-5 text-[var(--ink-muted)]">
            Compare the prior belief with estimates after observing the generated data. These
            distributions describe only this synthetic model.
          </p>
        </div>
        <p id="posterior-table-scroll-hint" className="section-note mb-3 md:hidden">
          Scroll horizontally to see credible intervals and recovery checks.
        </p>
        <div
          className="overflow-x-auto"
          role="region"
          aria-labelledby="posterior-estimates-title"
          aria-describedby="posterior-table-scroll-hint"
          tabIndex={0}
        >
          <table className="scientific-table">
            <thead>
              <tr>
                <th>Parameter</th>
                <th>Prior</th>
                <th>Posterior mean</th>
                <th>95% credible interval</th>
                <th>Known truth recovered?</th>
              </tr>
            </thead>
            <tbody>
              {run.posterior_summaries.map((summary) => (
                <tr key={summary.parameter}>
                  <td>
                    <strong>{humanize(summary.parameter)}</strong>
                  </td>
                  <td>{priorLabel(run, summary.parameter)}</td>
                  <td>{summary.mean.toFixed(3)}</td>
                  <td>
                    [{summary.interval_low.toFixed(3)}, {summary.interval_high.toFixed(3)}]
                  </td>
                  <td>
                    <span
                      className="badge"
                      data-tone={run.recovery[summary.parameter] ? "green" : "red"}
                    >
                      {run.recovery[summary.parameter] ? "Yes" : "No"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="max-w-3xl border-t border-[var(--border)] pt-5">
        <h3 className="font-bold">What does this uncertainty mean?</h3>
        <p className="mt-3 text-sm leading-6">
          The 95% credible interval contains 95% of the sampled parameter distribution under the
          stated prior and likelihood. It describes uncertainty about the synthetic parameter, not a
          range of biological treatment effects. Changing model assumptions may change the interval.
        </p>
        <p className="mt-3 text-xs leading-5 text-[var(--ink-muted)]">
          Known truth is available because these data were generated. Recovery means the generating
          value lies inside the interval; it does not validate a biological mechanism.
        </p>
      </section>
      <details className="border-t border-[var(--border)] pt-5">
        <summary className="cursor-pointer font-extrabold">Advanced mathematical details</summary>
        <div className="mt-5 space-y-5">
          <dl className="divide-y divide-[var(--border)]">
            <DiagnosticRow
              label="Rank-normalized R-hat max"
              value={format(run.diagnostics.r_hat_max, 3)}
              detail="split and folded; target ≤ 1.01"
              good={(run.diagnostics.r_hat_max ?? Infinity) <= 1.01}
            />
            <DiagnosticRow
              label="Bulk ESS min"
              value={format(run.diagnostics.ess_bulk_min, 0)}
              detail="rank-normalized; target ≥ 400"
              good={(run.diagnostics.ess_bulk_min ?? 0) >= 400}
            />
            <DiagnosticRow
              label="Divergences"
              value={format(run.diagnostics.divergences, 0)}
              detail="target 0"
              good={run.diagnostics.divergences === 0}
            />
            <DiagnosticRow
              label="Acceptance"
              value={
                run.diagnostics.acceptance_rate === null
                  ? "Unavailable"
                  : `${format(run.diagnostics.acceptance_rate * 100, 1)}%`
              }
              detail="Metropolis acceptance"
              good={clean}
            />
            <DiagnosticRow
              label="E-BFMI min"
              value={format(run.diagnostics.energy_bfmi_min, 2)}
              detail="target ≥ 0.30"
              good={(run.diagnostics.energy_bfmi_min ?? 0) >= 0.3}
            />
          </dl>

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="border-t border-[var(--border)] pt-5">
              <p className="eyebrow">Posterior predictive check</p>
              <h3 className="mt-2 text-sm font-extrabold">Replicated group difference</h3>
              <dl className="mt-4 grid grid-cols-[1fr_auto] gap-2 text-xs">
                <dt className="text-[var(--ink-muted)]">Observed</dt>
                <dd>{run.posterior_predictive.observed_group_difference.toFixed(3)}</dd>
                <dt className="text-[var(--ink-muted)]">Replicated mean</dt>
                <dd>{run.posterior_predictive.replicated_mean.toFixed(3)}</dd>
                <dt className="text-[var(--ink-muted)]">95% predictive interval</dt>
                <dd>
                  [{run.posterior_predictive.interval_low.toFixed(3)},{" "}
                  {run.posterior_predictive.interval_high.toFixed(3)}]
                </dd>
                <dt className="text-[var(--ink-muted)]">Bayesian p-value</dt>
                <dd>{run.posterior_predictive.bayesian_p_value.toFixed(3)}</dd>
              </dl>
              <p className="mt-4 text-xs leading-5 text-[var(--ink-muted)]">
                {run.posterior_predictive.interpretation}
              </p>
            </div>
            <div className="border-t border-[var(--border)] pt-5">
              <p className="eyebrow">Uncertainty propagation</p>
              <h3 className="mt-2 text-sm font-extrabold">Latent scenario means</h3>
              <div className="mt-4 space-y-3">
                {run.scenario_predictions.map((scenario) => (
                  <div key={scenario.scenario} className="border-b border-[var(--border)] pb-3">
                    <div className="flex items-center justify-between gap-3 text-xs">
                      <strong>{scenario.scenario}</strong>
                      <span>{scenario.mean.toFixed(3)}</span>
                    </div>
                    <p className="mt-1 text-xs text-[var(--ink-muted)]">
                      95% interval [{scenario.interval_low.toFixed(3)},{" "}
                      {scenario.interval_high.toFixed(3)}] · latent mean only
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="border-t border-[var(--border)] pt-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="eyebrow">Trace diagnostic</p>
                <h3 className="mt-2 text-sm font-extrabold">Retained chain draws</h3>
              </div>
              <label className="text-xs font-bold text-[var(--ink-muted)]">
                Parameter
                <select
                  className="field ml-2 inline-block w-auto py-1.5"
                  value={traceParameter}
                  onChange={(event) => setTraceParameter(event.target.value)}
                >
                  {run.parameters.map((parameter) => (
                    <option key={parameter.name} value={parameter.name}>
                      {humanize(parameter.name)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <ChartFrame label={`Trace plot for ${traceParameter}`}>
              {({ width, height }) => (
                <LineChart
                  width={width}
                  height={height}
                  data={traceData}
                  margin={{ top: 8, right: 12, bottom: 8, left: 2 }}
                >
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                  <XAxis dataKey="draw" tick={{ fontSize: 12 }} stroke="var(--ink-muted)" />
                  <YAxis tick={{ fontSize: 12 }} stroke="var(--ink-muted)" width={48} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      borderRadius: 4,
                      color: "var(--ink)",
                      fontSize: 13,
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 13 }} />
                  {run.chain_diagnostics.map((chain, index) => (
                    <Line
                      key={chain.chain}
                      type="linear"
                      dataKey={`chain_${chain.chain}`}
                      name={`Chain ${chain.chain}`}
                      stroke={CHAIN_COLORS[index % CHAIN_COLORS.length]}
                      strokeDasharray={[undefined, "6 3", "2 3", "8 3 2 3"][index % 4]}
                      strokeWidth={1}
                      isAnimationActive={false}
                      dot={false}
                    />
                  ))}
                </LineChart>
              )}
            </ChartFrame>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="border-t border-[var(--border)] pt-5">
              <p className="text-sm font-extrabold">Prior sensitivity</p>
              <div className="mt-3 overflow-x-auto">
                <table className="scientific-table">
                  <thead>
                    <tr>
                      <th>Parameter</th>
                      <th>Alternate prior</th>
                      <th>Mean shift</th>
                    </tr>
                  </thead>
                  <tbody>
                    {run.sensitivity.map((item) => (
                      <tr key={`${item.parameter}-${item.perturbation}`}>
                        <td>{humanize(item.parameter)}</td>
                        <td>{item.perturbation}</td>
                        <td>
                          {item.outcome_change >= 0 ? "+" : ""}
                          {item.outcome_change.toFixed(4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="border-t border-[var(--border)] pt-5">
              <p className="text-sm font-extrabold">Model specification</p>
              <p className="mt-3 font-mono text-xs leading-5">
                yᵢ ~ Normal(β₀ + β₁xᵢ, {run.dataset.known_sigma})<br />
                β₀, β₁ ~ Normal(0, 1)
              </p>
              <p className="mt-3 text-xs leading-5 text-[var(--ink-muted)]">
                {run.dataset.provenance}
              </p>
              <p className="mt-3 font-mono text-xs text-[var(--ink-muted)]">
                posterior corr(β₀, β₁) ={" "}
                {run.posterior_correlation.baseline?.condition_effect?.toFixed(3)}
              </p>
            </div>
          </section>
          <section className="border-t border-[var(--border)] pt-5">
            <h3 className="text-sm font-bold">Per-parameter diagnostics</h3>
            <p className="mt-2 text-xs">
              {run.configuration.chains} chains · {run.configuration.draws} retained draws per
              chain.
            </p>
            <ul className="mt-3 space-y-2 text-xs">
              {run.parameters.map((parameter) => (
                <li key={parameter.name}>
                  {humanize(parameter.name)}: R-hat{" "}
                  {run.diagnostics.parameter_r_hat[parameter.name]?.toFixed(3) ?? "unavailable"};
                  bulk ESS{" "}
                  {run.diagnostics.parameter_ess_bulk[parameter.name]?.toFixed(0) ?? "unavailable"}.
                </li>
              ))}
            </ul>
          </section>
        </div>
      </details>
      <details className="border-t border-[var(--border)] pt-5">
        <summary className="cursor-pointer text-sm font-bold">Assumptions and limits</summary>
        <section className="mt-4 grid gap-4 lg:grid-cols-2">
          <div>
            <p className="text-sm font-extrabold">Assumptions</p>
            <ul className="mt-3 space-y-2 text-xs leading-5 text-[var(--ink-muted)]">
              {run.assumptions.map((item) => (
                <li key={item}>— {item}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-sm font-extrabold">Limits</p>
            <ul className="mt-3 space-y-2 text-xs leading-5 text-[var(--amber)]">
              {run.limitations.map((item) => (
                <li key={item}>— {item}</li>
              ))}
            </ul>
          </div>
        </section>
      </details>
    </div>
  );
}

function priorLabel(run: HMCInferenceRun, parameter: string) {
  const prior = run.priors.find((item) => item.parameter === parameter);
  return prior
    ? `${prior.distribution} (${Object.entries(prior.parameters)
        .map(([key, value]) => `${key}=${value}`)
        .join(", ")})`
    : "Not supplied";
}

function DiagnosticRow({
  label,
  value,
  detail,
  good,
}: {
  label: string;
  value: string;
  detail: string;
  good: boolean;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-5 gap-y-1 py-3 text-sm sm:grid-cols-[minmax(0,1fr)_7rem_minmax(0,1fr)]">
      <dt>{label}</dt>
      <dd className="font-mono">{value}</dd>
      <dd
        className={`col-span-2 text-xs sm:col-span-1 ${good ? "text-[var(--ink-muted)]" : "text-[var(--amber)]"}`}
      >
        {detail}
        {!good && " · check required"}
      </dd>
    </div>
  );
}

function format(value: number | null, decimals: number): string {
  return value === null ? "—" : value.toFixed(decimals);
}
