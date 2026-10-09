"""Conservative extractive claims and topic clustering, with no invented relations."""

from __future__ import annotations

import re
from collections import defaultdict

from causalbio.domain.identifiers import stable_uuid
from causalbio.research.models import (
    ResearchClaim,
    ResearchEdge,
    ResearchEvidence,
    ResearchMechanism,
    ResearchNode,
    TemporaryGraph,
)

FAMILIES: tuple[tuple[str, str], ...] = (
    ("Mechanical loading and signaling", r"mechanotransduc|mechanical|loading|strain|exercise"),
    (
        "Extracellular matrix and collagen remodeling",
        r"collagen|extracellular matrix|remodel|\bECM\b",
    ),
    ("Inflammation and immune signaling", r"inflamm|cytokine|macrophage|immune"),
    ("Cell growth and tissue repair", r"proliferat|tenocyte|fibroblast|regenerat|wound|repair"),
    (
        "Energy and metabolic regulation",
        r"\bATP\b|mitochondri|metabol|energetic|phosphocreatine|insulin",
    ),
    (
        "Receptors and intracellular signaling",
        r"receptor|kinase|\bTrkB\b|signaling|signalling|phosphorylat",
    ),
    (
        "Neural function and plasticity",
        r"synap|neuron|neurotroph|plasticity|dopamine|motivation|memory",
    ),
    ("Vascular and tissue context", r"vascular|angiogene|endotheli|blood flow"),
)
_COMPLICATION = re.compile(
    r"\b(no (?:significant |beneficial )?effect|not (?:improve|support|increase|establish)|inconsisten\w*|contradic\w*|unclear|unknown|limited evidence|failed to|limitations?|however)\b",
    re.I,
)
_OPERATIONAL = re.compile(
    r"\b(mg|mcg|micrograms?|milligrams?|dosage|dose|doses|dosing|inject|injected|injection|synthesi[sz]e|synthesis protocol|procure|purchase|buy)\b|\d\s*(?:μg|µg|g\b|g/kg|mg/kg|mM|μM|uM)|\b(?:twice|once|thrice) (?:daily|weekly)\b",
    re.I,
)
_METHOD = re.compile(
    r"\b(technical note|surgical technique|arthroscop|suture|incision|patients? underwent|randomly assigned|we (?:aimed|sought)|aim of|purpose of|objective of|this study aims|were (?:enrolled|recruited)|search terms|search strategy|literature (?:search|was)|eligible publications|inclusion criteria|review aims|to investigate|to evaluate)\b",
    re.I,
)
_MECHANISTIC = re.compile(
    r"\b(signaling|signalling|regulat\w*|mediat\w*|activat\w*|inhibit\w*|bind\w*|receptor\w*|synthesis|remodel\w*|plasticity|proliferat\w*|differentiation|transduc\w*|homeostasis|phosphorylat\w*|buffer\w*)\b",
    re.I,
)
_MODIFIER = re.compile(
    r"\b(exercise|loading|sleep|creatine|caffeine|metformin|selegiline|therapy|treatment|intervention|inhibitor|agonist|antagonist)\b",
    re.I,
)
_NARROW_RESULT = re.compile(
    r"\b(this (?:study|work)|our (?:study|findings|results)|we (?:show|found|tested|hypothesized|subjected)|these (?:data|results|findings|extracts|effects|two extracts)|potential application|provided theoretical|the purpose is)\b",
    re.I,
)


def claim_priority(claim: ResearchClaim, topic: str = "") -> int:
    """Presentation relevance only; this is not an evidence-strength score."""
    terms = set(re.findall(r"[a-z][a-z-]{3,}", topic.casefold()))
    terms -= {
        "mechanism",
        "mechanisms",
        "biological",
        "pathways",
        "evidence",
        "known",
        "genes",
        "proteins",
        "associated",
        "targets",
        "inhibit",
        "inhibits",
    }
    matches = sum(bool(re.search(r"\b" + re.escape(term), claim.text, re.I)) for term in terms)
    return (
        min(matches, 3) * 5
        + min(len(_MECHANISTIC.findall(claim.text)), 3) * 2
        - (12 if _METHOD.search(claim.text) else 0)
        - (2 if len(claim.text.split()) > 45 else 0)
        - (7 if _NARROW_RESULT.search(claim.text) else 0)
    )


def source_claims(record: ResearchEvidence) -> tuple[ResearchClaim, ...]:
    if not record.abstract:
        return ()
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])|\n+", record.abstract)
    result: list[ResearchClaim] = []
    for sentence in sentences:
        text = re.sub(
            r"^(?:(?:abstract|background|methods|results|conclusions?|objectives?|purpose)\s*:?[\s]+)+",
            "",
            sentence.strip(),
            flags=re.I,
        )
        # Trailing database citation lists remain in the source record and structured
        # references. The retained text is still one exact contiguous source passage.
        text = re.sub(r"\s+\(PubMed:[\d,\s]+(?:PubMed:[\d,\s]+)*\)\.?$", "", text)
        words = text.split()
        if not 7 <= len(words) <= 65 or len(text) > 900 or _OPERATIONAL.search(text):
            continue
        if re.match(
            r"^(?:background|methods|results|conclusions?|objectives?|purpose):?\s*$", text, re.I
        ):
            continue
        # No generated paraphrase: the full displayed scientific statement is in the source.
        result.append(
            ResearchClaim(
                id=stable_uuid("research-claim-v1", f"{record.id}:{text}"),
                text=text,
                evidence_ids=(record.id,),
                kind="source_extract",
                source_passage=text,
                # A limiting sentence is supported by its source. It does not, by itself,
                # contradict a named assertion or establish a negative causal effect.
                relation="SUPPORTED_BY",
                uncertainty=(
                    (
                        f"Source context: {record.experimental_context}. "
                        if record.experimental_context
                        else ""
                    )
                    + "Source-reported statement; source context and limitations apply. "
                    "It is not independently adjudicated evidence of causality or clinical benefit."
                ),
            )
        )
    return tuple(result[:14])


def overview_claims(record: ResearchEvidence) -> tuple[ResearchClaim, ...]:
    return tuple(
        claim
        for claim in source_claims(record)
        if not _METHOD.search(claim.text)
        and not re.match(r"^(?:We\b|Our\b|This study\b|The (?:aim|purpose)\b)", claim.text, re.I)
    )


def matches_overview_topic(claim: ResearchClaim, topic: str) -> bool:
    """Require the requested process/target rather than a shared entity alone."""
    terms = set(re.findall(r"[a-z][a-z-]{3,}", topic.casefold()))
    terms -= {
        "mechanism",
        "mechanisms",
        "biological",
        "molecular",
        "pathway",
        "pathways",
        "evidence",
        "known",
        "genes",
        "proteins",
        "associated",
        "targets",
        "inhibit",
        "inhibits",
        "safety",
        "limitations",
        "concerns",
        "published",
        "relating",
        "function",
        "functions",
        "affects",
    }
    if not terms:
        return True
    synonyms = {
        "recovery": r"\b(recover|heal|repair|regenerat|remodel|homeostasis)",
        "healing": r"\b(heal|repair|regenerat)",
        "energetics": r"\b(energetic|energy|ATP|phosphocreatine)",
        "synthesis": r"\b(synthes|biosynthes|production|produc)",
        "inflammation": r"\b(inflamm|cytokine|immune)",
        "creatine": r"\bcreatine\b(?!\s+kinase)",
    }
    matches = sum(
        bool(re.search(synonyms.get(term, r"\b" + re.escape(term)), claim.text, re.I))
        for term in terms
    )
    if "creatine" in terms and not re.search(synonyms["creatine"], claim.text, re.I):
        return False
    # Two-topic questions need two corresponding concepts. One named entity alone
    # does not answer a question about its interaction with a particular target.
    return matches >= min(2, len(terms))


def build_mechanisms(
    evidence: tuple[ResearchEvidence, ...], *, maximum: int = 6, topic: str = ""
) -> tuple[tuple[ResearchMechanism, ...], tuple[ResearchClaim, ...]]:
    grouped: dict[str, list[ResearchClaim]] = defaultdict(list)
    complications: list[ResearchClaim] = []
    for record in evidence:
        for claim in source_claims(record):
            if _COMPLICATION.search(claim.text):
                complications.append(claim)
            if _METHOD.search(claim.text):
                # Keep the study in Evidence without elevating procedures to mechanisms.
                continue
            matched = False
            for name, pattern in FAMILIES:
                if re.search(pattern, claim.text, re.I):
                    grouped[name].append(claim)
                    matched = True
            if not matched:
                grouped["Reported biological functions and context"].append(claim)
    # Shared pathway vocabulary and source context cluster extracts. No semantic model or
    # causal discovery is claimed. Deterministic source-diverse selection avoids duplicates.
    ordered = sorted(
        grouped,
        key=lambda key: (
            key == "Reported biological functions and context",
            -len({e for c in grouped[key] for e in c.evidence_ids}),
            key,
        ),
    )
    mechanisms: list[ResearchMechanism] = []
    for name in ordered[:maximum]:
        selected: list[ResearchClaim] = []
        seen_sources: set[object] = set()
        for claim in sorted(grouped[name], key=lambda claim: -claim_priority(claim, topic)):
            if claim.evidence_ids[0] not in seen_sources:
                selected.append(claim)
                seen_sources.add(claim.evidence_ids[0])
            if len(selected) == 3:
                break
        records = [item for item in evidence if item.id in seen_sources]
        organisms = sorted({item.organism for item in records if item.organism})
        mechanisms.append(
            ResearchMechanism(
                id=stable_uuid("research-family-v1", name),
                title=name,
                description="Source extracts grouped by shared biological terminology. Read each study's context before interpreting this as a mechanism.",
                claims=tuple(selected),
                uncertainties=(
                    "Shared terminology does not establish one causal pathway.",
                    "Metadata and abstracts cannot establish independent replication or applicability to an individual.",
                ),
                evidence_dimensions={
                    "Organism context": "; ".join(organisms)
                    or "Not resolved from metadata; inspect source passages",
                    "Mechanistic evidence": "Preliminary source extracts; not independently graded",
                    "Replication": "Not assessed; publications may reuse underlying studies",
                    "Context match": "Search and terminology match; biological applicability unreviewed",
                    "Contradiction": "Limiting statements retained; not a systematic contradiction review",
                    "Translation uncertainty": "Unreviewed; no individual benefit inferred",
                },
            )
        )
    return tuple(mechanisms), tuple(dict((item.id, item) for item in complications).values())[:8]


def research_modifiers(
    evidence: tuple[ResearchEvidence, ...], topic: str
) -> tuple[ResearchClaim, ...]:
    candidates = [
        claim
        for record in evidence
        for claim in source_claims(record)
        if _MODIFIER.search(claim.text) and not _METHOD.search(claim.text)
    ]
    selected: list[ResearchClaim] = []
    for claim in sorted(candidates, key=lambda item: -claim_priority(item, topic)):
        if all(claim.evidence_ids != prior.evidence_ids for prior in selected):
            selected.append(claim)
        if len(selected) == 3:
            break
    return tuple(selected)


def temporary_graph(
    mechanisms: tuple[ResearchMechanism, ...], evidence: tuple[ResearchEvidence, ...]
) -> TemporaryGraph:
    nodes: dict[object, ResearchNode] = {}
    edges: list[ResearchEdge] = []
    records = {item.id: item for item in evidence}
    for mechanism in mechanisms:
        nodes[mechanism.id] = ResearchNode(
            id=mechanism.id, name=mechanism.title, entity_type="mechanism_topic"
        )
        for claim in mechanism.claims:
            for evidence_id in claim.evidence_ids:
                record = records[evidence_id]
                nodes[evidence_id] = ResearchNode(
                    id=evidence_id,
                    name=record.title,
                    entity_type="study" if record.source != "uniprot" else "protein_annotation",
                    identifiers={
                        key: value
                        for key, value in {"PMID": record.pmid, "DOI": record.doi}.items()
                        if value
                    },
                )
                edges.append(
                    ResearchEdge(
                        id=stable_uuid(
                            "research-edge-v1", f"{mechanism.id}:{claim.id}:{evidence_id}"
                        ),
                        subject_id=mechanism.id,
                        object_id=evidence_id,
                        relation=claim.relation,
                        claim_id=claim.id,
                        evidence_ids=(evidence_id,),
                    )
                )
    return TemporaryGraph(nodes=tuple(nodes.values()), edges=tuple(edges))
