"""Evidence-linked research reports and safe in-memory renderers.

The reporting layer deliberately does not perform literature synthesis, simulation,
or statistical inference.  It renders only the curated objects already present in an
``InvestigationResult`` and fails closed when a scientific claim lacks graph-local
evidence.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from html import escape
from typing import Final
from uuid import UUID

from causalbio.domain.identifiers import stable_uuid
from causalbio.domain.models import (
    BiologicalEntity,
    CausalAssertion,
    EvidenceRecord,
    InvestigationResult,
    MechanismPath,
    ReportClaim,
    ResearchReport,
)

REPORT_GENERATOR_VERSION: Final = "2.0.0"

SUMMARY_SECTIONS: Final[tuple[str, ...]] = (
    "Question",
    "Top mechanisms",
    "Strongest evidence",
    "Biggest uncertainties",
    "Intervention research",
    "Key limitations",
)

REQUIRED_REPORT_SECTIONS: Final[tuple[str, ...]] = (
    *SUMMARY_SECTIONS,
    "Research question",
    "Interpreted context",
    "Scope and exclusions",
    "Biological decomposition",
    "Competing hypotheses",
    "Causal mechanism paths",
    "Supporting evidence",
    "Contradictory evidence",
    "Intervention classes",
    "Evidence-plausibility scoring",
    "Petri-net model",
    "Simulation results",
    "Bayesian model",
    "Posterior diagnostics",
    "Sensitivity analysis",
    "Translation barriers",
    "Safety considerations",
    "Unknowns and research gaps",
    "Limitations",
    "Reproduction information",
    "References",
)


class ReportValidationError(ValueError):
    """Raised when report claims or references break provenance invariants."""


def _ordered_unique(values: Iterable[UUID]) -> tuple[UUID, ...]:
    return tuple(dict.fromkeys(values))


def _single_line(value: object) -> str:
    return " ".join(str(value).split())


def _bullets(items: Iterable[str], *, empty: str) -> str:
    materialized = tuple(item for item in items if item)
    if not materialized:
        return empty
    return "\n".join(f"- {item}" for item in materialized)


def _display_value(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw).replace("_", " ")


def validate_claim_evidence(
    claims: Iterable[ReportClaim], investigation: InvestigationResult
) -> float:
    """Validate scientific claim citations against the investigation graph.

    Every scientific claim must cite at least one evidence record, and every cited
    identifier (including optional citations on non-scientific claims) must exist in
    ``investigation.graph.evidence``.  The returned value is the resulting citation
    coverage fraction.  An empty scientific-claim set is vacuously fully covered.
    """

    materialized = tuple(claims)
    available = {record.id for record in investigation.graph.evidence}
    errors: list[str] = []
    scientific_count = 0
    covered_count = 0

    claim_ids = [claim.id for claim in materialized]
    if len(set(claim_ids)) != len(claim_ids):
        errors.append("Report claim identifiers must be unique")

    for claim in materialized:
        unknown = set(claim.evidence_ids) - available
        if unknown:
            rendered = ", ".join(sorted(str(item) for item in unknown))
            errors.append(f"Claim {claim.id} cites evidence absent from the graph: {rendered}")

        if not claim.is_scientific_claim:
            continue

        scientific_count += 1
        if not claim.evidence_ids:
            errors.append(f"Scientific claim {claim.id} has no evidence IDs")
        elif not unknown:
            covered_count += 1

    if errors:
        raise ReportValidationError("; ".join(errors))
    if scientific_count == 0:
        return 1.0
    return covered_count / scientific_count


def validate_report(report: ResearchReport, investigation: InvestigationResult) -> float:
    """Validate report completeness, provenance, reference index, and coverage."""

    errors: list[str] = []
    if report.investigation_id != investigation.id:
        errors.append("Report investigation ID does not match the supplied investigation")

    missing_sections = [name for name in REQUIRED_REPORT_SECTIONS if name not in report.sections]
    if missing_sections:
        errors.append("Report is missing required sections: " + ", ".join(missing_sections))
    empty_sections = [
        name for name in REQUIRED_REPORT_SECTIONS if not report.sections.get(name, "").strip()
    ]
    if empty_sections:
        errors.append("Report has empty required sections: " + ", ".join(empty_sections))

    available = {record.id for record in investigation.graph.evidence}
    unknown_references = set(report.reference_evidence_ids) - available
    if unknown_references:
        rendered = ", ".join(sorted(str(item) for item in unknown_references))
        errors.append(f"Reference index contains evidence absent from the graph: {rendered}")

    try:
        coverage = validate_claim_evidence(report.claims, investigation)
    except ReportValidationError as exc:
        errors.append(str(exc))
        coverage = 0.0

    indexed = set(report.reference_evidence_ids)
    cited = {evidence_id for claim in report.claims for evidence_id in claim.evidence_ids}
    missing_from_index = cited - indexed
    if missing_from_index:
        rendered = ", ".join(sorted(str(item) for item in missing_from_index))
        errors.append(f"Cited evidence is missing from the reference index: {rendered}")

    if abs(report.citation_coverage - coverage) > 1e-12:
        errors.append(
            "Stored citation coverage does not match validated coverage "
            f"({report.citation_coverage:.6f} != {coverage:.6f})"
        )

    if errors:
        raise ReportValidationError("; ".join(errors))
    return coverage


class ReportGenerator:
    """Generate complete reports without inventing absent analyses or results."""

    version = REPORT_GENERATOR_VERSION

    def generate(self, investigation: InvestigationResult) -> ResearchReport:
        entity_lookup = {entity.id: entity for entity in investigation.graph.entities}
        assertion_lookup = {assertion.id: assertion for assertion in investigation.graph.assertions}
        citation_labels = {
            record.id: f"E{index}"
            for index, record in enumerate(investigation.graph.evidence, start=1)
        }

        assertion_claims: dict[UUID, ReportClaim] = {}
        hypothesis_claims: dict[UUID, ReportClaim] = {}
        intervention_claims: dict[UUID, ReportClaim] = {}
        claims: list[ReportClaim] = []

        for assertion in investigation.graph.assertions:
            subject = entity_lookup[assertion.subject_id].preferred_name
            object_name = entity_lookup[assertion.object_id].preferred_name
            relation = assertion.relation.value.lower().replace("_", " ")
            if assertion.polarity < 0:
                relation = f"negatively {relation}"
            text = _single_line(f"{subject} {relation} {object_name}. {assertion.interpretation}")
            claim = self._claim(
                investigation,
                kind="assertion",
                source_id=assertion.id,
                text=text,
                evidence_ids=_ordered_unique(
                    (*assertion.supporting_evidence_ids, *assertion.contradictory_evidence_ids)
                ),
            )
            assertion_claims[assertion.id] = claim
            claims.append(claim)

        for hypothesis in investigation.hypotheses:
            claim = self._claim(
                investigation,
                kind="hypothesis",
                source_id=hypothesis.id,
                text=_single_line(hypothesis.plain_language_summary),
                evidence_ids=_ordered_unique(
                    (*hypothesis.evidence_ids, *hypothesis.contradictory_evidence_ids)
                ),
            )
            hypothesis_claims[hypothesis.id] = claim
            claims.append(claim)

        for intervention in investigation.interventions:
            claim = self._claim(
                investigation,
                kind="intervention",
                source_id=intervention.id,
                text=_single_line(f"{intervention.name}: {intervention.description}"),
                evidence_ids=_ordered_unique(intervention.evidence_ids),
            )
            intervention_claims[intervention.id] = claim
            claims.append(claim)

        for record in investigation.graph.evidence:
            claim = self._claim(
                investigation,
                kind="evidence-note",
                source_id=record.id,
                text=_single_line(record.evidence_note),
                evidence_ids=(record.id,),
            )
            claims.append(claim)

        citation_coverage = validate_claim_evidence(claims, investigation)
        cited_ids = {evidence_id for claim in claims for evidence_id in claim.evidence_ids}
        reference_ids = tuple(
            record.id for record in investigation.graph.evidence if record.id in cited_ids
        )
        generated_at = datetime.now(UTC)
        reproduction: dict[str, object] = {
            "software_version": investigation.software_version,
            "graph_version": investigation.graph_version,
            "evidence_rubric_version": investigation.evidence_rubric_version,
            "random_seed": investigation.random_seed,
            "domain_pack": investigation.domain_pack,
            "investigation_state": investigation.state.value,
            "investigation_completed_at": investigation.completed_at.isoformat(),
            "report_generator_version": self.version,
            "ranking_sensitivity": (
                investigation.ranking_sensitivity.model_dump(mode="json")
                if investigation.ranking_sensitivity
                else None
            ),
        }

        sections = self._sections(
            investigation,
            generated_at=generated_at,
            entity_lookup=entity_lookup,
            assertion_lookup=assertion_lookup,
            citation_labels=citation_labels,
            assertion_claims=assertion_claims,
            hypothesis_claims=hypothesis_claims,
            intervention_claims=intervention_claims,
            reproduction=reproduction,
        )
        report = ResearchReport(
            id=stable_uuid("research-report", str(investigation.id)),
            investigation_id=investigation.id,
            title="Research summary",
            sections=sections,
            claims=tuple(claims),
            reference_evidence_ids=reference_ids,
            citation_coverage=citation_coverage,
            generated_at=generated_at,
            reproduction=reproduction,
        )
        validate_report(report, investigation)
        return report

    @staticmethod
    def _claim(
        investigation: InvestigationResult,
        *,
        kind: str,
        source_id: UUID,
        text: str,
        evidence_ids: tuple[UUID, ...],
    ) -> ReportClaim:
        return ReportClaim(
            id=stable_uuid("report-claim", f"{investigation.id}:{kind}:{source_id}"),
            text=text,
            evidence_ids=evidence_ids,
        )

    def _sections(
        self,
        investigation: InvestigationResult,
        *,
        generated_at: datetime,
        entity_lookup: dict[UUID, BiologicalEntity],
        assertion_lookup: dict[UUID, CausalAssertion],
        citation_labels: dict[UUID, str],
        assertion_claims: dict[UUID, ReportClaim],
        hypothesis_claims: dict[UUID, ReportClaim],
        intervention_claims: dict[UUID, ReportClaim],
        reproduction: dict[str, object],
    ) -> dict[str, str]:
        question = investigation.question
        context = question.context
        context_items = (
            ("Requested outcome", context.requested_outcome),
            ("Symptom or process", context.symptom_or_process),
            ("Anatomical region", context.anatomical_region),
            ("Tissue", context.tissue),
            ("Activity", context.activity),
            ("Exposure", context.exposure),
            ("Timing", context.timing),
            ("Duration", context.duration),
            ("Population", context.population),
            ("Condition", context.condition),
            ("Candidate intervention", context.candidate_intervention),
        )
        interpreted_context = _bullets(
            (
                f"{label}: {_single_line(value)}"
                for label, value in context_items
                if value is not None and str(value).strip()
            ),
            empty="No structured context was available.",
        )
        if context.important_uncertainty:
            interpreted_context += "\n- Important uncertainty: " + "; ".join(
                _single_line(item) for item in context.important_uncertainty
            )

        path_lines: list[str] = []
        causal_path_lines: list[str] = []
        scoring_lines: list[str] = []
        for hypothesis in investigation.hypotheses:
            for index, path in enumerate(hypothesis.mechanism_paths, start=1):
                names = [
                    _single_line(entity_lookup[item].preferred_name) for item in path.entity_ids
                ]
                path_evidence = self._path_evidence(path, assertion_claims)
                marker = self._citation_marker(path_evidence, citation_labels)
                path_lines.append(
                    f"{hypothesis.title}, path {index}: {' → '.join(names)}. {marker}"
                )
                relations = " → ".join(
                    assertion_lookup[item].relation.value for item in path.assertion_ids
                )
                score = (
                    f"{path.score.display_index:.1f}/100 plausibility index"
                    if path.score is not None
                    else "not scored"
                )
                weak = (
                    f"{len(path.weak_link_assertion_ids)} weak link(s) flagged"
                    if path.weak_link_assertion_ids
                    else "no sub-threshold links flagged by the current rubric"
                )
                causal_path_lines.append(
                    f"{hypothesis.title}, path {index}: {' → '.join(names)}; "
                    f"relations: {relations}; {score}; {weak}. {marker}"
                )
                if path.score is not None:
                    scoring_lines.append(
                        f"{hypothesis.title}, path {index}: "
                        f"{path.score.display_index:.1f}/100. "
                        + " ".join(_single_line(item) for item in path.score.explanation)
                        + " Policy weights: "
                        + path.score.scoring_weights.model_dump_json()
                    )

        hypothesis_lines: list[str] = []
        summary_mechanisms: list[str] = []
        summary_uncertainties: list[str] = []
        gap_lines: list[str] = []
        for hypothesis in investigation.hypotheses:
            claim = hypothesis_claims[hypothesis.id]
            marker = self._citation_marker(claim.evidence_ids, citation_labels)
            summary_mechanisms.append(
                f"{hypothesis.title} — {hypothesis.evidence_label}. {claim.text} {marker}"
            )
            summary_uncertainties.append(
                f"{hypothesis.title}: "
                + "; ".join(
                    _single_line(item)
                    for item in (*hypothesis.uncertainty[:1], *hypothesis.missing_links[:1])
                )
                + f" {marker}"
            )
            best_score = max(
                (
                    path.score.display_index
                    for path in hypothesis.mechanism_paths
                    if path.score is not None
                ),
                default=None,
            )
            score_text = (
                f"best path {best_score:.1f}/100" if best_score is not None else "paths not scored"
            )
            hypothesis_lines.append(
                f"{hypothesis.title} ({hypothesis.evidence_label}; {score_text}): "
                f"{claim.text} {marker} Main uncertainty: "
                + "; ".join(_single_line(item) for item in hypothesis.uncertainty)
            )
            for item in hypothesis.missing_links:
                gap_lines.append(f"{hypothesis.title}: {_single_line(item)} {marker}")
            for item in hypothesis.uncertainty:
                gap_lines.append(f"{hypothesis.title}: {_single_line(item)} {marker}")

        supporting_lines: list[str] = []
        contradictory_ids = {
            evidence_id
            for assertion in investigation.graph.assertions
            for evidence_id in assertion.contradictory_evidence_ids
        } | {
            evidence_id
            for hypothesis in investigation.hypotheses
            for evidence_id in hypothesis.contradictory_evidence_ids
        }
        contradictory_ids |= {
            record.id
            for record in investigation.graph.evidence
            if record.result_direction in {"contradicts", "null"}
        }
        contradictory_lines: list[str] = []
        translation_lines: list[str] = []
        for record in investigation.graph.evidence:
            label = citation_labels[record.id]
            summary = self._evidence_summary(record, label)
            if record.id in contradictory_ids:
                contradictory_lines.append(summary)
            else:
                supporting_lines.append(summary)
            limitations = "; ".join(_single_line(item) for item in record.limitations)
            population = record.study.population
            translation_lines.append(
                f"[{label}] {population.species}; {_single_line(population.description)}. "
                f"Translation limits: {limitations or 'No additional limitation was recorded.'}"
            )

        intervention_groups: dict[str, list[str]] = {}
        safety_lines: list[str] = []
        for intervention in investigation.interventions:
            claim = intervention_claims[intervention.id]
            marker = self._citation_marker(claim.evidence_ids, citation_labels)
            group = _display_value(intervention.intervention_class)
            intervention_groups.setdefault(group, []).append(
                f"{claim.text} Research maturity: {_single_line(intervention.maturity)}; "
                f"addresses: {intervention.addresses}; this is not a personal recommendation. "
                f"{marker}"
            )
            concerns = "; ".join(_single_line(item) for item in intervention.major_safety_concerns)
            if not concerns:
                concerns = (
                    "No specific concern was recorded in the pack; absence of a listed concern "
                    "is not evidence of safety."
                )
            safety_lines.append(f"{intervention.name}: {concerns} {marker}")
        intervention_text = "\n".join(
            f"- {group}:\n" + "\n".join(f"  - {item}" for item in items)
            for group, items in intervention_groups.items()
        )
        if not intervention_text:
            intervention_text = "No intervention research objects were included."

        model = investigation.petri_model
        petri_text = (
            "\n".join(
                (
                    f"A curated executable model is available: {model.name} "
                    f"(model version {model.model_version}).",
                    _single_line(model.description),
                    f"Structure: {len(model.places)} places, {len(model.transitions)} transitions, "
                    f"and {len(model.arcs)} arcs.",
                    "No simulation run is embedded in this investigation, so the model description "
                    "must not be read as a simulated result or a prediction for a person.",
                    _bullets(
                        (_single_line(item) for item in model.assumptions),
                        empty="No model assumptions were supplied.",
                    ),
                )
            )
            if model is not None
            else (
                "This evidence pack does not include an executable pathway model. "
                "Its biological connections can still be explored through the evidence."
            )
        )

        eligibility = investigation.inference_eligibility
        bayesian_requirements = _bullets(
            (
                f"{name.replace('_', ' ')}: {'available' if met else 'not available'}"
                for name, met in eligibility.requirements.items()
            ),
            empty="No eligibility requirements were recorded.",
        )

        reference_lines = [
            self._reference_entry(record, citation_labels[record.id])
            for record in investigation.graph.evidence
        ]
        reproduction_lines = [
            f"{key.replace('_', ' ')}: {_single_line(value)}" for key, value in reproduction.items()
        ]
        reproduction_lines.append(f"report generated at: {generated_at.isoformat()}")
        reproduction_lines.append(
            f"scientific-claim citation coverage: {len(assertion_claims) + len(hypothesis_claims) + len(intervention_claims) + len(investigation.graph.evidence)} "
            "claims linked to evidence records; citation presence does not establish claim validity"
        )

        grade_order = {grade: index for index, grade in enumerate(("A", "B", "C", "D", "E", "U"))}
        strongest_records = sorted(
            (
                record
                for record in investigation.graph.evidence
                if record.id not in contradictory_ids
            ),
            key=lambda record: grade_order[record.evidence_grade.value],
        )[:3]
        strongest_summary = _bullets(
            (
                f"[{citation_labels[record.id]}] {record.study.title}: {record.evidence_note} "
                f"Context: {record.experimental_context.species}; "
                f"{record.experimental_context.tissue or 'tissue not recorded'}. "
                f"Limitation: {record.limitations[0] if record.limitations else 'No limitation recorded; this does not imply complete evidence.'}"
                for record in strongest_records
            ),
            empty="No supporting study was available in this evidence pack.",
        )
        conflicting_summary = _bullets(
            (
                f"[{citation_labels[record.id]}] {_single_line(record.evidence_note)} "
                f"Context: {record.experimental_context.species}; "
                f"{record.experimental_context.tissue or 'tissue not recorded'}."
                for record in investigation.graph.evidence
                if record.id in contradictory_ids
            ),
            empty=(
                "No contradictory or null findings were bundled. This does not establish "
                "that no conflicting evidence exists."
            ),
        )
        summary_interventions = _bullets(
            (
                f"{_display_value(item.intervention_class)} — {item.name}. "
                f"Targets: {', '.join(entity_lookup[target].preferred_name for target in item.target_entity_ids)}. "
                f"{'Symptom-focused' if item.addresses == 'symptom' else 'Mechanism-focused' if item.addresses in {'cause', 'mediator'} else 'Multiple pathway levels'}. "
                f"Evidence maturity: {item.maturity}. "
                f"Main uncertainty: {item.uncertainty[0] if item.uncertainty else 'Not recorded'}. "
                f"{self._citation_marker(item.evidence_ids, citation_labels)}"
                for item in investigation.interventions
            ),
            empty="No intervention research is included in this evidence pack.",
        )

        return {
            "Question": _single_line(question.original_text),
            "Top mechanisms": _bullets(
                summary_mechanisms,
                empty="No possible mechanism was identified in the available evidence.",
            ),
            "Strongest evidence": (
                "Selected supporting records with the highest curated evidence grades in this pack. "
                "Strength remains specific to the study's species, tissue, and measured outcome.\n"
                + strongest_summary
            ),
            "Biggest uncertainties": (
                (
                    "Mechanism order changes under modest evidence-weight changes; compare the paths and their weak links.\n\n"
                    if investigation.ranking_sensitivity
                    and not investigation.ranking_sensitivity.stable
                    else ""
                )
                + _bullets(
                    summary_uncertainties,
                    empty="No mechanism-specific uncertainty was recorded; the evidence may still be incomplete.",
                )
                + "\n\nWhat argues against this?\n"
                + conflicting_summary
            ),
            "Intervention research": (
                "These are research objects, not personal recommendations.\n"
                + summary_interventions
            ),
            "Key limitations": _bullets(
                (
                    "This is a small curated evidence pack, not a systematic review or a diagnosis.",
                    "A plausible biological connection does not establish a benefit or predict an individual's outcome.",
                    "Animal and cellular findings retain their original context; human relevance must be assessed separately.",
                    "The summary contains no fitted biological treatment effects or completed simulation results.",
                    "Full study details and reproducibility information remain available in the research appendix.",
                ),
                empty="No limitations recorded.",
            ),
            "Research question": "\n".join(
                (
                    f"Original question: {_single_line(question.original_text)}",
                    f"Interpreted question: {_single_line(question.interpreted_summary)}",
                    f"Investigation state: {investigation.state.value}.",
                )
            ),
            "Interpreted context": interpreted_context,
            "Scope and exclusions": "\n".join(
                (
                    "This is a curated, educational mechanism report. It is not a diagnosis, "
                    "personal treatment plan, or estimate of what will happen to an individual.",
                    "A mechanism graph is not automatically a statistically identified causal model. "
                    "Association, prediction, expert curation, and causal experiments retain their "
                    "distinct labels.",
                    f"Safety boundary: {_single_line(investigation.safety_notice.message)}",
                )
            ),
            "Biological decomposition": "\n".join(
                (
                    "Biological layers considered:",
                    _bullets(
                        (_single_line(item) for item in investigation.biological_layers),
                        empty="No biological layers were recorded.",
                    ),
                    "Evidence-linked problem-map paths:",
                    _bullets(path_lines, empty="No connected mechanism path was available."),
                )
            ),
            "Competing hypotheses": _bullets(
                hypothesis_lines, empty="No competing hypotheses were generated."
            ),
            "Causal mechanism paths": _bullets(
                causal_path_lines, empty="No evidence-linked causal path was available."
            ),
            "Supporting evidence": _bullets(
                supporting_lines,
                empty="No supporting evidence records were present in the investigation graph.",
            ),
            "Contradictory evidence": _bullets(
                contradictory_lines,
                empty=(
                    "No explicitly curated contradictory or null evidence record was present. "
                    "This means none was bundled, not that none exists."
                ),
            ),
            "Intervention classes": "\n".join(
                (
                    "Interventions are research objects, grouped rather than prescribed or personally ranked.",
                    intervention_text,
                )
            ),
            "Evidence-plausibility scoring": "\n".join(
                (
                    "The plausibility index is a transparent heuristic comparison of evidence "
                    "structure. It is not a probability, causal effect estimate, or clinical score.",
                    _bullets(scoring_lines, empty="No scored mechanism paths were available."),
                )
            ),
            "Petri-net model": petri_text,
            "Simulation results": (
                "Unavailable — InvestigationResult contains no SimulationRun. No baseline, modified "
                "scenario, trajectory, or simulated biological effect is reported."
            ),
            "Bayesian model": "\n".join(
                (
                    f"Unavailable — {_single_line(eligibility.explanation)}",
                    "No priors, likelihood, fitted parameters, or posterior probabilities are reported.",
                    bayesian_requirements,
                )
            ),
            "Posterior diagnostics": (
                "Unavailable — Bayesian sampling was not performed, so there are no R-hat, effective "
                "sample size, divergence, or posterior-predictive diagnostics to report."
            ),
            "Sensitivity analysis": (
                (
                    f"Evidence ranking: {investigation.ranking_sensitivity.changed_configurations} of "
                    f"{investigation.ranking_sensitivity.tested_configurations} one-weight-at-a-time "
                    f"configurations changed ranks at ±{investigation.ranking_sensitivity.relative_change:.0%}. "
                    f"{investigation.ranking_sensitivity.limitation}\n\n"
                    if investigation.ranking_sensitivity
                    else "Evidence ranking sensitivity was not assessed.\n\n"
                )
                + "Unavailable for numerical models — neither a completed inference result nor a simulation run with "
                "parameter perturbations is present in this investigation."
            ),
            "Translation barriers": _bullets(
                translation_lines,
                empty="No evidence-specific translation information was available.",
            ),
            "Safety considerations": "\n".join(
                (
                    f"{investigation.safety_notice.title}: "
                    f"{_single_line(investigation.safety_notice.message)}",
                    "The report does not provide dosing, acquisition, administration, synthesis, "
                    "or individualized treatment instructions.",
                    _bullets(
                        safety_lines,
                        empty="No intervention-specific safety notes were bundled.",
                    ),
                )
            ),
            "Unknowns and research gaps": _bullets(
                gap_lines,
                empty=(
                    "No explicit gap was recorded. This should not be interpreted as a complete "
                    "evidence base."
                ),
            ),
            "Limitations": _bullets(
                (
                    "The bundled literature is curated for an offline educational demonstration and is not comprehensive.",
                    "Mechanism paths combine context-specific assertions and do not identify a causal DAG or an individual counterfactual effect.",
                    "Plausibility scores are heuristic indices, not posterior probabilities.",
                    (
                        "The Petri model is a simplified executable abstraction; no simulation result is included here."
                        if model is not None
                        else "This evidence pack has no executable pathway model or simulation results."
                    ),
                    "No Bayesian inference was performed because the required numerical data and model specification are absent.",
                    "Evidence limitations and contradictory findings are retained in their dedicated sections.",
                ),
                empty="No limitations were recorded.",
            ),
            "Reproduction information": _bullets(
                reproduction_lines, empty="Reproduction metadata was unavailable."
            ),
            "References": _bullets(
                reference_lines,
                empty="No evidence records were cited because the graph contained none.",
            ),
        }

    @staticmethod
    def _path_evidence(
        path: MechanismPath, assertion_claims: dict[UUID, ReportClaim]
    ) -> tuple[UUID, ...]:
        return _ordered_unique(
            evidence_id
            for assertion_id in path.assertion_ids
            for evidence_id in assertion_claims[assertion_id].evidence_ids
        )

    @staticmethod
    def _citation_marker(evidence_ids: Sequence[UUID], citation_labels: dict[UUID, str]) -> str:
        if not evidence_ids:
            return "[no evidence linked]"
        return "[" + ", ".join(citation_labels[item] for item in evidence_ids) + "]"

    @staticmethod
    def _evidence_summary(record: EvidenceRecord, label: str) -> str:
        population = record.study.population
        sample = (
            f"n={population.sample_size}"
            if population.sample_size is not None
            else "sample size not reported in the bundled record"
        )
        limitations = "; ".join(_single_line(item) for item in record.limitations)
        return (
            f"[{label}] {record.study.title} ({record.study.publication_year}, "
            f"{record.study.journal}). {_display_value(record.study.study_type)}; "
            f"{population.species}; {_single_line(population.description)}; {sample}. "
            f"Direction: {record.result_direction}. {_single_line(record.evidence_note)} "
            f"Limitations: {limitations or 'none recorded in the bundled record.'}"
        )

    @staticmethod
    def _reference_entry(record: EvidenceRecord, label: str) -> str:
        authors = ", ".join(_single_line(item) for item in record.study.authors)
        identifiers = "; ".join(
            f"{_single_line(item.namespace).upper()}: {_single_line(item.value)}"
            for item in record.study.identifiers
        )
        return (
            f"[{label}] {authors} ({record.study.publication_year}). "
            f"{_single_line(record.study.title)}. {_single_line(record.study.journal)}. "
            f"{identifiers or 'No DOI or PMID was bundled.'} "
            f"Source: {record.study.source_url}. Retrieved {record.retrieved_at.isoformat()} "
            f"via {_single_line(record.source_adapter)}."
        )

    def render_markdown(self, report: ResearchReport) -> str:
        """Render a report as Markdown without writing an artifact file."""

        lines = [f"# {_escape_markdown_html(report.title)}"]
        appendix_started = False
        for name, content in report.sections.items():
            if name not in SUMMARY_SECTIONS and not appendix_started:
                lines.extend(("", "## Research and reproducibility appendix"))
                appendix_started = True
            heading = "###" if appendix_started else "##"
            lines.extend(
                (
                    "",
                    f"{heading} {_escape_markdown_html(name)}",
                    "",
                    _escape_markdown_html(content),
                )
            )
        return "\n".join(lines).rstrip() + "\n"

    def render_html(self, report: ResearchReport) -> str:
        """Render escaped, script-free, standalone HTML with a restrictive CSP."""

        summary_sections: list[str] = []
        appendix_sections: list[str] = []
        for index, (name, content) in enumerate(report.sections.items(), start=1):
            rendered = "\n".join(
                (
                    f'<section id="section-{index}">',
                    f"<h2>{escape(name)}</h2>",
                    _section_html(content),
                    "</section>",
                )
            )
            if name in SUMMARY_SECTIONS:
                summary_sections.append(rendered)
            else:
                appendix_sections.append(rendered)
        summary = "\n".join(summary_sections)
        appendix = "\n".join(appendix_sections)
        return (
            "<!doctype html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<meta http-equiv="Content-Security-Policy" '
            "content=\"default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; "
            "base-uri 'none'; form-action 'none'\">\n"
            f"<title>{escape(report.title)}</title>\n"
            "<style>"
            "*{box-sizing:border-box}body{margin:0;background:#f6f4ef;color:#20201d;"
            "font:16px/1.75 'Segoe UI',Arial,sans-serif}"
            "main{max-width:900px;margin:0 auto;padding:3rem 2rem;overflow-wrap:anywhere}"
            "header{margin-bottom:2rem}"
            "section{border-top:1px solid #d8d4cb;padding-top:1.5rem;margin-top:2rem}"
            "h1,h2{font-family:Georgia,serif;font-weight:400;line-height:1.2;letter-spacing:-.02em}"
            "h1{font-size:2.5rem;margin-top:0}h2{font-size:1.75rem}"
            "li{margin:.5rem 0}.meta{color:#68665f}a{color:#24483c;text-underline-offset:3px}"
            "summary{cursor:pointer;font-weight:600;padding:1rem 0}"
            "summary:focus-visible,a:focus-visible{outline:2px solid #24483c;outline-offset:4px}"
            "pre,code{font-family:Consolas,monospace}pre{overflow:auto}"
            "@media(max-width:600px){main{padding:2rem 1.25rem}h1{font-size:2rem}}"
            "@media(prefers-color-scheme:dark){body{background:#22231f;color:#eeeae0}"
            "header,section{border-color:#484a40}.meta{color:#bbb7aa}a{color:#c7d8cb}"
            "summary:focus-visible,a:focus-visible{outline-color:#c7d8cb}}"
            "@media print{body{background:white;color:#20201d}main{max-width:none;padding:0}"
            "h1,h2{break-after:avoid}a,.meta{color:inherit}}"
            "</style>\n"
            "</head>\n"
            "<body>\n"
            "<main>\n"
            "<header>"
            f"<h1>{escape(report.title)}</h1>"
            '<p class="meta">Possible mechanisms, supporting evidence, and unresolved questions.</p>'
            "</header>\n"
            f"{summary}\n"
            '<details class="appendix">\n'
            "<summary>Research and reproducibility appendix</summary>\n"
            f"{appendix}\n"
            "</details>\n"
            "</main>\n"
            "</body>\n"
            "</html>\n"
        )

    def to_markdown(self, report: ResearchReport) -> str:
        """Alias for :meth:`render_markdown`."""

        return self.render_markdown(report)

    def to_html(self, report: ResearchReport) -> str:
        """Alias for :meth:`render_html`."""

        return self.render_html(report)

    @staticmethod
    def validate(report: ResearchReport, investigation: InvestigationResult) -> float:
        return validate_report(report, investigation)


def _escape_markdown_html(value: str) -> str:
    """Prevent raw HTML execution while retaining generated Markdown structure."""

    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _section_html(value: str) -> str:
    """Render a deliberately small, fully escaped Markdown-like subset."""

    output: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{escape(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            output.append(
                "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in list_items) + "</ul>"
            )
            list_items.clear()

    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            flush_list()
            continue
        if line.startswith("- "):
            flush_paragraph()
            list_items.append(line[2:].strip())
            continue
        flush_list()
        paragraph.append(line)

    flush_paragraph()
    flush_list()
    return "\n".join(output)


def generate_report(investigation: InvestigationResult) -> ResearchReport:
    """Convenience wrapper around :class:`ReportGenerator`."""

    return ReportGenerator().generate(investigation)


def render_markdown(report: ResearchReport) -> str:
    return ReportGenerator().render_markdown(report)


def render_html(report: ResearchReport) -> str:
    return ReportGenerator().render_html(report)


def generate_markdown(investigation: InvestigationResult) -> str:
    return render_markdown(generate_report(investigation))


def generate_html(investigation: InvestigationResult) -> str:
    return render_html(generate_report(investigation))
