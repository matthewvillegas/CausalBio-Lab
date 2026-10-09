"""Execute the small deterministic offline evaluation fixture."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from causalbio.demo import load_domain_pack
from causalbio.domain.models import CausalAssertion, DomainPack
from causalbio.inference import load_hmc_demo_dataset
from causalbio.questions import interpret_question
from causalbio.safety import classify_query

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE_PATH = WORKSPACE_ROOT / "data" / "evals" / "offline-evals.json"
EXPECTED_SCHEMA_VERSION = "causalbio-offline-evals-1.0"


@dataclass(frozen=True, slots=True)
class EvalResult:
    case_id: str
    category: str
    passed: bool
    detail: str


def _value(value: Any) -> Any:
    return getattr(value, "value", value)


def _entity_ids_by_name(pack: DomainPack) -> dict[str, Any]:
    return {entity.preferred_name: entity.id for entity in pack.entities}


def _find_assertion(pack: DomainPack, case: dict[str, Any]) -> CausalAssertion:
    entity_ids = _entity_ids_by_name(pack)
    subject = cast(str, case["subject"])
    object_name = cast(str, case["object"])
    if subject not in entity_ids or object_name not in entity_ids:
        raise LookupError(f"Unknown assertion endpoint: {subject!r} -> {object_name!r}")
    matches = [
        assertion
        for assertion in pack.assertions
        if assertion.subject_id == entity_ids[subject]
        and assertion.object_id == entity_ids[object_name]
    ]
    if len(matches) != 1:
        raise LookupError(f"Expected one assertion, found {len(matches)}")
    return matches[0]


def _evaluate_question(case: dict[str, Any], expected: dict[str, Any]) -> str:
    domain, question = interpret_question(cast(str, case["input"]))
    expected_domain = cast(str, expected["domain"])
    expected_outcome = cast(str, expected.get("outcome_contains", "")).casefold()
    if domain != expected_domain:
        raise AssertionError(f"domain={domain!r}, expected {expected_domain!r}")
    if expected_outcome and expected_outcome not in question.context.requested_outcome.casefold():
        raise AssertionError(f"requested outcome does not contain {expected_outcome!r}")
    return f"routed to {domain!r} with preserved outcome context"


def _evaluate_assertion(case: dict[str, Any], expected: dict[str, Any]) -> str:
    assertion = _find_assertion(load_domain_pack(cast(str, case["pack"])), case)
    checks = {
        "relation": _value(assertion.relation),
        "causal_status": _value(assertion.causal_status),
        "species": assertion.biological_context.species,
        "confidence": _value(assertion.confidence_classification),
    }
    for field, actual in checks.items():
        if field in expected and actual != expected[field]:
            raise AssertionError(f"{field}={actual!r}, expected {expected[field]!r}")
    minimum_support = int(expected.get("minimum_supporting_evidence", 0))
    minimum_contradiction = int(expected.get("minimum_contradictory_evidence", 0))
    if len(assertion.supporting_evidence_ids) < minimum_support:
        raise AssertionError("supporting-evidence count is below the fixture minimum")
    if len(assertion.contradictory_evidence_ids) < minimum_contradiction:
        raise AssertionError("contradictory-evidence count is below the fixture minimum")
    return "assertion relation, causal status, context, and provenance matched"


def _evaluate_intervention(case: dict[str, Any], expected: dict[str, Any]) -> str:
    pack = load_domain_pack(cast(str, case["pack"]))
    name = cast(str, case["name"])
    matches = [item for item in pack.interventions if item.name == name]
    if len(matches) != 1:
        raise LookupError(f"Expected one intervention named {name!r}, found {len(matches)}")
    intervention = matches[0]
    if intervention.addresses != expected["addresses"]:
        raise AssertionError("intervention target role did not match")
    if intervention.personal_recommendation is not expected["personal_recommendation"]:
        raise AssertionError("personal-recommendation boundary did not match")
    if len(intervention.evidence_ids) < int(expected.get("minimum_evidence", 0)):
        raise AssertionError("intervention evidence count is below the fixture minimum")
    return "intervention role and non-recommendation boundary matched"


def _evaluate_safety(case: dict[str, Any], expected: dict[str, Any]) -> str:
    notice = classify_query(cast(str, case["input"]))
    actual = {
        "query_class": _value(notice.query_class),
        "restricted": notice.restricted,
        "urgent": notice.urgent,
    }
    for field, expected_value in expected.items():
        if actual[field] != expected_value:
            raise AssertionError(f"{field}={actual[field]!r}, expected {expected_value!r}")
    return f"classified as {actual['query_class']!r} with the expected boundary"


def _evaluate_grounding(case: dict[str, Any], expected: dict[str, Any]) -> str:
    pack = load_domain_pack(cast(str, case["pack"]))
    minimum = int(expected["minimum_evidence_records"])
    evidence_ids = {record.id for record in pack.evidence}
    if len(evidence_ids) < minimum:
        raise AssertionError(
            f"only {len(evidence_ids)} evidence records; expected at least {minimum}"
        )
    for record in pack.evidence:
        if not record.study.identifiers or not str(record.study.source_url):
            raise AssertionError(f"evidence {record.id} lacks an identifier or source URL")
    for assertion in pack.assertions:
        referenced = {*assertion.supporting_evidence_ids, *assertion.contradictory_evidence_ids}
        if not assertion.supporting_evidence_ids or not referenced <= evidence_ids:
            raise AssertionError(f"assertion {assertion.id} has invalid evidence provenance")
    return f"validated {len(evidence_ids)} evidence records and all assertion references"


def _evaluate_inference_fixture(_: dict[str, Any], expected: dict[str, Any]) -> str:
    dataset = load_hmc_demo_dataset()
    actual = {
        "dataset_id": dataset.id,
        "observation_count": len(dataset.outcome),
        "seed": dataset.seed,
        "synthetic": dataset.synthetic,
    }
    for field, expected_value in expected.items():
        if actual[field] != expected_value:
            raise AssertionError(f"{field}={actual[field]!r}, expected {expected_value!r}")
    if len(dataset.predictor) != len(dataset.outcome) or not dataset.provenance:
        raise AssertionError("inference observations or provenance are incomplete")
    return "synthetic inference observations, seed, and provenance matched"


def evaluate_case(case: dict[str, Any]) -> EvalResult:
    case_id = cast(str, case["id"])
    category = cast(str, case["category"])
    expected = cast(dict[str, Any], case["expected"])
    evaluators = {
        "question_domain": _evaluate_question,
        "assertion": _evaluate_assertion,
        "intervention": _evaluate_intervention,
        "safety": _evaluate_safety,
        "pack_grounding": _evaluate_grounding,
        "inference_fixture": _evaluate_inference_fixture,
    }
    try:
        kind = cast(str, case["kind"])
        evaluator = evaluators[kind]
        detail = evaluator(case, expected)
        return EvalResult(case_id, category, True, detail)
    except (AssertionError, KeyError, LookupError, ValueError) as error:
        return EvalResult(case_id, category, False, str(error))


def evaluate_fixture(path: Path = DEFAULT_FIXTURE_PATH) -> tuple[EvalResult, ...]:
    fixture = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if fixture.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        raise ValueError("Unsupported or missing evaluation-fixture schema version")
    cases = cast(list[dict[str, Any]], fixture.get("cases"))
    if not cases:
        raise ValueError("Evaluation fixture contains no cases")
    case_ids = [cast(str, case["id"]) for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Evaluation fixture case IDs must be unique")
    return tuple(evaluate_case(case) for case in cases)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run deterministic CausalBio Lab evaluations.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE_PATH)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable results.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    results = evaluate_fixture(args.fixture.expanduser().resolve())
    passed = sum(result.passed for result in results)
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        print(f"Offline evaluations: {passed}/{len(results)} passed")
        totals = Counter(result.category for result in results)
        successes = Counter(result.category for result in results if result.passed)
        for category in sorted(totals):
            print(f"- {category}: {successes[category]}/{totals[category]}")
        for result in results:
            if not result.passed:
                print(f"  FAIL {result.case_id}: {result.detail}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
