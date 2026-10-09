"""Regression tests for the executable offline evaluation fixture."""

from scripts.run_evals import DEFAULT_FIXTURE_PATH, evaluate_fixture

EXPECTED_CATEGORIES = {
    "causal_vs_associative_wording",
    "contradictory_evidence",
    "diagnosis_avoidance",
    "entity_linking",
    "harmful_action_boundary",
    "inference_data_provenance",
    "intervention_vs_outcome",
    "relation_classification",
    "source_grounding",
    "species_context",
    "unsupported_claim",
}


def test_offline_eval_fixture_covers_required_categories_and_passes() -> None:
    results = evaluate_fixture(DEFAULT_FIXTURE_PATH)

    assert len(results) == 11
    assert {result.category for result in results} == EXPECTED_CATEGORIES
    assert all(result.passed for result in results), [
        f"{result.case_id}: {result.detail}" for result in results if not result.passed
    ]
