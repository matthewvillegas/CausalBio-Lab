"""Deterministic query-safety classification with transparent boundaries."""

from __future__ import annotations

import re

from causalbio.domain.enums import QuerySafetyClass
from causalbio.domain.models import SafetyNotice

RESEARCH_BOUNDARY = (
    "CausalBio Lab examines biological mechanisms. It does not diagnose "
    "conditions or tell individuals what treatment or substance to use."
)

_URGENT = re.compile(
    r"\b(cannot breathe|can't breathe|chest pain|unconscious|severe bleeding|suicid|"
    r"hot swollen joint|major trauma|deformity|cannot bear weight|can't bear weight)\b",
    re.IGNORECASE,
)
_DOSING = re.compile(
    r"\b(dose|dosage|how many mg|milligrams|micrograms|how much should i take|how much .{0,100} (?:should|can|do) i (?:take|use|inject))\b",
    re.I,
)
_ACQUISITION = re.compile(
    r"\b(where (?:can|do|should) i (?:buy|get|obtain|order)|where to (?:buy|get|obtain|order)|how (?:do|can) i (?:get|obtain|buy|acquire)|without a prescription|source a drug)\b",
    re.I,
)
_SYNTHESIS = re.compile(
    r"\b(synthesi[sz]e|synthesis protocol|make (?:a )?peptide|chemical recipe)\b", re.I
)
_SELF_EXPERIMENT = re.compile(
    r"\b(inject myself|self[- ]experiment|evade medical|home infusion|how (?:do|can|should) i (?:inject|administer)|how to (?:inject|administer)|(?:injection|self[- ]administration) (?:instructions|protocol|steps))\b",
    re.I,
)
_PRESCRIBING = re.compile(
    r"\b(what should i take|which drug should i use|prescribe|best medication for me)\b", re.I
)
_DIAGNOSIS = re.compile(
    r"\b(do i have|diagnose me|what condition do i have|is this cancer)\b", re.I
)
_SYMPTOM = re.compile(r"\b(pain|symptom|swelling|ache|injury|inflammation)\b", re.I)
_INTERVENTION = re.compile(
    r"\b(drug|therapy|intervention|exercise|peptide|medication|treatment)\b", re.I
)


def classify_query(text: str) -> SafetyNotice:
    """Classify a query without retaining or sending it to an external service."""

    if _URGENT.search(text):
        return SafetyNotice(
            query_class=QuerySafetyClass.URGENT_SYMPTOMS,
            title="Potentially urgent symptoms are outside this research tool",
            message=(
                "This description may include warning signs that need prompt, real-world clinical "
                "assessment. Contact local emergency services or an appropriate urgent medical "
                f"service now. {RESEARCH_BOUNDARY}"
            ),
            restricted=True,
            urgent=True,
            allowed_scope=(
                "General biological education after immediate safety needs are addressed",
            ),
        )

    restricted_patterns = (
        (
            _SELF_EXPERIMENT,
            QuerySafetyClass.DANGEROUS_SELF_EXPERIMENTATION,
            "Self-experimentation instructions",
        ),
        (_SYNTHESIS, QuerySafetyClass.SYNTHESIS, "Synthesis instructions"),
        (_ACQUISITION, QuerySafetyClass.ACQUISITION, "Substance acquisition guidance"),
        (_DOSING, QuerySafetyClass.DOSING, "Personal dosing guidance"),
        (_PRESCRIBING, QuerySafetyClass.PERSONALIZED_PRESCRIBING, "Personal treatment selection"),
        (_DIAGNOSIS, QuerySafetyClass.DIAGNOSTIC_REQUEST, "Individual diagnosis"),
    )
    for pattern, query_class, title in restricted_patterns:
        if pattern.search(text):
            # Discussing endogenous biosynthesis or a dose-response concept is ordinary biology.
            if (
                query_class == QuerySafetyClass.SYNTHESIS
                and re.search(
                    r"\b(cells?|organisms?|body|enzymes?)\s+(?:biosynthesize|synthesize)\b",
                    text,
                    re.I,
                )
                and not re.search(r"\b(i|me|my|protocol|instructions?|steps?)\b", text, re.I)
            ):
                continue
            if (
                query_class == QuerySafetyClass.DOSING
                and re.search(r"\bdose[- ]response\b", text, re.I)
                and not re.search(r"\b(i|me|my|take|inject|use)\b", text, re.I)
            ):
                continue
            return SafetyNotice(
                query_class=query_class,
                title=f"{title} is outside scope",
                message=(
                    f"CausalBio Lab cannot provide {title.casefold()}. It can describe published "
                    f"mechanisms, evidence categories, limitations, and major safety concerns. {RESEARCH_BOUNDARY}"
                ),
                restricted=True,
                allowed_scope=(
                    "Published mechanism and target information",
                    "Evidence quality and translational limitations",
                    "Major safety concerns at a general research level",
                ),
            )

    if _SYMPTOM.search(text):
        return SafetyNotice(
            query_class=QuerySafetyClass.SYMPTOM_EDUCATION,
            title="Research context, not a diagnosis",
            message=(
                "This context improves research relevance but does not allow the system to diagnose "
                "a condition. Seek professional evaluation for severe, rapidly worsening, traumatic, "
                f"or otherwise concerning symptoms. {RESEARCH_BOUNDARY}"
            ),
            restricted=False,
            allowed_scope=(
                "Educational mechanism hypotheses",
                "Evidence comparison",
                "General limitations",
            ),
        )
    if _INTERVENTION.search(text):
        return SafetyNotice(
            query_class=QuerySafetyClass.INTERVENTION_RESEARCH,
            title="Interventions are research objects",
            message=(
                "Interventions are compared by mechanism, evidence, maturity, uncertainty, and major "
                f"safety concerns—not as personal recommendations. {RESEARCH_BOUNDARY}"
            ),
            restricted=False,
            allowed_scope=("Mechanism research", "Evidence comparison", "Safety limitations"),
        )
    return SafetyNotice(
        query_class=QuerySafetyClass.GENERAL_RESEARCH,
        title="Research-oriented analysis",
        message=RESEARCH_BOUNDARY,
        restricted=False,
        allowed_scope=("Mechanism maps", "Evidence summaries", "Uncertainty analysis"),
    )
