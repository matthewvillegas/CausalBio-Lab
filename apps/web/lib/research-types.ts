import type { InvestigationResult, ResearchQuestion, SafetyNotice } from "@/lib/types";

export type ResearchDepth = "quick" | "research" | "deep";
export type ResearchMode =
  | "CURATED"
  | "LIVE_RESEARCH"
  | "GENERAL_EVIDENCE_SUMMARY"
  | "EXPLANATORY"
  | "CLARIFICATION_REQUIRED"
  | "RESTRICTED_WITH_SAFE_ALTERNATIVE"
  | "OUT_OF_DOMAIN"
  | "ERROR";

export interface ResearchInterpretation {
  mode: ResearchMode;
  question: ResearchQuestion;
  domain_pack: string | null;
  depth: ResearchDepth;
  entities: {
    name: string;
    entity_type: string;
    aliases: string[];
    identifiers: Record<string, string>;
  }[];
  search_queries: string[];
  clarifications: string[];
  safe_research_question: string | null;
  notice: string;
  safety_notice: SafetyNotice;
}

export interface ResearchEvidence {
  id: string;
  source: string;
  source_record_id: string;
  title: string;
  authors: string[];
  year: number | null;
  doi: string | null;
  pmid: string | null;
  source_url: string;
  abstract: string | null;
  organism: string | null;
  population: string | null;
  tissue: string | null;
  cell_type: string | null;
  study_type: string | null;
  primary_or_review: "primary" | "review" | "unspecified";
  experimental_context: string | null;
  annotation_evidence?: {
    evidence_code?: string | null;
    source?: string | null;
    identifier?: string | null;
  }[];
  result_direction: "supports" | "contradicts" | "mixed" | "contextualizes" | "unspecified";
  effect_estimate: string | null;
  sample_size: number | null;
  limitations: string[];
  retrieved_at: string;
  cache_status: "fetched" | "fresh_cache" | "stale_cache" | "local_curated";
  evidence_status: "provisional" | "curated";
}

export interface ResearchClaim {
  id: string;
  text: string;
  evidence_ids: string[];
  kind: "source_extract" | "curated_summary" | "structured_annotation";
  source_passage: string | null;
  relation: "ASSOCIATED_WITH" | "SUPPORTED_BY" | "CONTRADICTED_BY" | "PARTICIPATES_IN";
  uncertainty: string;
}

export interface ResearchMechanism {
  id: string;
  title: string;
  description: string;
  claims: ResearchClaim[];
  uncertainties: string[];
  evidence_dimensions: Record<string, string>;
  model_eligibility:
    | "GRAPH_ONLY"
    | "QUALITATIVE_MODEL_AVAILABLE"
    | "PETRI_MODEL_AVAILABLE"
    | "ODE_MODEL_AVAILABLE"
    | "BAYESIAN_MODEL_AVAILABLE";
}

export interface UniversalResearchResult {
  id: string;
  mode: ResearchMode;
  interpretation: ResearchInterpretation;
  direct_answer: ResearchClaim[];
  mechanisms: ResearchMechanism[];
  evidence: ResearchEvidence[];
  graph: {
    nodes: { id: string; name: string; entity_type: string; identifiers: Record<string, string> }[];
    edges: {
      id: string;
      subject_id: string;
      object_id: string;
      relation: ResearchClaim["relation"];
      claim_id: string | null;
      evidence_ids: string[];
      status: "provisional";
    }[];
    notice: string;
  };
  complications: ResearchClaim[];
  modifiers: ResearchClaim[];
  source_runs: {
    source: string;
    provider_version?: string | null;
    query: string;
    status: "available" | "cached" | "unavailable" | "offline";
    record_count: number;
    retrieved_at: string | null;
    detail: string | null;
  }[];
  limitations: string[];
  notices: string[];
  created_at: string;
  curated_result: InvestigationResult | null;
  saved_locally: boolean;
  synthesis_method: string;
}

export interface ResearchServiceStatus {
  live_enabled: boolean;
  status_label: string;
  sources: string[];
}

export interface ResearchSession {
  id: string;
  question: string;
  mode: ResearchMode;
  created_at: string;
}
