"""Choose the best available research route without claiming universal coverage."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

from causalbio.demo.registry import DomainPackRegistry
from causalbio.domain.enums import QuestionClass
from causalbio.domain.identifiers import stable_uuid
from causalbio.domain.models import QuestionContext, ResearchQuestion
from causalbio.questions.interpreter import (
    AmbiguousQuestionError,
    EmptyQuestionError,
    UnsupportedQuestionError,
    interpret_question,
    normalize_question,
)
from causalbio.research.models import (
    EntityHint,
    ResearchDepth,
    ResearchInterpretation,
    ResearchMode,
)
from causalbio.safety.classifier import classify_query

# These are lexical entity aliases and search cues, not claims or a hidden evidence pack.
ENTITY_ALIASES: tuple[EntityHint, ...] = (
    EntityHint(
        name="BDNF",
        entity_type="protein",
        aliases=("brain-derived neurotrophic factor",),
        identifiers={"UniProtKB": "P23560"},
    ),
    EntityHint(name="NTRK2", entity_type="receptor", aliases=("TrkB",)),
    EntityHint(name="MTOR", entity_type="protein", aliases=("mTOR",)),
    EntityHint(name="COL1A1", entity_type="gene", aliases=("collagen type I alpha 1",)),
    EntityHint(name="Substance P", entity_type="peptide", aliases=("substance-p",)),
    EntityHint(name="BPC-157", entity_type="peptide", aliases=("BPC 157",)),
    EntityHint(name="GLP-1", entity_type="peptide", aliases=("glucagon-like peptide 1",)),
    *(
        EntityHint(name=name, entity_type=kind)
        for name, kind in (
            ("dopamine", "neurotransmitter"),
            ("selegiline", "drug"),
            ("metformin", "drug"),
            ("caffeine", "compound"),
            ("creatine", "metabolite"),
            ("insulin", "hormone"),
            ("tendon", "tissue"),
            ("cartilage", "tissue"),
            ("collagen", "protein"),
            ("muscle", "tissue"),
            ("skin", "tissue"),
            ("acne", "condition"),
            ("wound healing", "biological_process"),
            ("mechanotransduction", "biological_process"),
        )
    ),
)
_BIOLOGY = re.compile(
    r"\b(biolog\w*|biochem\w*|cell\w*|gene\w*|protein\w*|receptor\w*|pathway\w*|enzyme\w*|hormone\w*|peptide\w*|drug\w*|compound\w*|tissue\w*|organ\w*|disease\w*|symptom\w*|pain|swelling|inflamm\w*|neuro\w*|immune\w*|metabol\w*|muscle\w*|hypertrophy|wound\w*|heal\w*|recovery|tendon\w*|cartilage|collagen|insulin|sleep|memory|motivation|dopamine|caffeine|creatine|acne|metformin|selegiline|sensitivity|ATP|BDNF|GLP.?1|COL1A1|MTOR|mechanotransduction)\b",
    re.I,
)
_NONBIOLOGY = re.compile(
    r"\b(stock price|javascript|write code|bitcoin|weather|football|data retention|computer memory|database|recipe for dinner)\b",
    re.I,
)
_QUESTION_WORDS = re.compile(
    r"\b(what|which|how|does|do|is|are|the|a|an|can|could|would|of|for|to|in|on|and|with|my|i|me|help|helps|affect|affects|influence|influences|regulate|regulates|contribute|contributes|involved|support|supports|work|works|happen|happens)\b",
    re.I,
)
_TISSUES = (
    "tendon",
    "cartilage",
    "muscle",
    "skin",
    "brain",
    "liver",
    "kidney",
    "heart",
    "lung",
    "bone",
    "blood",
    "intestine",
)


def linked_entities(text: str) -> tuple[EntityHint, ...]:
    linked = tuple(
        entity
        for entity in ENTITY_ALIASES
        if any(
            re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", text, re.I)
            for alias in (entity.name, *entity.aliases)
        )
    )
    if not linked:
        symbol = re.search(
            r"\b(?:what (?:is|does)|role of|function of|protein|gene)\s+([A-Z][A-Z0-9-]{2,12})\b",
            text,
        )
        if symbol:
            # A lexical search hint, not a verified gene identity or database identifier.
            return (EntityHint(name=symbol.group(1), entity_type="unresolved_entity"),)
    return linked


def research_topic(text: str) -> str:
    cleaned = _QUESTION_WORDS.sub(" ", text)
    cleaned = re.sub(
        r"\b(mechanisms?|pathways?|biological|molecular|systems?|known|about|its|published|evidence|limitations|safety|concerns|relating)\b",
        " ",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"[^\w\s-]", " ", cleaned)
    return " ".join(cleaned.split())[:250]


def safe_research_question(text: str) -> str | None:
    entities = linked_entities(text)
    targets = [
        item.name for item in entities if item.entity_type not in {"tissue", "biological_process"}
    ]
    if not targets:
        match = re.search(
            r"\b(?:drug|compound|peptide|substance|medication)\s+([A-Za-z][A-Za-z0-9-]{0,60})",
            text,
            re.I,
        )
        if match and match.group(1).casefold() not in {"should", "can", "for", "to", "i", "myself"}:
            targets = [f"{match.group(0)}"]
    if not targets:
        return None
    outcome_match = re.search(
        r"\bfor (memory|pain|sleep|tendon recovery|muscle recovery|motivation)\b", text, re.I
    )
    outcome = f" relating to {outcome_match.group(1)}" if outcome_match else ""
    return f"What is known about {', '.join(targets[:2])}{outcome}, its biological mechanisms, published evidence, limitations, and safety concerns?"


def plan_queries(text: str, entities: tuple[EntityHint, ...]) -> tuple[str, ...]:
    topic = research_topic(text)
    topic = re.sub(r"\b(mechanisms?|pathways?)\b", " ", topic, flags=re.I)
    topic = " ".join(topic.split())
    if not topic:
        topic = " ".join(item.name for item in entities)
    topic = re.sub(
        r"\b\d+\b|\b(?:years? old|yesterday|today|my name|since)\b", " ", topic, flags=re.I
    )
    if re.search(r"\btendon\b", topic, re.I) and re.search(
        r"\b(recovery|healing|repair)\b", topic, re.I
    ):
        topic = (
            "tendon AND (healing OR recovery OR repair) AND "
            "(mechanotransduction OR collagen OR inflammation OR tenocyte OR remodeling)"
        )
    elif len(entities) == 1 and topic.casefold() in {
        entities[0].name.casefold(),
        *(alias.casefold() for alias in entities[0].aliases),
    }:
        entity = entities[0]
        names = (entity.name, *entity.aliases[:1])
        topic = (
            "("
            + " OR ".join('"' + name + '"' for name in names)
            + ") AND (function OR mechanism OR signaling)"
        )
    # At most one main query and one opposing/limiting-findings query.
    return (
        topic[:400],
        f'({topic[:320]}) AND ("no effect" OR inconsistent OR contradict* OR limitations)',
    )


def route_question(
    text: str,
    *,
    depth: ResearchDepth = "research",
    context_updates: Mapping[str, str | bool | None] | None = None,
    registry: DomainPackRegistry | None = None,
) -> ResearchInterpretation:
    normalized = normalize_question(text)
    if len(normalized) < 3:
        raise EmptyQuestionError("Enter a biological question with at least three characters.")
    if len(normalized) > 2000:
        raise ValueError("Questions are limited to 2000 characters")
    safety = classify_query(normalized)
    context_text = ""
    entities = linked_entities(normalized)
    topic = research_topic(normalized) or normalized
    context = QuestionContext(
        requested_outcome=topic,
        symptom_or_process=topic,
        tissue=next(
            (item for item in _TISSUES if re.search(r"\b" + item + r"\b", normalized, re.I)), None
        ),
        candidate_intervention=next(
            (item.name for item in entities if item.entity_type in {"drug", "compound", "peptide"}),
            None,
        ),
        population="Not specified; source populations remain separate",
        important_uncertainty=(
            "Interpretation is provisional; source context may differ from this question.",
        ),
    )
    if context_updates:
        context = QuestionContext.model_validate({**context.model_dump(), **context_updates})
        context_text = " ".join(
            value for value in context_updates.values() if isinstance(value, str)
        )
        context_safety = classify_query(context_text)
        if context_safety.restricted and not safety.urgent:
            safety = context_safety
        entities = linked_entities(context.requested_outcome) or entities
    classes = [QuestionClass.BIOLOGICAL_PROCESS]
    if re.search(r"\b(pain|swelling|symptom)\b", normalized, re.I):
        classes.append(QuestionClass.SYMPTOM_MECHANISM)
    if any(item.entity_type in {"protein", "gene", "receptor"} for item in entities):
        classes.append(QuestionClass.GENE_OR_PROTEIN)
    if context.candidate_intervention:
        classes.append(QuestionClass.INTERVENTION_MECHANISM)
    if any(item.entity_type == "peptide" for item in entities):
        classes.append(QuestionClass.PEPTIDE)
    if re.search(r"\bpathways?\b", normalized, re.I):
        classes.append(QuestionClass.PATHWAY)
    question = ResearchQuestion(
        id=stable_uuid(
            "research-question",
            normalized.casefold() + json.dumps(context.model_dump(mode="json"), sort_keys=True),
        ),
        original_text=normalized,
        normalized_text=normalized.casefold(),
        question_classes=tuple(classes),
        interpreted_summary=f"Investigate {context.requested_outcome}. Preserve study-specific context and separate evidence from proposed connections.",
        context=context,
    )
    common = {"question": question, "depth": depth, "entities": entities, "safety_notice": safety}
    if safety.restricted:
        return ResearchInterpretation(
            **common,
            mode=ResearchMode.RESTRICTED_WITH_SAFE_ALTERNATIVE,
            safe_research_question=None
            if safety.urgent
            else (safe_research_question(normalized) or safe_research_question(context_text)),
            notice=safety.message,
        )
    if _NONBIOLOGY.search(normalized):
        return ResearchInterpretation(
            **common,
            mode=ResearchMode.OUT_OF_DOMAIN,
            notice="This tool investigates biology. Describe a biological process, entity, tissue, or research outcome.",
        )
    try:
        domain, curated = interpret_question(
            normalized, context_updates=context_updates, registry=registry
        )
        selected_registry = registry or DomainPackRegistry()
        pack = selected_registry.load(domain)
        names = " ".join(
            name for entity in pack.entities for name in (entity.preferred_name, *entity.aliases)
        )
        uncovered = [
            entity
            for entity in entities
            if entity.entity_type
            in {
                "protein",
                "gene",
                "receptor",
                "drug",
                "compound",
                "peptide",
                "metabolite",
                "neurotransmitter",
                "unresolved_entity",
            }
            and not any(
                re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", names, re.I)
                for name in (entity.name, *entity.aliases)
            )
        ]
        if uncovered:
            raise UnsupportedQuestionError(
                "The named research entity is outside this pack's recorded scope."
            )
        return ResearchInterpretation(
            **{**common, "question": curated},
            mode=ResearchMode.CURATED,
            domain_pack=domain,
            notice="This topic has a reviewed CausalBio evidence pack. Its scope remains limited to the recorded context.",
        )
    except AmbiguousQuestionError as exc:
        return ResearchInterpretation(
            **common,
            mode=ResearchMode.CLARIFICATION_REQUIRED,
            clarifications=exc.alternatives[:3],
            notice=str(exc),
        )
    except UnsupportedQuestionError:
        pass
    if topic.casefold() in {
        "pain",
        "protein",
        "drug",
        "biology",
        "recovery",
        "drug x",
        "compound x",
        "peptide x",
    } or re.search(r"\b(?:drug|compound|peptide|substance) x\b", normalized, re.I):
        return ResearchInterpretation(
            **common,
            mode=ResearchMode.CLARIFICATION_REQUIRED,
            clarifications=(
                "Name the biological entity, tissue, or outcome you want to investigate.",
            ),
            notice="A specific research subject will make the evidence search useful.",
        )
    if not (_BIOLOGY.search(normalized) or entities):
        return ResearchInterpretation(
            **common,
            mode=ResearchMode.OUT_OF_DOMAIN,
            notice="I could not identify a biological research subject. Name a process, tissue, gene, protein, compound, or symptom; unfamiliar names may need biological context.",
        )
    explanation = bool(
        re.match(r"^(what (?:is|are|does)|what do|explain|define)\b", normalized, re.I)
    )
    return ResearchInterpretation(
        **common,
        mode=ResearchMode.EXPLANATORY if explanation else ResearchMode.LIVE_RESEARCH,
        search_queries=plan_queries(context.requested_outcome, entities),
        notice="Researching a new topic. Available sources will form a provisional investigation; source extracts and proposed connections are not curated conclusions.",
    )
