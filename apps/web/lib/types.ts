export type UUID = string;

export type EntityType =
  | "cognitive_outcome"
  | "symptom"
  | "phenotype"
  | "disease_or_condition"
  | "anatomical_region"
  | "organ"
  | "tissue"
  | "cell_type"
  | "cellular_component"
  | "gene"
  | "rna"
  | "protein"
  | "receptor"
  | "enzyme"
  | "ion_channel"
  | "pathway"
  | "biological_process"
  | "metabolite"
  | "neurotransmitter"
  | "hormone"
  | "immune_mediator"
  | "biomechanical_force"
  | "behavior"
  | "environmental_exposure"
  | "drug"
  | "peptide"
  | "experimental_compound"
  | "therapy"
  | "device"
  | "study"
  | "dataset";

export interface EntityIdentifier {
  namespace: string;
  value: string;
  url: string | null;
}

export interface BiologicalEntity {
  id: UUID;
  preferred_name: string;
  aliases: string[];
  entity_type: EntityType;
  description: string;
  identifiers: EntityIdentifier[];
  source: string;
  created_at: string;
  updated_at: string;
  curation_status: string;
}

export interface QuestionContext {
  requested_outcome: string;
  symptom_or_process: string;
  anatomical_region: string | null;
  tissue: string | null;
  activity: string | null;
  exposure: string | null;
  timing: string | null;
  duration: string | null;
  population: string;
  condition: string | null;
  candidate_intervention: string | null;
  wants_mechanisms: boolean;
  wants_interventions: boolean;
  important_uncertainty: string[];
}

export interface ResearchQuestion {
  id: UUID;
  original_text: string;
  normalized_text: string;
  question_classes: string[];
  interpreted_summary: string;
  context: QuestionContext;
  interpretation_options: string[];
  requires_clarification: boolean;
}

export interface Study {
  id: UUID;
  title: string;
  authors: string[];
  publication_year: number;
  journal: string;
  identifiers: EntityIdentifier[];
  study_type: string;
  population: {
    description: string;
    species: string;
    sample_size: number | null;
    age_range: string | null;
    relevant_condition: string | null;
  };
  source_url: string;
}

export interface EvidenceRecord {
  id: UUID;
  study: Study;
  experimental_context: {
    species: string;
    population: string;
    tissue: string | null;
    cell_type: string | null;
    condition: string | null;
    temporal_context: string | null;
  };
  result_direction: "supports" | "contradicts" | "mixed" | "null" | "contextualizes";
  effect_estimate: {
    measure: string;
    value: number;
    unit: string | null;
    interval_low: number | null;
    interval_high: number | null;
    interval_level: number | null;
    source_note: string;
  } | null;
  uncertainty_measure: string | null;
  limitations: string[];
  evidence_note: string;
  retrieved_at: string;
  source_adapter: string;
  curation_status: string;
  evidence_grade: "A" | "B" | "C" | "D" | "E" | "U";
}

export interface CausalAssertion {
  id: UUID;
  subject_id: UUID;
  relation: string;
  object_id: UUID;
  polarity: -1 | 1;
  direction: "directed";
  confidence_classification: "A" | "B" | "C" | "D" | "E" | "U";
  causal_status: string;
  biological_context: EvidenceRecord["experimental_context"];
  supporting_evidence_ids: UUID[];
  contradictory_evidence_ids: UUID[];
  curator: string;
  extraction_method: string;
  source: string;
  retrieval_date: string;
  review_status: string;
  interpretation: string;
  limitations: string[];
}

export interface EvidenceScoreComponents {
  evidence_quality: number;
  causal_directness: number;
  human_relevance: number;
  replication: number;
  context_match: number;
  contradiction_penalty: number;
  extrapolation_penalty: number;
}

export interface MechanismPath {
  id: UUID;
  entity_ids: UUID[];
  assertion_ids: UUID[];
  score: {
    raw_log_support: number;
    display_index: number;
    edge_components: EvidenceScoreComponents[];
    edge_support_values?: number[];
    path_length_penalty: number;
    unsupported_link_penalty: number;
    explanation: string[];
    label: "plausibility index";
    scoring_weights?: Record<string, number>;
  } | null;
  weak_link_assertion_ids: UUID[];
}

export interface MechanisticHypothesis {
  id: UUID;
  title: string;
  plain_language_summary: string;
  outcome_id: UUID;
  trigger_id: UUID;
  mechanism_paths: MechanismPath[];
  mediator_ids: UUID[];
  tissue_ids: UUID[];
  cell_ids: UUID[];
  pathway_ids: UUID[];
  evidence_ids: UUID[];
  contradictory_evidence_ids: UUID[];
  context_requirements: string[];
  missing_links: string[];
  uncertainty: string[];
  intervention_ids: UUID[];
  evidence_label: string;
}

export interface Intervention {
  id: UUID;
  name: string;
  intervention_class: string;
  description: string;
  target_entity_ids: UUID[];
  downstream_assertion_ids: UUID[];
  evidence_ids: UUID[];
  maturity: string;
  addresses: "cause" | "mediator" | "symptom" | "multiple";
  mechanistic_relevance: number;
  evidence_strength: number;
  directness: number;
  translational_maturity: number;
  uncertainty: string[];
  major_safety_concerns: string[];
  unsupported_assumptions: string[];
  personal_recommendation: false;
}

export interface PetriPlace {
  id: UUID;
  name: string;
  description: string;
  representation: string;
  units: string;
  compartment: string;
  valid_min: number;
  valid_max: number;
  initial_value: number;
}

export interface PetriTransition {
  id: UUID;
  name: string;
  biological_event: string;
  rate_law: string;
  parameters: Record<string, number>;
  evidence_ids: UUID[];
  assumptions: string[];
}

export interface PetriScenarioChange {
  key: string;
  baseline: number;
  at_full_strength: number;
}

export interface PetriScenario {
  id: string;
  label: string;
  description: string;
  parameter_changes: PetriScenarioChange[];
  initial_changes: PetriScenarioChange[];
}

export interface PetriModel {
  id: UUID;
  slug: string;
  name: string;
  description: string;
  model_version: string;
  places: PetriPlace[];
  transitions: PetriTransition[];
  scenarios: PetriScenario[];
  output_place_id: UUID | null;
  arcs: Array<{
    id: UUID;
    place_id: UUID;
    transition_id: UUID;
    arc_type: string;
    weight: number;
    threshold: number;
  }>;
  curated: true;
  assumptions: string[];
  safety_label: string;
}

export interface SafetyNotice {
  query_class: string;
  title: string;
  message: string;
  restricted: boolean;
  urgent: boolean;
  allowed_scope: string[];
}

export interface InvestigationResult {
  id: UUID;
  state: string;
  question: ResearchQuestion;
  domain_pack: string;
  graph: {
    graph_id: UUID;
    entities: BiologicalEntity[];
    assertions: CausalAssertion[];
    evidence: EvidenceRecord[];
    filters_applied: string[];
  };
  hypotheses: MechanisticHypothesis[];
  interventions: Intervention[];
  petri_model: PetriModel | null;
  safety_notice: SafetyNotice;
  key_findings: string[];
  biological_layers: string[];
  problem_map_paths: string[][];
  inference_eligibility: {
    state: string;
    eligible: boolean;
    requirements: Record<string, boolean>;
    explanation: string;
    no_fake_fallback: true;
  };
  software_version: string;
  graph_version: string;
  evidence_rubric_version: string;
  ranking_sensitivity?: {
    relative_change: number;
    tested_configurations: number;
    changed_configurations: number;
    stable: boolean;
    ranks: { hypothesis_id: UUID; baseline_rank: number; best_rank: number; worst_rank: number }[];
    method: string;
    limitation: string;
  } | null;
  random_seed: number;
  completed_at: string;
}

export interface InterpretationResponse {
  domain_pack: string;
  question: ResearchQuestion;
  safety_notice: SafetyNotice;
}

export interface SimulationRun {
  id: UUID;
  state: string;
  model_id: UUID;
  parameters: {
    model_id: UUID;
    scenario: string;
    duration: number;
    steps: number;
    seed: number;
    parameter_overrides: Record<string, number>;
    initial_overrides: Record<string, number>;
  };
  times: number[];
  trajectories: Record<UUID, number[]>;
  transition_activity: Record<UUID, number[]>;
  summary: string[];
  warnings: string[];
  software_version: string;
  model_version: string;
}

export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
  correlation_id: string;
  alternatives: string[];
}

export interface ReportResponse {
  report_id: UUID;
  citation_coverage: number;
  artifacts: Array<{
    format: string;
    filename: string;
    media_type: string;
    download_url: string;
  }>;
}

export interface HMCInferenceRun {
  id: UUID;
  state: "COMPLETE" | "DIAGNOSTIC_WARNING" | "FAILED";
  model_name: string;
  model_version: string;
  dataset: {
    id: string;
    name: string;
    description: string;
    predictor: number[];
    outcome: number[];
    known_sigma: number;
    true_parameters: Record<string, number>;
    provenance: string;
    seed: number;
    synthetic: true;
  };
  parameters: Array<{ name: string; description: string; units: string }>;
  priors: Array<{
    parameter: string;
    distribution: string;
    parameters: Record<string, number>;
    provenance: string;
  }>;
  likelihood: {
    distribution: string;
    outcome: string;
    parameters: Record<string, string>;
    observations_description: string;
  };
  configuration: {
    chains: number;
    warmup: number;
    draws: number;
    leapfrog_steps: number;
    step_size: number;
    seed: number;
  };
  posterior_summaries: Array<{
    parameter: string;
    mean: number;
    median: number;
    interval_low: number;
    interval_high: number;
    interval_level: number;
  }>;
  diagnostics: {
    r_hat_max: number | null;
    ess_bulk_min: number | null;
    divergences: number | null;
    acceptance_rate: number | null;
    energy_bfmi_min: number | null;
    parameter_r_hat: Record<string, number>;
    parameter_ess_bulk: Record<string, number>;
    warnings: string[];
  };
  chain_diagnostics: Array<{
    chain: number;
    acceptance_rate: number;
    divergences: number;
    energy_bfmi: number;
  }>;
  posterior_draws: Record<string, number[][]>;
  posterior_correlation: Record<string, Record<string, number>>;
  posterior_predictive: {
    observed_group_difference: number;
    replicated_mean: number;
    interval_low: number;
    interval_high: number;
    interval_level: number;
    bayesian_p_value: number;
    interpretation: string;
  };
  scenario_predictions: Array<{
    scenario: string;
    mean: number;
    interval_low: number;
    interval_high: number;
    interval_level: number;
    includes_observation_noise: boolean;
  }>;
  sensitivity: Array<{
    parameter: string;
    perturbation: string;
    outcome_change: number;
    interpretation: string;
  }>;
  recovery: Record<string, boolean>;
  assumptions: string[];
  limitations: string[];
  software_version: string;
}

export interface KnownPeptideAnalysis {
  peptide: {
    slug: string;
    name: string;
    sequence: string;
    organism: string;
    precursor: string;
    precursor_uniprot: string;
    source_url: string;
    terminal_modifications: string[];
    known_targets: Array<{
      name: string;
      identifier: string;
      relationship: string;
      source_url: string;
    }>;
    reported_biological_context: string[];
    available_structures: Array<{
      identifier: string;
      description: string;
      source_url: string;
    }>;
    evidence_stage: string;
    measured_properties: Record<string, number | string>;
    annotation_limitations: string[];
  };
  measured_properties: Record<string, number | string>;
  calculated_properties: {
    sequence_length: number;
    amino_acid_composition: {
      counts: Record<string, number>;
      fractions: Record<string, number>;
    };
    approximate_molecular_weight_da: number;
    estimated_net_charge: number;
    charge_pH: number;
    estimated_isoelectric_point: number | null;
    mean_kyte_doolittle_hydrophobicity: number;
    signed_charge_density: number;
    absolute_charge_density: number;
    alpha_helix_hydrophobic_moment: number;
    beta_strand_hydrophobic_moment: number;
    normalized_sequence_entropy: number;
  };
  database_annotations: Record<string, unknown>;
  model_predictions: {
    amphipathicity_indicator: "low" | "moderate" | "high";
    rule: string;
    unsupported_activity_prediction: false;
  };
  unsupported_assumptions: string[];
  calculation_notes: string[];
  safety_notice: string;
}

export interface PeptideSequenceComparison {
  peptide_a: string;
  peptide_b: string;
  aligned_a: string;
  aligned_b: string;
  sequence_identity: number;
  conserved_positions: Array<{
    peptide_a_position: number;
    peptide_b_position: number;
    residue: string;
  }>;
  scoring: Record<string, number>;
  interpretation: string;
}
