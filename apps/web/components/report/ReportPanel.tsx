"use client";

import { useEffect, useState } from "react";

import { API_URL, ApiError, generateReport } from "@/lib/api";
import type { InvestigationResult, ProblemDetail, ReportResponse } from "@/lib/types";

type ReportWorkflow =
  | { state: "READY" }
  | { state: "GENERATING" }
  | { state: "COMPLETE"; response: ReportResponse }
  | { state: "FAILED"; problem: ProblemDetail };

type CachedReport = { request: Promise<ReportResponse>; response?: ReportResponse };
// Session-only cache survives tab remounts. A new completed investigation gets a new key.
const reports = new Map<string, CachedReport>();

function requestReport(key: string, investigationId: string): Promise<ReportResponse> {
  const cached = reports.get(key);
  if (cached) return cached.request;
  const entry: CachedReport = {
    request: generateReport(investigationId).then(
      (response) => {
        entry.response = response;
        return response;
      },
      (error: unknown) => {
        reports.delete(key);
        throw error;
      },
    ),
  };
  reports.set(key, entry);
  if (reports.size > 24) {
    const completedKey = [...reports].find(([, report]) => report.response)?.[0];
    if (completedKey) reports.delete(completedKey);
  }
  return entry.request;
}

function reportError(error: unknown): ReportWorkflow {
  return {
    state: "FAILED",
    problem:
      error instanceof ApiError
        ? error.problem
        : {
            type: "about:blank",
            title: "We could not prepare your report",
            status: 0,
            detail:
              "Your investigation is still available. Check that the local research service is running, then retry the report.",
            correlation_id: "unavailable",
            alternatives: [],
          },
  };
}

export function ReportPanel({ result }: { result: InvestigationResult }) {
  const cacheKey = `${result.id}:${result.completed_at}:${result.graph_version}:${result.evidence_rubric_version}`;
  return <ReportContent key={cacheKey} result={result} cacheKey={cacheKey} />;
}

function ReportContent({ result, cacheKey }: { result: InvestigationResult; cacheKey: string }) {
  const [workflow, setWorkflow] = useState<ReportWorkflow>(() => {
    const cached = reports.get(cacheKey);
    return cached?.response
      ? { state: "COMPLETE", response: cached.response }
      : { state: cached ? "GENERATING" : "READY" };
  });

  useEffect(() => {
    const cached = reports.get(cacheKey);
    if (!cached || cached.response) return;
    let active = true;
    void cached.request.then(
      (response) => active && setWorkflow({ state: "COMPLETE", response }),
      (error: unknown) => active && setWorkflow(reportError(error)),
    );
    return () => {
      active = false;
    };
  }, [cacheKey]);

  async function create() {
    setWorkflow({ state: "GENERATING" });
    try {
      const response = await requestReport(cacheKey, result.id);
      setWorkflow({ state: "COMPLETE", response });
    } catch (error) {
      setWorkflow(reportError(error));
    }
  }

  const response = workflow.state === "COMPLETE" ? workflow.response : null;
  const readable = response?.artifacts.filter((item) =>
    ["report.html", "report.md"].includes(item.filename),
  );
  const technical = response?.artifacts.filter(
    (item) => !["report.html", "report.md"].includes(item.filename),
  );

  return (
    <section id="panel-report" aria-labelledby="report-heading" className="max-w-4xl">
      <p className="eyebrow">Report and source records</p>
      <h2 id="report-heading" className="mt-2">
        Research summary
      </h2>
      <p className="mt-4 text-sm leading-6 text-[var(--ink-muted)]">
        Save the question, mechanisms, evidence, and unresolved questions. The report includes
        sources and a reproducibility appendix.
      </p>
      <div className="mt-5 border-y border-[var(--border)] py-5">
        <h3 className="font-bold">Your question</h3>
        <p className="mt-2 text-sm leading-6">{result.question.original_text}</p>
        <p className="mt-3 text-sm text-[var(--ink-muted)]">
          {result.hypotheses.length} possible mechanisms · {result.graph.evidence.length} source
          records · supporting and conflicting findings
        </p>
      </div>
      <ul className="mt-5 list-disc space-y-1 pl-5 text-sm" aria-label="Report contents">
        {[
          "Question and top mechanisms",
          "Strongest evidence and its context",
          "Biggest uncertainties and conflicting findings",
          "Intervention research and key limitations",
        ].map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>

      {workflow.state === "READY" ? (
        <button type="button" className="button-primary mt-6" onClick={() => void create()}>
          Generate research report
        </button>
      ) : null}
      {workflow.state === "GENERATING" ? (
        <p className="mt-6 text-sm" role="status">
          Preparing your summary and checking its source links…
        </p>
      ) : null}
      {workflow.state === "FAILED" ? (
        <div role="alert" className="mt-6 border-l-2 border-[var(--red)] pl-4">
          <h3 className="font-bold">We could not prepare your report</h3>
          <p className="mt-2 text-sm leading-6">{workflow.problem.detail}</p>
          <p className="mt-2 text-sm">
            Your investigation remains available. Retry when the local research service is ready.
          </p>
          <button type="button" className="button-secondary mt-4" onClick={() => void create()}>
            Retry report
          </button>
          <details className="mt-4 text-xs">
            <summary>Technical details</summary>
            <p className="mt-2 break-all">
              {workflow.problem.title} · Reference: {workflow.problem.correlation_id}
            </p>
          </details>
        </div>
      ) : null}
      {response ? (
        <div className="mt-6 border-t border-[var(--border)] pt-5">
          <h3 className="font-extrabold" role="status">
            Your research report is ready
          </h3>
          <p className="mt-2 text-sm leading-6">
            The HTML report opens in a browser. Its technical appendix is collapsed until you choose
            to read it.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            {readable?.map((artifact) => (
              <a
                key={artifact.filename}
                className={
                  artifact.filename === "report.html" ? "button-primary" : "text-link self-center"
                }
                href={`${API_URL}${artifact.download_url}`}
                target={artifact.filename === "report.html" ? "_blank" : undefined}
                rel={artifact.filename === "report.html" ? "noopener noreferrer" : undefined}
              >
                {artifact.filename === "report.html"
                  ? "Read HTML report"
                  : "Download Markdown report"}
              </a>
            ))}
          </div>
        </div>
      ) : null}

      <p className="mt-5 text-sm leading-6 text-[var(--ink-muted)]">
        This report describes research, not a diagnosis or personal treatment advice. It includes
        model availability and assumptions; simulation runs and the separate uncertainty
        demonstration are not included as biological findings.
      </p>

      <details className="mt-6 border-t border-[var(--border)] pt-5">
        <summary className="cursor-pointer font-bold">Reproducibility and data exports</summary>
        <dl className="metadata mt-4">
          <dt>Software version</dt>
          <dd className="break-all font-mono">{result.software_version}</dd>
          <dt>Graph version</dt>
          <dd className="break-all font-mono">{result.graph_version}</dd>
          <dt>Evidence rubric</dt>
          <dd className="break-all font-mono">{result.evidence_rubric_version}</dd>
          <dt>Random seed</dt>
          <dd className="font-mono">{result.random_seed}</dd>
        </dl>
        <p className="mt-4 text-xs leading-5 text-[var(--ink-muted)]">
          {result.petri_model
            ? "An executable pathway model is included in the data exports."
            : "This evidence pack has no executable pathway model to export."}{" "}
          Each scientific report claim must link to a source in this investigation. A source link
          does not establish that a claim is valid.
        </p>
        {response ? (
          <>
            <p className="mt-4 text-xs">
              Source-link coverage: {Math.round(response.citation_coverage * 100)}%
            </p>
            <p className="mt-2 break-all font-mono text-xs">Report ID: {response.report_id}</p>
            <div className="mt-4 flex flex-wrap gap-x-6 gap-y-3">
              {technical?.map((artifact) => (
                <a
                  key={artifact.filename}
                  className="text-link break-all text-sm"
                  href={`${API_URL}${artifact.download_url}`}
                >
                  {artifact.format} ↓
                </a>
              ))}
            </div>
          </>
        ) : (
          <p className="mt-4 text-xs">Prepare the report to download the underlying data.</p>
        )}
      </details>
    </section>
  );
}
