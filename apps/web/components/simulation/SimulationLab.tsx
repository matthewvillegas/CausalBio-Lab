"use client";

import { useMemo, useRef, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import { ApiError, simulate } from "@/lib/api";
import { ChartFrame } from "@/components/charts/ChartFrame";
import type {
  InvestigationResult,
  PetriModel,
  PetriScenario,
  ProblemDetail,
  SimulationRun,
} from "@/lib/types";

type Comparison = {
  baseline: SimulationRun;
  modified: SimulationRun;
  scenarioId: string;
  label: string;
  strength: number;
  description: string;
};
type Workflow =
  | { state: "READY" }
  | { state: "RUNNING" }
  | { state: "COMPLETE"; comparison: Comparison }
  | { state: "FAILED"; problem: ProblemDetail };

function scenarioOverrides(scenario: PetriScenario | undefined, strength: number) {
  const interpolate = (changes: PetriScenario["parameter_changes"] = []) =>
    Object.fromEntries(
      changes.map((change) => [
        change.key,
        change.baseline + (change.at_full_strength - change.baseline) * strength,
      ]),
    );
  return {
    parameters: interpolate(scenario?.parameter_changes),
    initials: interpolate(scenario?.initial_changes),
  };
}

export function SimulationLab({ result }: { result: InvestigationResult }) {
  if (!result.petri_model)
    return (
      <section id="panel-simulation" role="tabpanel">
        <h2>Pathway simulation</h2>
        <p className="mt-3 text-sm text-[var(--ink-muted)]">
          No executable pathway model is curated for this investigation. The evidence and mechanisms
          remain available.
        </p>
      </section>
    );
  return (
    <ModelSimulation
      key={`${result.petri_model.id}:${result.petri_model.model_version}`}
      model={result.petri_model}
    />
  );
}

function ModelSimulation({ model }: { model: PetriModel }) {
  const [scenarioId, setScenarioId] = useState(model.scenarios[0]?.id ?? "baseline");
  const [strength, setStrength] = useState(0.7);
  const [placeId, setPlaceId] = useState(model.output_place_id ?? model.places[0]?.id ?? "");
  const [workflow, setWorkflow] = useState<Workflow>({ state: "READY" });
  const baselineCache = useRef<Promise<SimulationRun> | null>(null);
  const scenario = model.scenarios.find((item) => item.id === scenarioId);
  const place = model.places.find((item) => item.id === placeId);

  async function runComparison() {
    const submitted = {
      scenarioId,
      strength,
      label: scenario?.label ?? "Baseline",
      description:
        scenario?.description ?? "Unmodified model with its declared initial states and rates.",
    };
    const overrides = scenarioOverrides(scenario, strength);
    setWorkflow({ state: "RUNNING" });
    try {
      if (!baselineCache.current)
        baselineCache.current = simulate(model.id, "baseline", {}, {}).catch((error: unknown) => {
          baselineCache.current = null;
          throw error;
        });
      const [baseline, modified] = await Promise.all([
        baselineCache.current,
        scenario
          ? simulate(model.id, scenario.id, overrides.parameters, overrides.initials)
          : baselineCache.current,
      ]);
      setWorkflow({ state: "COMPLETE", comparison: { ...submitted, baseline, modified } });
    } catch (error) {
      setWorkflow({
        state: "FAILED",
        problem:
          error instanceof ApiError
            ? error.problem
            : {
                type: "about:blank",
                title: "Simulation failed",
                status: 0,
                detail: "The model could not be executed. Check the local API and try again.",
                correlation_id: "unavailable",
                alternatives: [],
              },
      });
    }
  }

  const completed = workflow.state === "COMPLETE" ? workflow.comparison : null;
  const chartData = useMemo(
    () =>
      completed?.baseline.times.map((time, index) => ({
        time,
        baseline: completed.baseline.trajectories[placeId]?.[index],
        modified: completed.modified.trajectories[placeId]?.[index],
      })) ?? [],
    [completed, placeId],
  );
  const stale =
    completed &&
    (completed.scenarioId !== scenarioId ||
      (scenarioId !== "baseline" && completed.strength !== strength));
  const baselineFinal = completed?.baseline.trajectories[placeId]?.at(-1);
  const modifiedFinal = completed?.modified.trajectories[placeId]?.at(-1);

  return (
    <div id="panel-simulation" role="tabpanel">
      <p className="eyebrow">Computational workbench</p>
      <h2 className="mt-2">Pathway simulation</h2>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--ink-muted)]">
        Compare the model baseline with a declared change to its pathway. The trajectories show
        model behavior under the stated assumptions.
      </p>
      <p className="mt-2 text-xs text-[var(--ink-muted)]">
        {model.name} · {model.safety_label}
      </p>
      <div className="mt-6 grid gap-8 border-t border-[var(--border)] pt-6 lg:grid-cols-[250px_minmax(0,1fr)]">
        <section>
          <h3 className="text-sm font-extrabold">Explore a change</h3>
          <label className="mt-4 block">
            <span className="mb-2 block text-xs font-bold">Compare baseline with</span>
            <select
              className="field text-sm"
              value={scenarioId}
              onChange={(event) => setScenarioId(event.target.value)}
            >
              <option value="baseline">Baseline</option>
              {model.scenarios.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          <p className="mt-3 text-xs leading-5 text-[var(--ink-muted)]">
            {scenario?.description ?? "Run the model without changing its declared settings."}
          </p>
          {scenario ? (
            <label className="mt-4 block">
              <span className="flex justify-between text-xs font-bold">
                <span>Scenario strength</span>
                <span>{Math.round(strength * 100)}%</span>
              </span>
              <input
                aria-label="Scenario strength"
                className="mt-2 w-full accent-[var(--accent)]"
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={strength}
                onChange={(event) => setStrength(Number(event.target.value))}
              />
              <span className="block text-xs leading-5 text-[var(--ink-muted)]">
                Fraction of the declared synthetic change; not a biological dose.
              </span>
            </label>
          ) : null}
          <label className="mt-4 block">
            <span className="mb-2 block text-xs font-bold">State to explore</span>
            <select
              className="field text-sm"
              value={placeId}
              onChange={(event) => setPlaceId(event.target.value)}
            >
              {model.places.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} ({item.units})
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="button-primary mt-5 w-full"
            disabled={workflow.state === "RUNNING"}
            onClick={() => void runComparison()}
          >
            {workflow.state === "RUNNING" ? "Running model…" : "Run baseline comparison"}
          </button>
        </section>
        <section
          className="min-w-0 border-t border-[var(--border)] pt-6 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-8"
          aria-live="polite"
        >
          {workflow.state === "READY" ? (
            <p className="py-6 text-sm text-[var(--ink-muted)]">
              Choose a change and run the model to compare trajectories.
            </p>
          ) : null}
          {workflow.state === "RUNNING" ? (
            <p role="status" className="py-6 text-sm">
              Calculating model trajectories…
            </p>
          ) : null}
          {workflow.state === "FAILED" ? (
            <div role="alert">
              <h3 className="font-bold">{workflow.problem.title}</h3>
              <p className="mt-2 text-sm">{workflow.problem.detail}</p>
            </div>
          ) : null}
          {completed ? (
            <>
              <h3 className="font-extrabold">{place?.name}</h3>
              <p className="mt-2 text-xs text-[var(--ink-muted)]">
                Showing: {completed.label}
                {completed.scenarioId !== "baseline"
                  ? ` at ${Math.round(completed.strength * 100)}% strength`
                  : ""}
              </p>
              {stale ? (
                <p
                  role="status"
                  className="mt-3 border-l-2 border-[var(--amber)] pl-3 text-sm text-[var(--amber)]"
                >
                  Controls have changed. Run again to update these results.
                </p>
              ) : null}
              <figure className="mt-5">
                <figcaption className="text-xs text-[var(--ink-muted)]">
                  Model trajectories. Dashed line: baseline; solid line: submitted change.
                </figcaption>
                <ChartFrame label="Simulation trajectory chart">
                  {({ width, height }) => (
                    <LineChart width={width} height={height} data={chartData}>
                      <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                      <XAxis
                        dataKey="time"
                        tick={{ fontSize: 12 }}
                        stroke="var(--ink-muted)"
                        label={{
                          value: "Model time (a.u.)",
                          position: "insideBottom",
                          offset: -4,
                          fontSize: 12,
                        }}
                      />
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
                      <Legend wrapperStyle={{ fontSize: 13, paddingTop: 12 }} />
                      <Line
                        dataKey="baseline"
                        name="Baseline"
                        stroke="var(--blue)"
                        strokeWidth={2}
                        strokeDasharray="5 3"
                        isAnimationActive={false}
                        dot={false}
                      />
                      <Line
                        dataKey="modified"
                        name={completed.label}
                        stroke="var(--amber)"
                        isAnimationActive={false}
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  )}
                </ChartFrame>
              </figure>
              {baselineFinal !== undefined && modifiedFinal !== undefined ? (
                <dl className="mt-4 grid grid-cols-3 gap-3 text-xs">
                  <div>
                    <dt>Baseline final</dt>
                    <dd className="mt-1 font-mono font-bold">{baselineFinal.toFixed(3)}</dd>
                  </div>
                  <div>
                    <dt>Modified final</dt>
                    <dd className="mt-1 font-mono font-bold">{modifiedFinal.toFixed(3)}</dd>
                  </div>
                  <div>
                    <dt>Final difference ({place?.units})</dt>
                    <dd className="mt-1 font-mono font-bold">
                      {(modifiedFinal - baselineFinal).toFixed(3)}
                    </dd>
                  </div>
                </dl>
              ) : (
                <p className="mt-3 text-xs">This run did not return the selected state.</p>
              )}
              <details className="mt-5">
                <summary className="cursor-pointer text-xs font-bold">
                  View trajectory values
                </summary>
                <div className="mt-3 max-h-64 overflow-auto">
                  <table className="scientific-table">
                    <caption className="sr-only">
                      {place?.name} values in {place?.units}; submitted scenario: {completed.label}
                    </caption>
                    <thead>
                      <tr>
                        <th>Model time</th>
                        <th>Baseline</th>
                        <th>{completed.label}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {chartData.map((point) => (
                        <tr key={point.time}>
                          <td>{point.time.toFixed(2)}</td>
                          <td>{point.baseline?.toFixed(4) ?? "Unavailable"}</td>
                          <td>{point.modified?.toFixed(4) ?? "Unavailable"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </>
          ) : null}
        </section>
      </div>
      {completed ? <ChangeExplanation model={model} comparison={completed} /> : null}
      <details className="mt-6 border-t border-[var(--border)] pt-5">
        <summary className="cursor-pointer text-sm font-extrabold">View Petri-net model</summary>
        <p className="mt-4 text-xs leading-5">
          {model.description} Continuous solver: SciPy RK45. State bounds are numerical guards; they
          do not establish biological saturation. Conservation invariants are not asserted for this
          open model with input and loss.
        </p>
        <h3 className="mt-5 text-sm font-bold">Places and initial markings</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="scientific-table">
            <thead>
              <tr>
                <th>State</th>
                <th>Initial value</th>
                <th>Declared range</th>
                <th>Representation</th>
              </tr>
            </thead>
            <tbody>
              {model.places.map((item) => (
                <tr key={item.id}>
                  <td>{item.name}</td>
                  <td>
                    {item.initial_value} {item.units}
                  </td>
                  <td>
                    {item.valid_min}–{item.valid_max}
                  </td>
                  <td>{item.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h3 className="mt-5 text-sm font-bold">Transitions and rate laws</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="scientific-table">
            <thead>
              <tr>
                <th>Transition</th>
                <th>Rate law</th>
                <th>Parameters</th>
                <th>Assumptions</th>
              </tr>
            </thead>
            <tbody>
              {model.transitions.map((item) => (
                <tr key={item.id}>
                  <td>
                    {item.name}
                    <span className="block text-xs">{item.biological_event}</span>
                  </td>
                  <td>{item.rate_law}</td>
                  <td>
                    {Object.entries(item.parameters)
                      .map(([key, value]) => `${key}=${value}`)
                      .join(", ")}
                  </td>
                  <td>{item.assumptions.join(" ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h3 className="mt-5 text-sm font-bold">Arcs and gates</h3>
        <ul className="mt-3 space-y-2 text-xs">
          {model.arcs.map((arc) => (
            <li key={arc.id}>
              {model.places.find((item) => item.id === arc.place_id)?.name} — {arc.arc_type} —{" "}
              {model.transitions.find((item) => item.id === arc.transition_id)?.name}; weight{" "}
              {arc.weight}, threshold {arc.threshold > 0 ? arc.threshold : arc.weight}
            </li>
          ))}
        </ul>
      </details>
      <details className="mt-6 border-t border-[var(--border)] pt-5">
        <summary className="cursor-pointer text-sm font-extrabold">
          Model assumptions and limits
        </summary>
        <ul className="mt-3 space-y-2 text-xs leading-5 text-[var(--ink-muted)]">
          {model.assumptions.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        <p className="mt-3 text-xs leading-5">
          These trajectories describe this synthetic model. They cannot estimate treatment effects,
          diagnose a condition, or predict an individual outcome.
        </p>
      </details>
    </div>
  );
}

function ChangeExplanation({ model, comparison }: { model: PetriModel; comparison: Comparison }) {
  const differences = model.places.map((place) => {
    const baseline = comparison.baseline.trajectories[place.id] ?? [];
    const modified = comparison.modified.trajectories[place.id] ?? [];
    const first = baseline.findIndex(
      (value, index) => modified[index] !== undefined && Math.abs(modified[index]! - value) > 1e-5,
    );
    const final =
      baseline.length && modified.length
        ? modified[modified.length - 1]! - baseline[baseline.length - 1]!
        : null;
    return { place, first, final };
  });
  const changed = differences.filter((item) => item.first >= 0).sort((a, b) => a.first - b.first);
  const firstIndex = changed[0]?.first;
  const firstStates = changed
    .filter((item) => item.first === firstIndex)
    .map((item) => item.place.name);
  const warnings = [...new Set([...comparison.baseline.warnings, ...comparison.modified.warnings])];
  const gates = model.arcs.filter(
    (arc) => arc.arc_type === "read" || arc.arc_type === "inhibitory",
  );
  return (
    <section className="mt-6 border-t border-[var(--border)] pt-5">
      <h3 className="font-extrabold">What changed?</h3>
      <p className="mt-3 text-sm leading-6">{comparison.description}</p>
      <p className="mt-3 text-xs leading-5">
        {firstIndex !== undefined
          ? `First sampled differences: ${firstStates.join(", ")} at model time ${comparison.baseline.times[firstIndex]?.toFixed(2)}. Sampling does not establish the exact causal onset.`
          : "No state differences above 0.00001 were observed at the sampled times."}
      </p>
      <ul className="mt-3 space-y-2 text-xs leading-5">
        {changed
          .filter((item) => item.final !== null)
          .slice(0, 6)
          .map((item) => (
            <li key={item.place.id}>
              {item.place.name}: final change {item.final!.toFixed(3)} {item.place.units}.
            </li>
          ))}
      </ul>
      {gates.length ? (
        <div className="mt-4">
          <h4 className="text-xs font-bold">Why a control may have little downstream effect</h4>
          <p className="mt-2 text-xs leading-5">
            These are threshold gates. Raising a state while its gate stays open does not scale the
            transition rate.
          </p>
          <ul className="mt-2 space-y-2 text-xs leading-5">
            {gates.map((arc) => (
              <li key={arc.id}>
                {model.transitions.find((item) => item.id === arc.transition_id)?.name}:{" "}
                {model.places.find((item) => item.id === arc.place_id)?.name} must be{" "}
                {arc.arc_type === "read" ? "at least" : "below"}{" "}
                {arc.threshold > 0 ? arc.threshold : arc.weight}.
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <p className="mt-4 text-xs leading-5 text-[var(--ink-muted)]">
        A trajectory comparison alone does not identify a bottleneck, demonstrate biological
        saturation, or validate feedback. Rate laws, gates, and feedback connections are declared
        assumptions that can be inspected below.
      </p>
      {warnings.length ? (
        <div
          role="status"
          className="mt-4 border-l-2 border-[var(--amber)] pl-4 text-sm text-[var(--amber)]"
        >
          {warnings.join(" ")}
        </div>
      ) : null}
    </section>
  );
}
