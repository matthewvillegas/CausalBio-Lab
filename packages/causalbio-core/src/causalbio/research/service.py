"""Bounded, isolated source research with explicit partial and offline results."""

from __future__ import annotations

import re
import time
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict
from uuid import uuid4

from causalbio.demo.registry import DomainPackRegistry
from causalbio.domain.identifiers import stable_uuid
from causalbio.investigations.service import InvestigationService
from causalbio.research.extraction import (
    build_mechanisms,
    claim_priority,
    matches_overview_topic,
    overview_claims,
    research_modifiers,
    source_claims,
    temporary_graph,
)
from causalbio.research.models import (
    ResearchClaim,
    ResearchDepth,
    ResearchEvidence,
    ResearchInterpretation,
    ResearchMode,
    SourceRun,
    UniversalResearchResult,
)
from causalbio.research.router import route_question
from causalbio.sources import EuropePMCAdapter, PubMedAdapter, UniProtAdapter
from causalbio.sources.cache import FileSystemSourceCache
from causalbio.sources.errors import SourceAdapterError, SourceUnavailableError
from causalbio.sources.models import (
    CacheStatus,
    EuropePMCSearchResult,
    NormalizedLiteratureRecord,
    NormalizedProteinRecord,
    ProteinFunctionAnnotation,
    SourceAdapter,
    SourceSearchRequest,
    SourceSearchResultBase,
)
from causalbio.sources.policy import RequestPolicy
from causalbio.sources.transport import HTTPResponse

_POOL = ThreadPoolExecutor(max_workers=6, thread_name_prefix="causalbio-source")


class OfflineTransport:
    def get(
        self, url: str, *, params: Mapping[str, str], headers: Mapping[str, str], timeout: float
    ) -> HTTPResponse:
        raise SourceUnavailableError("Offline research: external requests are disabled")


class _ProviderOptions(TypedDict):
    cache: FileSystemSourceCache
    timeout_seconds: float
    max_search_seconds: float
    request_policy: RequestPolicy


def configured_providers(
    cache_root: Path, *, online: bool
) -> dict[str, SourceAdapter[SourceSearchResultBase]]:
    cache = FileSystemSourceCache(cache_root)
    kwargs: _ProviderOptions = {
        "cache": cache,
        "timeout_seconds": 5.0,
        "max_search_seconds": 14.0,
        "request_policy": RequestPolicy(max_attempts=2 if online else 1),
    }
    transport = None if online else OfflineTransport()
    return {
        "europe_pmc": EuropePMCAdapter(transport=transport, **kwargs),
        "pubmed": PubMedAdapter(transport=transport, **kwargs),
        "uniprot": UniProtAdapter(transport=transport, **kwargs),
    }


def _year(value: str | None) -> int | None:
    match = re.search(r"\b(19|20)\d{2}\b", value or "")
    return int(match.group()) if match else None


def normalize_records(result: SourceSearchResultBase) -> tuple[ResearchEvidence, ...]:
    records: list[ResearchEvidence] = []
    common = {"retrieved_at": result.retrieved_at, "cache_status": result.cache_status.value}
    if isinstance(result, EuropePMCSearchResult):
        for item in result.records:
            review = any("review" in text.casefold() for text in item.publication_types)
            records.append(
                ResearchEvidence(
                    **common,
                    id=stable_uuid("research-source", f"{item.source}:{item.record_id}"),
                    source=item.source,
                    source_record_id=item.record_id,
                    title=item.title,
                    authors=item.authors,
                    year=item.publication_year,
                    doi=item.doi,
                    pmid=item.pmid,
                    source_url=item.canonical_url,
                    abstract=item.abstract,
                    study_type=", ".join(item.publication_types) or None,
                    primary_or_review="review" if review else "unspecified",
                    limitations=(
                        "Abstract and metadata retrieval; full-text methods and claim entailment have not been independently reviewed.",
                        "Species, tissue, effect size, and sample size remain unknown unless explicitly supplied by structured source metadata.",
                    ),
                )
            )
    else:
        for item in getattr(result, "records", ()):
            if isinstance(item, NormalizedLiteratureRecord):
                doi = next(
                    (
                        entry.value
                        for entry in item.identifiers
                        if entry.namespace.casefold() == "doi"
                    ),
                    None,
                )
                records.append(
                    ResearchEvidence(
                        **common,
                        id=stable_uuid("research-source", f"pubmed:{item.record_id}"),
                        source="pubmed",
                        source_record_id=item.record_id,
                        title=item.title,
                        authors=item.authors,
                        year=_year(item.publication_date),
                        doi=doi,
                        pmid=item.record_id,
                        source_url=item.canonical_url,
                        study_type=", ".join(item.publication_types) or None,
                        primary_or_review="review"
                        if any("review" in text.casefold() for text in item.publication_types)
                        else "unspecified",
                        limitations=(
                            "Citation metadata only. A title cannot support a detailed biological mechanism claim.",
                        ),
                    )
                )
            elif isinstance(item, NormalizedProteinRecord):
                annotations = item.function_annotations or tuple(
                    ProteinFunctionAnnotation(text=text) for text in item.functions
                )
                grouped: dict[str | None, list[ProteinFunctionAnnotation]] = {}
                for annotation in annotations:
                    grouped.setdefault(annotation.molecule, []).append(annotation)
                if not grouped:
                    grouped[None] = []
                for molecule, group in grouped.items():
                    scope = (
                        f"Specific to {molecule}"
                        if molecule
                        else "Molecule scope not specified by source"
                    )
                    records.append(
                        ResearchEvidence(
                            **common,
                            id=stable_uuid(
                                "research-source",
                                f"uniprot:{item.record_id}:{molecule or 'unspecified'}",
                            ),
                            source="uniprot",
                            source_record_id=item.record_id,
                            title=f"{molecule or item.protein_name} — {item.organism_name} ({scope})",
                            source_url=item.canonical_url,
                            abstract="\n".join(annotation.text for annotation in group) or None,
                            organism=item.organism_name,
                            experimental_context=scope,
                            annotation_evidence=tuple(
                                evidence.model_dump()
                                for annotation in group
                                for evidence in annotation.evidences
                            ),
                            study_type="Reviewed protein annotation"
                            if item.reviewed
                            else "Unreviewed protein annotation",
                            limitations=(
                                "Database function annotation; not a clinical study or an estimate of treatment benefit.",
                                "Protein forms and precursors may have different roles. An unscoped annotation does not establish a form-specific mechanism.",
                                "Multiple annotations from this entry are one database source, not independent replication.",
                            ),
                        )
                    )
    return tuple(records)


def _local_records(
    interpretation: ResearchInterpretation, registry: DomainPackRegistry
) -> tuple[ResearchEvidence, ...]:
    anchors = [item.name.casefold() for item in interpretation.entities]
    if not anchors:
        anchors = [
            word
            for word in interpretation.question.context.requested_outcome.casefold().split()
            if len(word) > 4
        ]
    result: list[ResearchEvidence] = []
    for slug in registry.slugs():
        for record in registry.load(slug).evidence:
            haystack = f"{record.study.title} {record.evidence_note}".casefold()
            if not anchors or not any(anchor in haystack for anchor in anchors):
                continue
            identifiers = {item.namespace.upper(): item.value for item in record.study.identifiers}
            result.append(
                ResearchEvidence(
                    id=record.id,
                    source="local_curated",
                    source_record_id=identifiers.get("PMID", str(record.id)),
                    title=record.study.title,
                    authors=record.study.authors,
                    year=record.study.publication_year,
                    doi=identifiers.get("DOI"),
                    pmid=identifiers.get("PMID"),
                    source_url=record.study.source_url,
                    abstract=record.evidence_note,
                    organism=record.experimental_context.species,
                    population=record.experimental_context.population,
                    tissue=record.experimental_context.tissue,
                    cell_type=record.experimental_context.cell_type,
                    experimental_context=record.experimental_context.condition,
                    study_type=record.study.study_type.value,
                    primary_or_review="review"
                    if "review" in record.study.study_type.value
                    else "primary",
                    result_direction=record.result_direction
                    if record.result_direction != "null"
                    else "contradicts",
                    sample_size=record.study.population.sample_size,
                    limitations=record.limitations,
                    retrieved_at=datetime.combine(
                        record.retrieved_at, datetime.min.time(), tzinfo=UTC
                    ),
                    cache_status="local_curated",
                    evidence_status="curated",
                )
            )
    return tuple(result)


class ResearchService:
    def __init__(
        self,
        *,
        providers: Mapping[str, SourceAdapter[SourceSearchResultBase]] | None = None,
        cache_root: Path = Path("data/cache/sources"),
        online: bool = True,
        registry: DomainPackRegistry | None = None,
        deadline_seconds: float = 22.0,
    ) -> None:
        if not 0 < deadline_seconds <= 60:
            raise ValueError("Research deadline must be within (0, 60] seconds")
        self.providers = (
            dict(providers)
            if providers is not None
            else configured_providers(cache_root, online=online)
        )
        self.registry = registry or DomainPackRegistry()
        self.online = online
        self.deadline_seconds = deadline_seconds

    def investigate(
        self,
        text: str,
        *,
        depth: ResearchDepth = "research",
        context_updates: Mapping[str, str | bool | None] | None = None,
    ) -> UniversalResearchResult:
        interpretation = route_question(
            text, depth=depth, context_updates=context_updates, registry=self.registry
        )
        if interpretation.mode == ResearchMode.CURATED:
            result = InvestigationService(self.registry).investigate(
                text, context_updates=context_updates
            )
            return UniversalResearchResult(
                id=uuid4(),
                mode=ResearchMode.CURATED,
                interpretation=interpretation,
                curated_result=result,
                limitations=(
                    "Curated evidence pack; small educational curation set, not a systematic review.",
                ),
            )
        if interpretation.mode not in {ResearchMode.LIVE_RESEARCH, ResearchMode.EXPLANATORY}:
            return UniversalResearchResult(
                id=uuid4(),
                mode=interpretation.mode,
                interpretation=interpretation,
                limitations=(interpretation.notice,),
            )
        main, opposite = interpretation.search_queries
        limit = {"quick": 4, "research": 8, "deep": 12}[depth]
        jobs: list[tuple[str, str, int]] = [
            ("europe_pmc", main, limit),
            ("pubmed", main, min(limit, 6)),
        ]
        if depth != "quick":
            jobs.append(("europe_pmc", opposite, 3))
            overview_entity = next(
                (
                    entity
                    for entity in interpretation.entities
                    if entity.entity_type not in {"tissue", "biological_process"}
                ),
                None,
            )
            overview_query = f'TITLE:"{overview_entity.name}"' if overview_entity else f"({main})"
            jobs.append(("europe_pmc", f"{overview_query} AND PUB_TYPE:review", 3))
        protein = next(
            (
                item
                for item in interpretation.entities
                if item.entity_type in {"protein", "gene", "receptor"}
            ),
            None,
        )
        if protein:
            accession = protein.identifiers.get("UniProtKB")
            query = (
                f"accession:{accession}"
                if accession
                else f"gene_exact:{protein.name} AND reviewed:true"
            )
            jobs.append(("uniprot", query, 3))
        started = time.monotonic()
        futures = {
            _POOL.submit(
                self.providers[name].search, SourceSearchRequest(query=query, limit=count)
            ): (name, query)
            for name, query, count in jobs
            if name in self.providers
        }
        wait(futures, timeout=max(0.0, self.deadline_seconds - (time.monotonic() - started)))
        evidence: list[ResearchEvidence] = []
        runs: list[SourceRun] = []
        for future, (name, query) in futures.items():
            version = str(getattr(self.providers[name], "adapter_version", "unspecified"))
            if not future.done():
                future.cancel()
                runs.append(
                    SourceRun(
                        source=name,
                        query=query,
                        provider_version=version,
                        status="unavailable",
                        record_count=0,
                        detail="Source exceeded the investigation deadline; other results are retained.",
                    )
                )
                continue
            try:
                retrieved = future.result()
                normalized = normalize_records(retrieved)
                evidence.extend(normalized)
                runs.append(
                    SourceRun(
                        source=name,
                        query=query,
                        provider_version=version,
                        status="available"
                        if retrieved.cache_status == CacheStatus.FETCHED
                        else "cached",
                        record_count=len(normalized),
                        retrieved_at=retrieved.retrieved_at,
                        detail=" ".join(retrieved.warnings) or None,
                    )
                )
            except (SourceAdapterError, ValueError, OSError):
                runs.append(
                    SourceRun(
                        source=name,
                        query=query,
                        provider_version=version,
                        status="unavailable" if self.online else "offline",
                        record_count=0,
                        detail="This source could not provide validated evidence for the bounded query.",
                    )
                )
            except Exception:
                runs.append(
                    SourceRun(
                        source=name,
                        query=query,
                        provider_version=version,
                        status="unavailable",
                        record_count=0,
                        detail="Source processing failed; other sources remain available.",
                    )
                )
        if not self.online or not any(item.abstract for item in evidence):
            local = _local_records(interpretation, self.registry)
            evidence.extend(local)
            if local:
                runs.append(
                    SourceRun(
                        source="local_curated",
                        query=main,
                        status="cached",
                        record_count=len(local),
                        detail="Existing curated records reused with their original context; no new pack was created.",
                    )
                )
        # Same publication indexed by both services is one evidence record, not replication.
        unique: dict[str, ResearchEvidence] = {}
        for record in evidence:
            key = (
                f"uniprot:{record.id}"
                if record.source == "uniprot"
                else "pmid:" + record.pmid
                if record.pmid
                else "doi:" + record.doi.casefold()
                if record.doi
                else f"{record.source}:{record.source_record_id}"
            )
            previous = unique.get(key)
            if previous is None or (not previous.abstract and record.abstract):
                unique[key] = record
        records = tuple(unique.values())
        topic = interpretation.question.context.requested_outcome
        mechanisms, complications = build_mechanisms(
            records, maximum=3 if depth == "quick" else 6, topic=topic
        )
        answer: list[ResearchClaim] = []
        seen_sources: set[object] = set()
        # Protein function annotations lead entity explanations when actually retrieved.
        preferred = sorted(
            (claim for record in records for claim in overview_claims(record)),
            key=lambda claim: (
                not any(
                    item.source == "uniprot" and item.id in claim.evidence_ids for item in records
                ),
                -claim_priority(claim, topic),
            ),
        )
        if interpretation.mode == ResearchMode.EXPLANATORY:
            # A gene-function introduction should lead with the retrieved database role,
            # rather than whichever disease paper contains the most signaling keywords.
            annotations = [
                claim
                for record in records
                if record.source == "uniprot"
                for claim in source_claims(record)
            ]
            if annotations:
                preferred = list({claim.text: claim for claim in reversed(annotations)}.values())[
                    ::-1
                ][:3]
        primary_entities = [
            entity
            for entity in interpretation.entities
            if entity.entity_type not in {"tissue", "biological_process"}
        ]
        seen_text: set[str] = set()
        for claim in preferred:
            if claim.text in seen_text:
                continue
            is_annotation = any(
                record.source == "uniprot" and record.id in claim.evidence_ids for record in records
            )
            if not is_annotation and not matches_overview_topic(claim, topic):
                continue
            if (
                primary_entities
                and not any(
                    re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", claim.text, re.I)
                    for entity in primary_entities
                    for name in (entity.name, *entity.aliases)
                )
                and not any(
                    record.source == "uniprot" and record.id in claim.evidence_ids
                    for record in records
                )
            ):
                continue
            if claim.evidence_ids[0] not in seen_sources or (
                interpretation.mode == ResearchMode.EXPLANATORY
                and all(
                    record.source == "uniprot"
                    for record in records
                    if record.id in claim.evidence_ids
                )
            ):
                answer.append(claim)
                seen_sources.add(claim.evidence_ids[0])
                seen_text.add(claim.text)
            if len(answer) == 3:
                break
        fetched = any(item.cache_status == "fetched" for item in records)
        mode = (
            interpretation.mode
            if fetched or (interpretation.mode == ResearchMode.EXPLANATORY and answer)
            else ResearchMode.GENERAL_EVIDENCE_SUMMARY
        )
        notices = []
        if not self.online:
            notices.append(
                "Offline mode — live literature research is unavailable. Cached and curated retrieval dates are preserved."
            )
        if not mechanisms:
            notices.append(
                "We could not retrieve enough evidence to build a mechanism map. Review available citations, refine the named topic, enable live sources, or retry research."
            )
        elif not answer:
            notices.append(
                "Related source records were found, but no extracted passage directly addressed the requested combination of subject and process. Review the evidence or refine the question."
            )
        elif not fetched:
            notices.append(
                "Using cached or local curated evidence. This result does not imply a current live search."
            )
        if any(run.status == "unavailable" for run in runs):
            notices.append(
                "Some sources were unavailable. Available results are retained; this is a partial search."
            )
        return UniversalResearchResult(
            id=uuid4(),
            mode=mode,
            interpretation=interpretation,
            direct_answer=tuple(answer),
            mechanisms=mechanisms,
            evidence=records,
            graph=temporary_graph(mechanisms, records),
            complications=complications,
            modifiers=research_modifiers(records, topic),
            source_runs=tuple(runs),
            limitations=(
                "Provisional source extracts and terminology clusters, not a reviewed causal pathway or systematic review.",
                "Human, animal, cellular, review and database contexts may differ; unknown metadata stays unknown.",
                "Contradiction queries and limiting passages do not establish that all opposing evidence has been found.",
                "No executable pathway model or biological Bayesian inference model is available for this provisional investigation.",
                "No diagnosis, personalized use, dosing, sourcing, synthesis or novel peptide design is provided.",
            ),
            notices=tuple(notices),
        )
