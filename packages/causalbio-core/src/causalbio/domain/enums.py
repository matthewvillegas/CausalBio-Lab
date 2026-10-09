"""Controlled vocabularies used across the scientific core."""

from enum import StrEnum


class EntityType(StrEnum):
    COGNITIVE_OUTCOME = "cognitive_outcome"
    SYMPTOM = "symptom"
    PHENOTYPE = "phenotype"
    DISEASE_OR_CONDITION = "disease_or_condition"
    ANATOMICAL_REGION = "anatomical_region"
    ORGAN = "organ"
    TISSUE = "tissue"
    CELL_TYPE = "cell_type"
    CELLULAR_COMPONENT = "cellular_component"
    GENE = "gene"
    RNA = "rna"
    PROTEIN = "protein"
    RECEPTOR = "receptor"
    ENZYME = "enzyme"
    ION_CHANNEL = "ion_channel"
    PATHWAY = "pathway"
    BIOLOGICAL_PROCESS = "biological_process"
    METABOLITE = "metabolite"
    NEUROTRANSMITTER = "neurotransmitter"
    HORMONE = "hormone"
    IMMUNE_MEDIATOR = "immune_mediator"
    BIOMECHANICAL_FORCE = "biomechanical_force"
    BEHAVIOR = "behavior"
    ENVIRONMENTAL_EXPOSURE = "environmental_exposure"
    DRUG = "drug"
    PEPTIDE = "peptide"
    EXPERIMENTAL_COMPOUND = "experimental_compound"
    THERAPY = "therapy"
    DEVICE = "device"
    STUDY = "study"
    DATASET = "dataset"


class RelationType(StrEnum):
    ACTIVATES = "ACTIVATES"
    INHIBITS = "INHIBITS"
    BINDS_TO = "BINDS_TO"
    PHOSPHORYLATES = "PHOSPHORYLATES"
    EXPRESSED_IN = "EXPRESSED_IN"
    LOCATED_IN = "LOCATED_IN"
    PARTICIPATES_IN = "PARTICIPATES_IN"
    PRODUCES = "PRODUCES"
    CONSUMES = "CONSUMES"
    REQUIRES = "REQUIRES"
    UPREGULATES = "UPREGULATES"
    DOWNREGULATES = "DOWNREGULATES"
    INCREASES = "INCREASES"
    DECREASES = "DECREASES"
    CAUSES = "CAUSES"
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    MEDIATES = "MEDIATES"
    MODERATES = "MODERATES"
    PRECEDES = "PRECEDES"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    PREDICTED_TO_AFFECT = "PREDICTED_TO_AFFECT"
    TREATS = "TREATS"
    REDUCES_SYMPTOM = "REDUCES_SYMPTOM"
    AFFECTS_RISK = "AFFECTS_RISK"
    METABOLIZED_BY = "METABOLIZED_BY"
    TRANSPORTED_BY = "TRANSPORTED_BY"
    SUPPORTED_BY = "SUPPORTED_BY"
    CONTRADICTED_BY = "CONTRADICTED_BY"
    DERIVED_FROM = "DERIVED_FROM"


class CausalStatus(StrEnum):
    CAUSAL_EXPERIMENTAL = "causal_experimental"
    QUASI_EXPERIMENTAL = "quasi_experimental"
    LONGITUDINAL_ASSOCIATION = "longitudinal_association"
    CROSS_SECTIONAL_ASSOCIATION = "cross_sectional_association"
    MECHANISTIC_BIOCHEMICAL = "mechanistic_biochemical"
    GENETIC_EVIDENCE = "genetic_evidence"
    COMPUTATIONAL_PREDICTION = "computational_prediction"
    EXPERT_CURATION = "expert_curation"
    HYPOTHESIS_ONLY = "hypothesis_only"


class CurationStatus(StrEnum):
    SUGGESTED = "SUGGESTED"
    EXTRACTED = "EXTRACTED"
    VALIDATED = "VALIDATED"
    CURATED = "CURATED"
    REJECTED = "REJECTED"
    OUTDATED = "OUTDATED"


class EvidenceGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    U = "U"


class StudyType(StrEnum):
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"
    RANDOMIZED_TRIAL = "randomized_trial"
    CONTROLLED_EXPERIMENT = "controlled_experiment"
    COHORT = "cohort"
    CROSS_SECTIONAL = "cross_sectional"
    CASE_CONTROL = "case_control"
    ANIMAL_EXPERIMENT = "animal_experiment"
    CELL_EXPERIMENT = "cell_experiment"
    MECHANISTIC_REVIEW = "mechanistic_review"
    COMPUTATIONAL = "computational"
    OTHER = "other"


class InterventionClass(StrEnum):
    BEHAVIOR = "behavior"
    PHYSICAL_OR_MECHANICAL = "physical_or_mechanical"
    REHABILITATION_CONCEPT = "rehabilitation_concept"
    APPROVED_THERAPY = "approved_therapy"
    APPROVED_DRUG = "approved_drug"
    KNOWN_PEPTIDE = "known_peptide"
    EXPERIMENTAL_COMPOUND = "experimental_compound"
    BIOLOGICAL_THERAPY = "biological_therapy"
    DEVICE = "device"
    ENVIRONMENTAL_MODIFICATION = "environmental_modification"


class QuestionClass(StrEnum):
    SYMPTOM_MECHANISM = "symptom_mechanism"
    BIOLOGICAL_PROCESS = "biological_process"
    PERFORMANCE_GOAL = "performance_goal"
    DISEASE_MECHANISM = "disease_mechanism"
    INTERVENTION_MECHANISM = "intervention_mechanism"
    COMPARATIVE_INTERVENTION = "comparative_intervention"
    PATHWAY = "pathway"
    GENE_OR_PROTEIN = "gene_or_protein"
    PEPTIDE = "peptide"
    LITERATURE_REVIEW = "literature_review"


class QuerySafetyClass(StrEnum):
    GENERAL_RESEARCH = "general_biological_research"
    SYMPTOM_EDUCATION = "symptom_education"
    INTERVENTION_RESEARCH = "intervention_mechanism_research"
    DIAGNOSTIC_REQUEST = "diagnostic_request"
    PERSONALIZED_PRESCRIBING = "personalized_prescribing_request"
    DOSING = "dosing_request"
    ACQUISITION = "substance_acquisition_request"
    SYNTHESIS = "synthesis_request"
    DANGEROUS_SELF_EXPERIMENTATION = "dangerous_self_experimentation_request"
    URGENT_SYMPTOMS = "urgent_symptom_description"


class InvestigationState(StrEnum):
    EMPTY = "EMPTY"
    INTERPRETING = "INTERPRETING"
    CONTEXT_REQUIRED = "CONTEXT_REQUIRED"
    READY = "READY"
    BUILDING_GRAPH = "BUILDING_GRAPH"
    RETRIEVING_EVIDENCE = "RETRIEVING_EVIDENCE"
    RANKING_HYPOTHESES = "RANKING_HYPOTHESES"
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    STALE = "STALE"


class SimulationState(StrEnum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class InferenceState(StrEnum):
    INELIGIBLE = "INELIGIBLE"
    READY = "READY"
    SAMPLING = "SAMPLING"
    DIAGNOSTIC_WARNING = "DIAGNOSTIC_WARNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class PetriArcType(StrEnum):
    INPUT = "input"
    OUTPUT = "output"
    INHIBITORY = "inhibitory"
    READ = "read"


class RateLawType(StrEnum):
    MASS_ACTION = "mass_action"
    CONSTANT = "constant"
    HILL_ACTIVATION = "hill_activation"
    HILL_INHIBITION = "hill_inhibition"
