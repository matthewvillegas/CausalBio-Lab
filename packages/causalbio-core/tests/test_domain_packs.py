"""Third-pack contract and registry boundaries without introducing a scientific domain."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from causalbio.demo.registry import DomainPackRegistry
from causalbio.domain.models import QuestionContext
from causalbio.investigations.service import InvestigationService
from causalbio.questions.interpreter import UnsupportedQuestionError, interpret_question
from causalbio.reporting import generate_report
from pydantic import ValidationError

FIXTURE_ROOT = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_registry(tmp_path: Path) -> DomainPackRegistry:
    shutil.copytree(FIXTURE_ROOT / "third-pack", tmp_path / "third-pack")
    return DomainPackRegistry(tmp_path)


def test_third_pack_discovers_interprets_investigates_and_reports_without_code_branches(
    fixture_registry: DomainPackRegistry,
) -> None:
    assert fixture_registry.slugs() == ("third-pack",)
    pack = fixture_registry.load("third-pack")
    result = InvestigationService(fixture_registry).investigate(pack.example_questions[0])
    assert result.domain_pack == pack.slug
    assert result.question == pack.question
    assert len(result.hypotheses) == 1
    assert result.petri_model is None
    assert not result.inference_eligibility.requirements["defined_numerical_model"]
    assert not result.inference_eligibility.eligible
    assert "No numerical data" in result.inference_eligibility.explanation
    assert result.ranking_sensitivity is not None
    report = generate_report(result)
    assert report.citation_coverage == 1
    assert "no executable pathway model" in report.sections["Limitations"]
    with pytest.raises(UnsupportedQuestionError) as unsupported:
        interpret_question("What controls liver glucose metabolism?", registry=fixture_registry)
    assert unsupported.value.alternatives == pack.example_questions


@pytest.mark.parametrize(
    "slug", ["../memory", "../third-pack", "THIRD-PACK", "third-pack/..", "missing"]
)
def test_registry_rejects_invalid_or_missing_paths(
    fixture_registry: DomainPackRegistry, slug: str
) -> None:
    with pytest.raises(KeyError):
        fixture_registry.load(slug)


@pytest.mark.parametrize("collection", ["entities", "assertions", "evidence", "hypotheses"])
def test_raw_duplicate_keys_are_rejected_before_identifiers_can_overwrite(
    fixture_registry: DomainPackRegistry,
    collection: str,
) -> None:
    path = fixture_registry.root / "third-pack" / "pack.json"
    raw = json.loads(path.read_text())
    raw[collection].append(raw[collection][0])
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match=f"duplicate {collection} keys"):
        fixture_registry.load("third-pack")


def test_expected_mechanisms_and_metadata_are_validated(
    fixture_registry: DomainPackRegistry,
) -> None:
    path = fixture_registry.root / "third-pack" / "pack.json"
    raw = json.loads(path.read_text())
    raw["metadata"]["expected_hypothesis_keys"] = ["missing"]
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="expected hypothesis keys"):
        fixture_registry.load("third-pack")
    raw["metadata"]["context_defaults"]["wants_mechanisms"] = "false"
    path.write_text(json.dumps(raw))
    with pytest.raises(ValidationError):
        fixture_registry.slugs()


@pytest.mark.parametrize(
    "updates",
    [
        {"requested_outcome": None},
        {"activity": True},
        {"wants_interventions": "false"},
        {"requested_outcome": "   "},
        {"tissue": "a" * 2001},
        {"important_uncertainty": "not a tuple"},
    ],
)
def test_context_updates_cannot_bypass_domain_validation(updates: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        interpret_question("How could memory persist after learning?", context_updates=updates)


def test_normalized_context_changes_question_and_investigation_identity() -> None:
    service = InvestigationService()
    original = service.investigate("What supports memory retention?")
    changed = service.investigate(
        "What supports memory retention?",
        context_updates={"activity": "spaced learning", "timing": "after sleep"},
    )
    repeated = service.investigate(
        "WHAT supports memory retention?",
        context_updates={"timing": "after sleep", "activity": "  spaced learning  "},
    )
    assert original.id != changed.id == repeated.id
    assert original.question.id != changed.question.id == repeated.question.id
    assert changed.question.context == repeated.question.context
    assert (
        QuestionContext.model_validate(changed.question.context.model_dump())
        == changed.question.context
    )


def test_invalid_directed_mechanism_is_rejected_at_pack_boundary(
    fixture_registry: DomainPackRegistry,
) -> None:
    path = fixture_registry.root / "third-pack" / "pack.json"
    raw = json.loads(path.read_text())
    raw["hypotheses"][0]["paths"][0]["entities"].reverse()
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="direction"):
        fixture_registry.load("third-pack")


@pytest.mark.parametrize("invalid", [[], {"metadata": None}])
def test_malformed_pack_root_cannot_escape_validation(
    fixture_registry: DomainPackRegistry,
    invalid: object,
) -> None:
    path = fixture_registry.root / "third-pack" / "pack.json"
    path.write_text(json.dumps(invalid), encoding="utf-8")
    with pytest.raises(ValueError):
        fixture_registry.load("third-pack")


def test_dangling_pack_reference_is_a_validation_error(
    fixture_registry: DomainPackRegistry,
) -> None:
    path = fixture_registry.root / "third-pack" / "pack.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["assertions"][0]["evidence"] = ["nonexistent-source"]
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match=r"unknown reference.*nonexistent-source"):
        fixture_registry.load("third-pack")


def test_numerical_declarations_are_strict_and_do_not_enable_unbound_inference(
    fixture_registry: DomainPackRegistry,
) -> None:
    path = fixture_registry.root / "third-pack" / "pack.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    declarations = raw["metadata"]["numerical_data"]
    declarations["observations_available"] = "false"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValidationError):
        fixture_registry.metadata("third-pack")
    for field in (
        "observations_available",
        "unknown_parameters_defined",
        "priors_defined",
        "likelihood_defined",
        "identifiability_reviewed",
    ):
        declarations[field] = True
    path.write_text(json.dumps(raw), encoding="utf-8")
    result = InvestigationService(fixture_registry).investigate(
        raw["metadata"]["example_questions"][0]
    )
    assert result.inference_eligibility.requirements["observed_or_curated_numerical_data"]
    assert not result.inference_eligibility.requirements["hmc_backend_and_diagnostics"]
    assert not result.inference_eligibility.eligible


def test_recognition_uses_phrase_boundaries(fixture_registry: DomainPackRegistry) -> None:
    with pytest.raises(UnsupportedQuestionError):
        interpret_question("Explain presynthetic switchboard activity", registry=fixture_registry)
