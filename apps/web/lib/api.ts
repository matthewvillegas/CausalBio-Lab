import type {
  HMCInferenceRun,
  KnownPeptideAnalysis,
  PeptideSequenceComparison,
  InvestigationResult,
  ProblemDetail,
  ReportResponse,
  SimulationRun,
} from "@/lib/types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(public readonly problem: ProblemDetail) {
    super(problem.detail);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const fallback: ProblemDetail = {
      type: "about:blank",
      title: "Request failed",
      status: response.status,
      detail: `The research service returned ${response.status}. Check that the local API is running.`,
      correlation_id: response.headers.get("x-correlation-id") ?? "unavailable",
      alternatives: [],
    };
    let problem = fallback;
    try {
      const body: unknown = await response.json();
      if (
        typeof body === "object" &&
        body !== null &&
        "type" in body &&
        typeof body.type === "string" &&
        "title" in body &&
        typeof body.title === "string" &&
        "status" in body &&
        body.status === response.status &&
        "detail" in body &&
        typeof body.detail === "string" &&
        "correlation_id" in body &&
        typeof body.correlation_id === "string" &&
        "alternatives" in body &&
        Array.isArray(body.alternatives) &&
        body.alternatives.every((item: unknown) => typeof item === "string")
      ) {
        problem = {
          type: body.type,
          title: body.title,
          status: body.status,
          detail: body.detail,
          correlation_id: body.correlation_id,
          alternatives: body.alternatives,
        };
      }
    } catch {
      // Retain the safe fallback instead of exposing a raw response body.
    }
    throw new ApiError(problem);
  }
  return (await response.json()) as T;
}

export function interpretResearch(
  question: string,
  depth: import("./research-types").ResearchDepth = "research",
  online = true,
): Promise<import("./research-types").ResearchInterpretation> {
  return request("/api/v1/research/interpret", {
    method: "POST",
    body: JSON.stringify({ question, depth, online, context: {} }),
  });
}

export function researchQuestion(
  question: string,
  context: Record<string, string | boolean | null>,
  depth: import("./research-types").ResearchDepth,
  online: boolean,
): Promise<import("./research-types").UniversalResearchResult> {
  return request("/api/v1/research", {
    method: "POST",
    body: JSON.stringify({ question, context, depth, online }),
  });
}

export function researchStatus(): Promise<import("./research-types").ResearchServiceStatus> {
  return request("/api/v1/research/status");
}

export function researchSessions(): Promise<import("./research-types").ResearchSession[]> {
  return request("/api/v1/research/sessions");
}

export function loadResearchSession(
  id: string,
): Promise<import("./research-types").UniversalResearchResult> {
  return request(`/api/v1/research/${encodeURIComponent(id)}`);
}

export function createInvestigation(
  question: string,
  context: Record<string, string | boolean | null>,
): Promise<InvestigationResult> {
  return request("/api/v1/investigations", {
    method: "POST",
    body: JSON.stringify({ question, context }),
  });
}

export function simulate(
  modelId: string,
  scenario: string,
  parameterOverrides: Record<string, number>,
  initialOverrides: Record<string, number>,
): Promise<SimulationRun> {
  return request("/api/v1/petri/simulate", {
    method: "POST",
    body: JSON.stringify({
      model_id: modelId,
      scenario,
      duration: 24,
      steps: 121,
      seed: 1729,
      parameter_overrides: parameterOverrides,
      initial_overrides: initialOverrides,
    }),
  });
}

export function generateReport(investigationId: string): Promise<ReportResponse> {
  return request("/api/v1/reports", {
    method: "POST",
    body: JSON.stringify({ investigation_id: investigationId, persist_artifacts: true }),
  });
}

export function runHMCDemo(): Promise<HMCInferenceRun> {
  return request("/api/v1/bayes/demo/run", {
    method: "POST",
    body: JSON.stringify({
      chains: 4,
      warmup: 500,
      draws: 750,
      leapfrog_steps: 8,
      step_size: 0.55,
      seed: 1729,
    }),
  });
}

export function analyzeKnownPeptide(slug: string, ph: number): Promise<KnownPeptideAnalysis> {
  return request(`/api/v1/peptides/known/${encodeURIComponent(slug)}/analysis?pH=${ph}`);
}

export function compareKnownPeptides(
  slugA: string,
  slugB: string,
): Promise<PeptideSequenceComparison> {
  return request(
    `/api/v1/peptides/compare/${encodeURIComponent(slugA)}/${encodeURIComponent(slugB)}`,
  );
}
