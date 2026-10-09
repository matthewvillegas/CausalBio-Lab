"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import {
  ApiError,
  API_URL,
  createInvestigation,
  interpretResearch,
  researchQuestion,
  researchStatus,
  researchSessions,
  loadResearchSession,
} from "@/lib/api";
import type { InvestigationResult, ProblemDetail, QuestionContext } from "@/lib/types";
import { formatDate } from "@/lib/presentation";
import { ResultsView } from "@/components/ResultsView";
import { UniversalResultsView } from "@/components/UniversalResultsView";
import type {
  ResearchDepth,
  ResearchInterpretation,
  ResearchServiceStatus,
  ResearchSession,
  UniversalResearchResult,
} from "@/lib/research-types";

interface Example {
  slug: string;
  title: string;
  example_questions: string[];
}
type Workflow =
  | { stage: "EMPTY" }
  | { stage: "INTERPRETING"; question: string }
  | {
      stage: "NEEDS_CONTEXT";
      question: string;
      interpretation: ResearchInterpretation;
      context: QuestionContext;
    }
  | { stage: "BUILDING"; question: string; curated: boolean }
  | { stage: "COMPLETE"; result: InvestigationResult }
  | { stage: "RESEARCH_COMPLETE"; result: UniversalResearchResult }
  | { stage: "GUIDANCE"; question: string; interpretation: ResearchInterpretation }
  | { stage: "FAILED"; question: string; problem: ProblemDetail };
const FAILURE: ProblemDetail = {
  type: "about:blank",
  title: "We could not reach the research service",
  status: 0,
  detail:
    "Your question has not been analyzed. Check that the local API is running, then try again.",
  correlation_id: "unavailable",
  alternatives: [],
};

export function InvestigationApp() {
  const [workflow, setWorkflow] = useState<Workflow>({ stage: "EMPTY" });
  const [question, setQuestion] = useState("");
  const [page, setPage] = useState<"investigate" | "library" | "about">("investigate");
  const [theme, setTheme] = useState("light");
  const [editing, setEditing] = useState(false);
  const [examples, setExamples] = useState<Example[]>([]);
  const [libraryState, setLibraryState] = useState<"loading" | "ready" | "failed">("loading");
  const [depth, setDepth] = useState<ResearchDepth>("research");
  const [online, setOnline] = useState(true);
  const [service, setService] = useState<ResearchServiceStatus | null>();
  const [sessions, setSessions] = useState<ResearchSession[]>([]);
  const [sessionsFailed, setSessionsFailed] = useState(false);
  const requestVersion = useRef(0);
  const mainRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_URL}/api/v1/demo-cases`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Library unavailable");
        const data: Example[] = await response.json();
        if (
          !Array.isArray(data) ||
          data.some(
            (item) => typeof item.title !== "string" || !Array.isArray(item.example_questions),
          )
        )
          throw new Error("Invalid library metadata");
        setExamples(data);
        setLibraryState("ready");
      })
      .catch(() => {
        if (!controller.signal.aborted) setLibraryState("failed");
      });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    let active = true;
    void researchStatus()
      .then((status) => {
        if (active) setService(status);
      })
      .catch(() => {
        if (active) setService(null);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (page === "about") return;
    let active = true;
    void researchSessions()
      .then((items) => {
        if (active) {
          setSessions(items);
          setSessionsFailed(false);
        }
      })
      .catch(() => {
        if (active) setSessionsFailed(true);
      });
    return () => {
      active = false;
    };
  }, [page]);
  useEffect(() => {
    if (workflow.stage !== "EMPTY") mainRef.current?.focus();
  }, [workflow.stage]);
  useEffect(
    () => () => {
      requestVersion.current += 1;
    },
    [],
  );

  async function begin(value: string, requestedDepth: ResearchDepth = depth) {
    const normalized = value.trim();
    if (normalized.length < 3) return;
    const version = ++requestVersion.current;
    setPage("investigate");
    setQuestion(normalized);
    setEditing(false);
    setWorkflow({ stage: "INTERPRETING", question: normalized });
    try {
      const interpretation = await interpretResearch(normalized, requestedDepth, online);
      if (version !== requestVersion.current) return;
      if (
        [
          "RESTRICTED_WITH_SAFE_ALTERNATIVE",
          "CLARIFICATION_REQUIRED",
          "OUT_OF_DOMAIN",
          "ERROR",
        ].includes(interpretation.mode)
      ) {
        setWorkflow({ stage: "GUIDANCE", question: normalized, interpretation });
        return;
      }
      if (interpretation.mode === "EXPLANATORY" && requestedDepth !== "deep") {
        setWorkflow({ stage: "BUILDING", question: normalized, curated: false });
        const result = await researchQuestion(normalized, {}, requestedDepth, online);
        if (version === requestVersion.current) setWorkflow({ stage: "RESEARCH_COMPLETE", result });
        return;
      }
      setWorkflow({
        stage: "NEEDS_CONTEXT",
        question: normalized,
        interpretation,
        context: interpretation.question.context,
      });
    } catch (error) {
      if (version === requestVersion.current)
        setWorkflow({
          stage: "FAILED",
          question: normalized,
          problem: error instanceof ApiError ? error.problem : FAILURE,
        });
    }
  }
  async function confirm() {
    if (workflow.stage !== "NEEDS_CONTEXT") return;
    const current = workflow;
    const version = ++requestVersion.current;
    setWorkflow({
      stage: "BUILDING",
      question: current.question,
      curated: current.interpretation.mode === "CURATED",
    });
    const context = Object.fromEntries(
      Object.entries(current.context).filter(
        ([, value]) => typeof value === "string" || typeof value === "boolean" || value === null,
      ),
    );
    try {
      if (current.interpretation.mode === "CURATED") {
        const result = await createInvestigation(current.question, context);
        if (version === requestVersion.current) setWorkflow({ stage: "COMPLETE", result });
      } else {
        const result = await researchQuestion(
          current.question,
          context,
          current.interpretation.depth,
          online,
        );
        if (version === requestVersion.current) setWorkflow({ stage: "RESEARCH_COMPLETE", result });
      }
    } catch (error) {
      if (version === requestVersion.current)
        setWorkflow({
          stage: "FAILED",
          question: current.question,
          problem: error instanceof ApiError ? error.problem : FAILURE,
        });
    }
  }
  function reset() {
    requestVersion.current += 1;
    setWorkflow({ stage: "EMPTY" });
    setQuestion("");
    setPage("investigate");
    window.scrollTo({ top: 0 });
    requestAnimationFrame(() => document.getElementById("question")?.focus());
  }
  function update(field: keyof QuestionContext, value: string) {
    setWorkflow((current) =>
      current.stage === "NEEDS_CONTEXT"
        ? { ...current, context: { ...current.context, [field]: value || null } }
        : current,
    );
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void begin(question);
  }
  async function openSession(session: ResearchSession) {
    const version = ++requestVersion.current;
    setPage("investigate");
    setQuestion(session.question);
    setWorkflow({ stage: "BUILDING", question: session.question, curated: false });
    try {
      const result = await loadResearchSession(session.id);
      if (version === requestVersion.current)
        setWorkflow(
          result.curated_result
            ? { stage: "COMPLETE", result: result.curated_result }
            : { stage: "RESEARCH_COMPLETE", result },
        );
    } catch (error) {
      if (version === requestVersion.current)
        setWorkflow({
          stage: "FAILED",
          question: session.question,
          problem: error instanceof ApiError ? error.problem : FAILURE,
        });
    }
  }
  const busy = workflow.stage === "INTERPRETING" || workflow.stage === "BUILDING";
  const context = workflow.stage === "NEEDS_CONTEXT" ? workflow.context : null;
  const exampleButtons = (
    <div className="notebook-list">
      {examples.map((example) => (
        <button
          key={example.slug}
          disabled={busy}
          onClick={() => void begin(example.example_questions[0] ?? "")}
        >
          {example.title}
          <small>Curated investigation</small>
        </button>
      ))}
    </div>
  );
  return (
    <div className="page-shell">
      <a className="skip-link" href="#main-content">
        Skip to investigation
      </a>
      <header className="border-b border-[var(--border)] bg-[var(--surface)]">
        <div className="site-header">
          <button
            className="flex items-center gap-3 text-left"
            onClick={reset}
            aria-label="Return to CausalBio Lab home"
          >
            <span className="brand-mark" aria-hidden="true">
              c<span>·</span>b
            </span>
            <span className="brand-name">CausalBio Lab</span>
          </button>
          <nav className="site-nav" aria-label="Main navigation">
            {(
              [
                ["investigate", "Investigate"],
                ["library", "Library"],
                ["about", "About"],
              ] as const
            ).map(([id, label]) => (
              <button
                className="button-quiet px-3 text-xs"
                key={id}
                aria-current={page === id ? "page" : undefined}
                onClick={() => setPage(id)}
              >
                {label}
              </button>
            ))}
            <button
              className="button-quiet px-3"
              onClick={() => {
                const next = theme === "light" ? "dark" : "light";
                setTheme(next);
                document.documentElement.classList.toggle("dark", next === "dark");
              }}
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
            >
              ◐
            </button>
          </nav>
          <p className="service-status">
            {!online
              ? "Offline — using cached/curated evidence"
              : service === undefined
                ? "Checking research service…"
                : (service?.status_label ?? "Research service status unavailable")}
          </p>
        </div>
      </header>
      <main id="main-content" tabIndex={-1} ref={mainRef}>
        {page === "about" && <About />}
        {page === "library" && (
          <section className="reading-page">
            <p className="eyebrow">Evidence library</p>
            <h1 className="mt-3 text-3xl font-bold">Curated investigations</h1>
            <p className="mt-4 text-sm leading-6 text-[var(--ink-muted)]">
              Two topics reviewed in depth, with evidence maps and optional numerical
              demonstrations. These are small educational collections, not comprehensive reviews.
            </p>
            {exampleButtons}
            {libraryState === "loading" && <p role="status">Loading available examples…</p>}
            {libraryState === "failed" && (
              <p role="alert" className="mt-4">
                The example library could not load. Start the local API and reload this page.
              </p>
            )}
            <h2 className="mt-10 text-xl font-bold">Recent investigations</h2>
            <p className="mt-3 text-sm leading-6 text-[var(--ink-muted)]">
              Research sessions saved by this local service. Opening a saved result preserves its
              original evidence and retrieval dates.
            </p>
            {sessionsFailed ? (
              <p className="mt-4 text-sm" role="status">
                Saved investigations are temporarily unavailable.
              </p>
            ) : sessions.length ? (
              <div className="session-list mt-4">
                {sessions.map((session) => (
                  <button
                    key={session.id}
                    className="text-sm"
                    onClick={() => void openSession(session)}
                  >
                    {session.question}
                    <span className="mt-2 block text-xs text-[var(--ink-muted)]">
                      Saved {formatDate(session.created_at, true)}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm text-[var(--ink-muted)]">
                Your locally saved research will appear here.
              </p>
            )}
          </section>
        )}
        {page === "investigate" && (
          <>
            {(workflow.stage === "EMPTY" || workflow.stage === "INTERPRETING") && (
              <div className="home-workspace">
                <section className="home-introduction">
                  <h1>Investigate biological mechanisms</h1>
                  <p>
                    Ask about a biological process, pathway, tissue, molecule, intervention, or
                    symptom.
                  </p>
                  <form onSubmit={submit} className="question-form">
                    <label htmlFor="question">Your research question</label>
                    <textarea
                      id="question"
                      aria-label="What biological question do you want to investigate?"
                      className="field"
                      rows={3}
                      maxLength={2000}
                      value={question}
                      onChange={(event) => setQuestion(event.target.value)}
                      placeholder="What mechanisms influence tendon recovery?"
                      disabled={busy}
                    />
                    <div className="form-actions">
                      <button
                        type="submit"
                        className="button-primary"
                        disabled={busy || question.trim().length < 3}
                      >
                        {busy ? "Reading your question…" : "Investigate"}
                        <span aria-hidden="true">→</span>
                      </button>
                    </div>
                  </form>
                  <details className="research-options">
                    <summary className="disclosure">Research options</summary>
                    <label>
                      Search scope
                      <select
                        className="field"
                        value={depth}
                        disabled={busy}
                        onChange={(event) => setDepth(event.target.value as ResearchDepth)}
                      >
                        <option value="quick">Quick overview</option>
                        <option value="research">Standard research</option>
                        <option value="deep">Expanded search</option>
                      </select>
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={online}
                        disabled={busy}
                        onChange={(event) => setOnline(event.target.checked)}
                      />
                      Use live scientific sources when available
                    </label>
                    <p className="mt-2 text-[var(--ink-muted)]">
                      Live searches send your question’s scientific terms to public sources. Leave
                      out personal information.
                    </p>
                  </details>
                  <p className="workspace-note">
                    CausalBio organizes available evidence into mechanisms, sources, and
                    uncertainties. Two topics have been reviewed in depth; other questions draw on
                    available scientific sources.
                  </p>
                </section>
                <aside className="workspace-aside" aria-label="Investigation library">
                  <h2>Example investigations</h2>
                  {exampleButtons}
                  <div className="notebook-list mt-0">
                    {[
                      ["Tendon recovery", "What mechanisms influence tendon recovery?"],
                      ["BDNF signaling", "What does BDNF do?"],
                    ].map(([label, value]) => (
                      <button
                        key={value}
                        aria-label={value}
                        disabled={busy}
                        onClick={() => void begin(value!)}
                      >
                        {label}
                        <small>Research from scientific sources</small>
                      </button>
                    ))}
                  </div>
                  {libraryState === "loading" && (
                    <p className="mt-3 text-sm" role="status">
                      Loading curated investigations…
                    </p>
                  )}
                  {libraryState === "failed" && (
                    <p className="mt-3 text-sm" role="alert">
                      The curated library is unavailable. Check the local API and reload.
                    </p>
                  )}
                  {!!sessions.length && (
                    <section className="mt-8">
                      <h2>Recent research</h2>
                      <div className="notebook-list">
                        {sessions.slice(0, 3).map((session) => (
                          <button
                            key={session.id}
                            onClick={() => void openSession(session)}
                            disabled={busy}
                          >
                            {session.question}
                            <small>Saved {formatDate(session.created_at, true)}</small>
                          </button>
                        ))}
                      </div>
                      <button className="text-link mt-3 text-sm" onClick={() => setPage("library")}>
                        All saved investigations →
                      </button>
                    </section>
                  )}
                </aside>
              </div>
            )}
            {workflow.stage === "NEEDS_CONTEXT" && context && (
              <section className="reading-page">
                <p className="eyebrow">Research context</p>
                <h1 className="mt-4 text-3xl font-bold tracking-tight">
                  We interpreted your question as:
                </h1>
                <div className="interpretation-sheet">
                  <p className="mb-5 text-sm leading-6 text-[var(--ink-muted)]">
                    {workflow.interpretation.notice}
                  </p>
                  <dl className="space-y-5">
                    <div>
                      <dt className="text-xs font-bold text-[var(--ink-muted)]">Outcome</dt>
                      <dd className="mt-2 text-xl font-semibold">{context.requested_outcome}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-bold text-[var(--ink-muted)]">
                        Relevant processes
                      </dt>
                      <dd className="mt-2 text-sm leading-6">{context.symptom_or_process}</dd>
                    </div>
                    <div>
                      <dt className="text-xs font-bold text-[var(--ink-muted)]">
                        Primary biological context
                      </dt>
                      <dd className="mt-2 text-sm leading-6">
                        {[context.anatomical_region, context.tissue, context.activity]
                          .filter(Boolean)
                          .join(" · ") ||
                          "Not specified; source-specific context will stay visible."}
                      </dd>
                    </div>
                  </dl>
                  <button
                    className="button-quiet mt-4 px-0"
                    aria-expanded={editing}
                    onClick={() => setEditing(!editing)}
                  >
                    Edit interpretation
                  </button>
                  {editing && (
                    <div className="mt-4 grid gap-4 sm:grid-cols-2">
                      {(
                        [
                          ["requested_outcome", "Outcome"],
                          ["symptom_or_process", "Relevant processes"],
                          ["anatomical_region", "Body region"],
                          ["tissue", "Tissue"],
                          ["activity", "Activity or exposure"],
                          ["population", "Research population context"],
                        ] as const
                      ).map(([key, label]) => (
                        <label key={key}>
                          <span className="mb-1 block text-xs font-bold">{label}</span>
                          <input
                            className="field text-sm"
                            value={context[key] ?? ""}
                            onChange={(event) => update(key, event.target.value)}
                          />
                        </label>
                      ))}
                    </div>
                  )}
                  <div className="section-note mt-5">
                    <strong>Important uncertainty:</strong>{" "}
                    {context.important_uncertainty[0] ??
                      "Source relevance and biological context require review."}
                  </div>
                  {workflow.interpretation.question.question_classes.includes(
                    "symptom_mechanism",
                  ) && (
                    <p className="mt-4 text-sm leading-6">
                      This context improves research relevance but does not allow CausalBio Lab to
                      diagnose a condition.
                    </p>
                  )}
                  <div className="mt-6 flex flex-wrap gap-3">
                    <button
                      className="button-primary min-w-36"
                      disabled={
                        !context.requested_outcome?.trim() || !context.symptom_or_process?.trim()
                      }
                      onClick={() => void confirm()}
                    >
                      Continue →
                    </button>
                    <button
                      className="button-secondary"
                      onClick={() => {
                        requestVersion.current += 1;
                        setWorkflow({ stage: "EMPTY" });
                      }}
                    >
                      Edit question
                    </button>
                  </div>
                </div>
              </section>
            )}
            {workflow.stage === "BUILDING" && (
              <section role="status" className="loading-sheet">
                <p className="eyebrow">Research in progress</p>
                <h1>
                  {workflow.curated ? "Comparing possible mechanisms" : "Researching your question"}
                </h1>
                <p className="mt-4">{workflow.question}</p>
                <ul className="loading-stages">
                  <li>
                    {workflow.curated
                      ? "Reading the curated evidence"
                      : "Searching scientific sources"}
                  </li>
                  <li>Comparing related mechanisms</li>
                  <li>Retaining source context and limitations</li>
                </ul>
                <p className="mt-6 text-sm text-[var(--ink-muted)]">
                  {workflow.curated
                    ? "The comparison includes supporting and conflicting evidence."
                    : "Unavailable sources and gaps will be included in the result."}
                </p>
              </section>
            )}
            {workflow.stage === "GUIDANCE" && (
              <section className="reading-page">
                <div className="interpretation-sheet">
                  <p className="eyebrow">Research scope</p>
                  <h1 className="mt-4 text-2xl font-bold">
                    {workflow.interpretation.mode === "RESTRICTED_WITH_SAFE_ALTERNATIVE"
                      ? "I can help with the science, but not that action"
                      : workflow.interpretation.mode === "CLARIFICATION_REQUIRED"
                        ? "More information needed"
                        : "Let’s focus on a biological question"}
                  </h1>
                  <p className="mt-4 text-sm leading-7">{workflow.interpretation.notice}</p>
                  {workflow.interpretation.safe_research_question && (
                    <div className="section-note mt-5">
                      <p className="text-sm leading-7">
                        A question I can research: {workflow.interpretation.safe_research_question}
                      </p>
                      <button
                        className="button-primary mt-4"
                        onClick={() => void begin(workflow.interpretation.safe_research_question!)}
                      >
                        Investigate the biology
                      </button>
                    </div>
                  )}
                  <div className="mt-5 flex flex-wrap gap-2">
                    {workflow.interpretation.clarifications.slice(0, 3).map((item) => (
                      <button
                        key={item}
                        className="button-secondary"
                        onClick={() => void begin(item)}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                  <div className="mt-5 flex flex-wrap gap-2">
                    <button
                      className="button-secondary"
                      onClick={() => setWorkflow({ stage: "EMPTY" })}
                    >
                      Edit question
                    </button>
                    <button className="button-quiet" onClick={reset}>
                      Start over
                    </button>
                  </div>
                </div>
              </section>
            )}
            {workflow.stage === "RESEARCH_COMPLETE" && (
              <>
                <div className="mx-auto max-w-[1240px] px-4 pt-5 sm:px-7">
                  <button className="button-quiet px-0 text-xs" onClick={reset}>
                    ← New investigation
                  </button>
                  <button
                    className="button-quiet ml-3 text-xs"
                    onClick={() => {
                      setQuestion(workflow.result.interpretation.question.original_text);
                      setWorkflow({ stage: "EMPTY" });
                    }}
                  >
                    Edit question
                  </button>
                </div>
                <UniversalResultsView
                  key={workflow.result.id}
                  result={workflow.result}
                  onDeeper={() => {
                    setDepth("deep");
                    void begin(workflow.result.interpretation.question.original_text, "deep");
                  }}
                  onRetry={() =>
                    void begin(
                      workflow.result.interpretation.question.original_text,
                      workflow.result.interpretation.depth,
                    )
                  }
                />
              </>
            )}
            {workflow.stage === "COMPLETE" && (
              <>
                <div className="mx-auto max-w-[1240px] px-4 pt-5 sm:px-7">
                  <button className="button-quiet px-0 text-xs" onClick={reset}>
                    ← New investigation
                  </button>
                  <button
                    className="button-quiet ml-3 text-xs"
                    onClick={() => {
                      setQuestion(workflow.result.question.original_text);
                      setWorkflow({ stage: "EMPTY" });
                    }}
                  >
                    Edit question
                  </button>
                </div>
                <ResultsView key={workflow.result.id} result={workflow.result} />
              </>
            )}
            {workflow.stage === "FAILED" && (
              <section role="alert" className="reading-page">
                <div className="interpretation-sheet">
                  <p className="eyebrow">Research unavailable</p>
                  <h1 className="mt-4 text-2xl font-bold">{workflow.problem.title}</h1>
                  <p className="mt-4 text-sm leading-6">{workflow.problem.detail}</p>
                  <p className="mt-3 text-sm text-[var(--ink-muted)]">
                    Edit your question or choose an available example to continue.
                  </p>
                  <div className="mt-5 flex flex-wrap gap-2">
                    {workflow.problem.alternatives.slice(0, 3).map((item) => (
                      <button
                        key={item}
                        className="button-secondary"
                        onClick={() => void begin(`What mechanisms influence ${item}?`)}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                  <div className="mt-5 flex flex-wrap gap-2">
                    <button
                      className="button-primary"
                      onClick={() => {
                        setWorkflow({ stage: "EMPTY" });
                      }}
                    >
                      Edit question
                    </button>
                    <button
                      className="button-secondary"
                      onClick={() => void begin(workflow.question)}
                    >
                      Try again
                    </button>
                    <button className="button-quiet" onClick={reset}>
                      Start over
                    </button>
                  </div>
                  <details className="mt-5 text-xs">
                    <summary className="disclosure">Technical details</summary>
                    <p className="mt-2">Correlation ID: {workflow.problem.correlation_id}</p>
                  </details>
                </div>
              </section>
            )}
          </>
        )}
      </main>
      <footer className="mx-auto max-w-[1240px] border-t border-[var(--border)] px-5 py-7 text-xs leading-5 text-[var(--ink-muted)]">
        A workbench for biological research. Not diagnosis or prescribing. Read each source in
        context; curated and newly retrieved evidence have different levels of review.
      </footer>
    </div>
  );
}

function About() {
  return (
    <article className="reading-page">
      <p className="eyebrow">About the lab</p>
      <h1 className="mt-4 text-3xl font-bold">How CausalBio Lab works</h1>
      <ol className="mt-8 space-y-6">
        {[
          [
            "Interpret the biological question",
            "Identify an outcome and confirm the research context.",
          ],
          [
            "Find possible mechanisms",
            "Use a curated evidence pack or retrieve scientific sources for a provisional investigation.",
          ],
          [
            "Connect evidence into causal pathways",
            "Follow directed connections while retaining species, tissue, and study limitations.",
          ],
          [
            "Compare competing explanations",
            "Inspect contradictions, missing links, and alternative mechanisms.",
          ],
          [
            "Model selected pathways when appropriate",
            "Explore a declared mathematical model with synthetic parameters and explicit assumptions.",
          ],
        ].map(([title, detail], index) => (
          <li key={title} className="border-t border-[var(--border)] py-5">
            <h2 className="font-bold">
              {index + 1}. {title}
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">{detail}</p>
          </li>
        ))}
      </ol>
      <h2 className="mt-8 text-lg font-bold">Evidence, interpretation, and models are different</h2>
      <p className="mt-3 text-sm leading-7">
        A study supports a specific claim in a specific context. A pathway connects claims and may
        contain proposed links. A simulation shows the behavior of a mathematical model. None
        establishes what will happen to an individual.
      </p>
      <details className="surface-flat mt-6 p-5">
        <summary className="disclosure">Optional advanced analysis and methods</summary>
        <p className="mt-4 text-sm leading-7">
          The full causal graph retains provenance and evidence scoring. Pathway simulation uses
          curated Petri nets and continuous ODE models. Bayesian inference requires numerical
          observations, priors, and a likelihood; its teaching demonstration uses synthetic data
          only. Known-peptide analysis describes published records and calculated properties.
        </p>
      </details>
      <h2 className="mt-8 font-bold">Current capabilities and limitations</h2>
      <p className="mt-3 text-sm leading-7 text-[var(--ink-muted)]">
        CausalBio Lab investigates a broad range of biological questions using available curated and
        live evidence. Live research is bounded and provisional, not a comprehensive systematic
        review. Some questions have insufficient evidence. Curated examples and cached records work
        offline. Live searches send search terms to external scientific providers; local saved
        sessions and reports contain the question. Avoid identifying information. Diagnosis,
        prescribing, personal dosing, acquisition guidance, and novel peptide design are outside
        scope.
      </p>
    </article>
  );
}
