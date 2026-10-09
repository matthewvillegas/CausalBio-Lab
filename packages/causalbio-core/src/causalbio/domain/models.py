"""Pydantic models for provenance-rich biological mechanism research."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StrictBool, model_validator

from causalbio.domain.enums import (
    CausalStatus,
    CurationStatus,
    EntityType,
    EvidenceGrade,
    InferenceState,
    InterventionClass,
    InvestigationState,
    PetriArcType,
    QuerySafetyClass,
    QuestionClass,
    RateLawType,
    RelationType,
    SimulationState,
    StudyType,
)
from causalbio.domain.scoring_policy import RankingSensitivity, ScoringWeights

UnitInterval = Annotated[float, Field(ge=0.0, le=1.0)]


def utc_now() -> datetime:
    return datetime.now(UTC)


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, use_enum_values=False)


class EntityIdentifier(DomainModel):
    namespace: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=200)
    url: HttpUrl | None = None


class BiologicalEntity(DomainModel):
    id: UUID
    preferred_name: str = Field(min_length=1, max_length=200)
    aliases: tuple[str, ...] = ()
    entity_type: EntityType
    description: str = Field(min_length=1, max_length=1200)
    identifiers: tuple[EntityIdentifier, ...] = ()
    source: str = Field(min_length=1, max_length=200)
    created_at: datetime
    updated_at: datetime
    curation_status: CurationStatus


class QuestionContext(DomainModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        str_min_length=1,
        str_max_length=2000,
    )

    requested_outcome: str
    symptom_or_process: str
    anatomical_region: str | None = None
    tissue: str | None = None
    activity: str | None = None
    exposure: str | None = None
    timing: str | None = None
    duration: str | None = None
    population: str = "general research context"
    condition: str | None = None
    candidate_intervention: str | None = None
    wants_mechanisms: StrictBool = True
    wants_interventions: StrictBool = True
    important_uncertainty: tuple[str, ...] = ()


class ResearchQuestion(DomainModel):
    id: UUID
    original_text: str = Field(min_length=3, max_length=2000)
    normalized_text: str = Field(min_length=3, max_length=2000)
    question_classes: tuple[QuestionClass, ...]
    interpreted_summary: str
    context: QuestionContext
    interpretation_options: tuple[str, ...] = ()
    requires_clarification: bool = False


class StudyPopulation(DomainModel):
    description: str
    species: str
    sample_size: int | None = Field(default=None, ge=1)
    age_range: str | None = None
    relevant_condition: str | None = None


class ExperimentalContext(DomainModel):
    species: str = "not specified"
    population: str = "not specified"
    tissue: str | None = None
    cell_type: str | None = None
    condition: str | None = None
    temporal_context: str | None = None


class EffectEstimate(DomainModel):
    measure: str
    value: float
    unit: str | None = None
    interval_low: float | None = None
    interval_high: float | None = None
    interval_level: float | None = Field(default=None, gt=0, lt=1)
    source_note: str


class Study(DomainModel):
    id: UUID
    title: str
    authors: tuple[str, ...]
    publication_year: int = Field(ge=1600, le=2200)
    journal: str
    identifiers: tuple[EntityIdentifier, ...]
    study_type: StudyType
    population: StudyPopulation
    source_url: HttpUrl


class EvidenceRecord(DomainModel):
    id: UUID
    study: Study
    experimental_context: ExperimentalContext
    result_direction: Literal["supports", "contradicts", "mixed", "null", "contextualizes"]
    effect_estimate: EffectEstimate | None = None
    uncertainty_measure: str | None = None
    limitations: tuple[str, ...]
    evidence_note: str = Field(min_length=10, max_length=2000)
    supporting_excerpt: str | None = Field(default=None, max_length=500)
    retrieved_at: date
    source_adapter: str
    curation_status: CurationStatus
    evidence_grade: EvidenceGrade


class ContradictoryEvidence(DomainModel):
    evidence_id: UUID
    interpretation: str


class CausalAssertion(DomainModel):
    id: UUID
    subject_id: UUID
    relation: RelationType
    object_id: UUID
    polarity: Literal[-1, 1] = 1
    direction: Literal["directed"] = "directed"
    confidence_classification: EvidenceGrade
    causal_status: CausalStatus
    biological_context: ExperimentalContext
    supporting_evidence_ids: tuple[UUID, ...]
    contradictory_evidence_ids: tuple[UUID, ...] = ()
    curator: str
    extraction_method: Literal["manual_curation", "validated_structured_extraction"]
    source: str
    retrieval_date: date
    review_status: CurationStatus
    interpretation: str
    limitations: tuple[str, ...] = ()

    @model_validator(mode="after")
    def reject_self_edge_and_untrusted_confidence(self) -> CausalAssertion:
        if self.subject_id == self.object_id:
            raise ValueError("An assertion must connect two distinct entities")
        if not self.supporting_evidence_ids and self.review_status in {
            CurationStatus.VALIDATED,
            CurationStatus.CURATED,
        }:
            raise ValueError("Trusted assertions require supporting evidence")
        return self


class EvidenceScoreComponents(DomainModel):
    evidence_quality: UnitInterval
    causal_directness: UnitInterval
    human_relevance: UnitInterval
    replication: UnitInterval
    context_match: UnitInterval
    contradiction_penalty: UnitInterval
    extrapolation_penalty: UnitInterval


class PlausibilityScore(DomainModel):
    raw_log_support: float
    display_index: float = Field(ge=0.0, le=100.0)
    edge_components: tuple[EvidenceScoreComponents, ...]
    edge_support_values: tuple[UnitInterval, ...] = ()
    path_length_penalty: float = Field(ge=0)
    unsupported_link_penalty: float = Field(ge=0)
    explanation: tuple[str, ...]
    label: Literal["plausibility index"] = "plausibility index"
    scoring_weights: ScoringWeights = Field(default_factory=ScoringWeights)

    @model_validator(mode="after")
    def edge_support_matches_components(self) -> PlausibilityScore:
        if self.edge_support_values and len(self.edge_support_values) != len(self.edge_components):
            raise ValueError("Edge support values must align with the score components")
        return self


class MechanismPath(DomainModel):
    id: UUID
    entity_ids: tuple[UUID, ...]
    assertion_ids: tuple[UUID, ...]
    score: PlausibilityScore | None = None
    weak_link_assertion_ids: tuple[UUID, ...] = ()

    @model_validator(mode="after")
    def path_shape_is_consistent(self) -> MechanismPath:
        if len(self.entity_ids) != len(self.assertion_ids) + 1:
            raise ValueError("A mechanism path needs exactly one more entity than assertions")
        return self


class MechanisticHypothesis(DomainModel):
    id: UUID
    title: str
    plain_language_summary: str
    outcome_id: UUID
    trigger_id: UUID
    mechanism_paths: tuple[MechanismPath, ...]
    mediator_ids: tuple[UUID, ...]
    tissue_ids: tuple[UUID, ...] = ()
    cell_ids: tuple[UUID, ...] = ()
    pathway_ids: tuple[UUID, ...] = ()
    evidence_ids: tuple[UUID, ...]
    contradictory_evidence_ids: tuple[UUID, ...] = ()
    context_requirements: tuple[str, ...] = ()
    missing_links: tuple[str, ...] = ()
    uncertainty: tuple[str, ...]
    intervention_ids: tuple[UUID, ...] = ()
    evidence_label: str


class Intervention(DomainModel):
    id: UUID
    name: str
    intervention_class: InterventionClass
    description: str
    target_entity_ids: tuple[UUID, ...]
    downstream_assertion_ids: tuple[UUID, ...] = ()
    evidence_ids: tuple[UUID, ...]
    maturity: str
    addresses: Literal["cause", "mediator", "symptom", "multiple"]
    mechanistic_relevance: UnitInterval
    evidence_strength: UnitInterval
    directness: UnitInterval
    translational_maturity: UnitInterval
    uncertainty: tuple[str, ...]
    major_safety_concerns: tuple[str, ...]
    unsupported_assumptions: tuple[str, ...] = ()
    personal_recommendation: Literal[False] = False


class KnowledgeGraph(DomainModel):
    id: UUID
    version: str
    entity_ids: tuple[UUID, ...]
    assertion_ids: tuple[UUID, ...]


class GraphProjection(DomainModel):
    graph_id: UUID
    entities: tuple[BiologicalEntity, ...]
    assertions: tuple[CausalAssertion, ...]
    evidence: tuple[EvidenceRecord, ...]
    filters_applied: tuple[str, ...] = ()


class PetriPlace(DomainModel):
    id: UUID
    name: str
    description: str
    representation: str
    units: str
    compartment: str
    valid_min: float = 0.0
    valid_max: float
    initial_value: float = Field(ge=0)

    @model_validator(mode="after")
    def initial_is_in_range(self) -> PetriPlace:
        if not self.valid_min <= self.initial_value <= self.valid_max:
            raise ValueError("Initial place value is outside its declared range")
        return self


class PetriTransition(DomainModel):
    id: UUID
    name: str
    biological_event: str
    rate_law: RateLawType
    parameters: dict[str, float]
    evidence_ids: tuple[UUID, ...]
    assumptions: tuple[str, ...]


class PetriArc(DomainModel):
    id: UUID
    place_id: UUID
    transition_id: UUID
    arc_type: PetriArcType
    weight: float = Field(gt=0)
    threshold: float = Field(default=0.0, ge=0)


class PetriScenarioChange(DomainModel):
    key: str = Field(min_length=1)
    baseline: float = Field(ge=0, allow_inf_nan=False)
    at_full_strength: float = Field(ge=0, allow_inf_nan=False)


class PetriScenario(DomainModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    parameter_changes: tuple[PetriScenarioChange, ...] = ()
    initial_changes: tuple[PetriScenarioChange, ...] = ()


class PetriModel(DomainModel):
    id: UUID
    slug: str
    name: str
    description: str
    model_version: str
    places: tuple[PetriPlace, ...]
    transitions: tuple[PetriTransition, ...]
    arcs: tuple[PetriArc, ...]
    scenarios: tuple[PetriScenario, ...] = ()
    output_place_id: UUID | None = None
    curated: Literal[True] = True
    assumptions: tuple[str, ...]
    safety_label: str = "Model-based simulation, not a personalized biological prediction."

    @model_validator(mode="after")
    def validate_scenarios(self) -> PetriModel:
        if self.output_place_id is not None and self.output_place_id not in {
            place.id for place in self.places
        }:
            raise ValueError("Simulation output must reference a declared place")
        parameter_values = {
            f"{transition.name}.{key}": value
            for transition in self.transitions
            for key, value in transition.parameters.items()
        }
        places = {place.name: place for place in self.places}
        scenario_ids = [scenario.id for scenario in self.scenarios]
        if len(scenario_ids) != len(set(scenario_ids)) or "baseline" in scenario_ids:
            raise ValueError("Scenario IDs must be unique and cannot use reserved baseline")
        for scenario in self.scenarios:
            for changes in (scenario.parameter_changes, scenario.initial_changes):
                if len({change.key for change in changes}) != len(changes):
                    raise ValueError("Scenario change keys must be unique")
            for change in scenario.parameter_changes:
                if parameter_values.get(change.key) != change.baseline:
                    raise ValueError("Scenario parameter baseline must match its declared rate")
            for change in scenario.initial_changes:
                place = places.get(change.key)
                if place is None or place.initial_value != change.baseline:
                    raise ValueError("Scenario initial baseline must match a declared place")
                if not place.valid_min <= change.at_full_strength <= place.valid_max:
                    raise ValueError("Scenario initial value is outside its declared range")
        return self


class SimulationParameters(DomainModel):
    model_id: UUID
    scenario: str = "baseline"
    duration: float = Field(default=24.0, gt=0, le=1000)
    steps: int = Field(default=121, ge=3, le=5000)
    seed: int = 1729
    parameter_overrides: dict[str, float] = Field(default_factory=dict)
    initial_overrides: dict[str, float] = Field(default_factory=dict)


class SimulationRun(DomainModel):
    id: UUID
    state: SimulationState
    model_id: UUID
    parameters: SimulationParameters
    times: tuple[float, ...]
    trajectories: dict[str, tuple[float, ...]]
    transition_activity: dict[str, tuple[float, ...]]
    summary: tuple[str, ...]
    warnings: tuple[str, ...]
    software_version: str
    model_version: str


class BayesianParameter(DomainModel):
    name: str
    description: str
    units: str


class PriorSpecification(DomainModel):
    parameter: str
    distribution: str
    parameters: dict[str, float]
    provenance: str


class LikelihoodSpecification(DomainModel):
    distribution: str
    outcome: str
    parameters: dict[str, str]
    observations_description: str


class InferenceDiagnostics(DomainModel):
    r_hat_max: float | None = None
    ess_bulk_min: float | None = None
    divergences: int | None = None
    acceptance_rate: float | None = None
    energy_bfmi_min: float | None = None
    parameter_r_hat: dict[str, float] = Field(default_factory=dict)
    parameter_ess_bulk: dict[str, float] = Field(default_factory=dict)
    warnings: tuple[str, ...] = ()


class PosteriorSummary(DomainModel):
    parameter: str
    mean: float
    median: float
    interval_low: float
    interval_high: float
    interval_level: float


class SensitivityResult(DomainModel):
    parameter: str
    perturbation: str
    outcome_change: float
    interpretation: str


class HMCDemoDataset(DomainModel):
    """Numerical inputs for the bounded synthetic parameter-recovery demo."""

    id: str
    name: str
    description: str
    predictor: tuple[float, ...]
    outcome: tuple[float, ...]
    known_sigma: float = Field(gt=0)
    true_parameters: dict[str, float]
    provenance: str
    seed: int
    synthetic: Literal[True] = True

    @model_validator(mode="after")
    def validate_observations(self) -> HMCDemoDataset:
        if len(self.predictor) != len(self.outcome):
            raise ValueError("predictor and outcome must contain the same number of observations")
        if len(self.outcome) < 4:
            raise ValueError("the HMC demonstration requires at least four observations")
        return self


class HMCConfiguration(DomainModel):
    chains: int = Field(default=4, ge=2, le=8)
    warmup: int = Field(default=500, ge=100, le=5000)
    draws: int = Field(default=750, ge=100, le=5000)
    leapfrog_steps: int = Field(default=8, ge=1, le=50)
    step_size: float = Field(default=0.55, gt=0, le=1)
    seed: int = 1729


class HMCChainDiagnostics(DomainModel):
    chain: int
    acceptance_rate: float = Field(ge=0, le=1)
    divergences: int = Field(ge=0)
    energy_bfmi: float = Field(ge=0)


class PosteriorPredictiveCheck(DomainModel):
    observed_group_difference: float
    replicated_mean: float
    interval_low: float
    interval_high: float
    interval_level: float
    bayesian_p_value: float = Field(ge=0, le=1)
    interpretation: str


class ScenarioPrediction(DomainModel):
    scenario: str
    mean: float
    interval_low: float
    interval_high: float
    interval_level: float
    includes_observation_noise: bool


class HMCInferenceRun(DomainModel):
    """A reproducible result from the deliberately narrow HMC demonstration."""

    id: UUID
    state: InferenceState
    model_name: str
    model_version: str
    dataset: HMCDemoDataset
    parameters: tuple[BayesianParameter, ...]
    priors: tuple[PriorSpecification, ...]
    likelihood: LikelihoodSpecification
    configuration: HMCConfiguration
    posterior_summaries: tuple[PosteriorSummary, ...]
    diagnostics: InferenceDiagnostics
    chain_diagnostics: tuple[HMCChainDiagnostics, ...]
    posterior_draws: dict[str, tuple[tuple[float, ...], ...]]
    posterior_correlation: dict[str, dict[str, float]]
    posterior_predictive: PosteriorPredictiveCheck
    scenario_predictions: tuple[ScenarioPrediction, ...]
    sensitivity: tuple[SensitivityResult, ...]
    recovery: dict[str, bool]
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    software_version: str


class InferenceEligibility(DomainModel):
    state: InferenceState
    eligible: bool
    requirements: dict[str, bool]
    explanation: str
    no_fake_fallback: Literal[True] = True


class SafetyNotice(DomainModel):
    query_class: QuerySafetyClass
    title: str
    message: str
    restricted: bool
    urgent: bool = False
    allowed_scope: tuple[str, ...]


class ReportClaim(DomainModel):
    id: UUID
    text: str
    evidence_ids: tuple[UUID, ...]
    is_scientific_claim: bool = True


class ResearchReport(DomainModel):
    id: UUID
    investigation_id: UUID
    title: str
    sections: dict[str, str]
    claims: tuple[ReportClaim, ...]
    reference_evidence_ids: tuple[UUID, ...]
    citation_coverage: float = Field(ge=0, le=1)
    generated_at: datetime
    reproduction: dict[str, Any]


class DomainPack(DomainModel):
    slug: str
    title: str
    version: str
    description: str
    educational_notice: str
    example_questions: tuple[str, ...]
    question: ResearchQuestion
    entities: tuple[BiologicalEntity, ...]
    evidence: tuple[EvidenceRecord, ...]
    assertions: tuple[CausalAssertion, ...]
    hypotheses: tuple[MechanisticHypothesis, ...]
    interventions: tuple[Intervention, ...]
    petri_model: PetriModel | None = None


class InvestigationResult(DomainModel):
    id: UUID
    state: InvestigationState
    question: ResearchQuestion
    domain_pack: str
    graph: GraphProjection
    hypotheses: tuple[MechanisticHypothesis, ...]
    interventions: tuple[Intervention, ...]
    petri_model: PetriModel | None = None
    safety_notice: SafetyNotice
    key_findings: tuple[str, ...]
    biological_layers: tuple[str, ...]
    problem_map_paths: tuple[tuple[str, ...], ...]
    inference_eligibility: InferenceEligibility
    software_version: str
    graph_version: str
    evidence_rubric_version: str
    ranking_sensitivity: RankingSensitivity | None = None
    random_seed: int
    completed_at: datetime = Field(default_factory=utc_now)
