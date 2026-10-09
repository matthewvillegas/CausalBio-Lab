"""Tests for safe, explicit calculations on known peptide records."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from causalbio.peptides import (
    KnownPeptideRegistry,
    analyze_known_peptide,
    compare_known_peptides,
)
from causalbio.peptides.analysis import estimated_net_charge


def test_registry_contains_only_curated_known_sequences() -> None:
    registry = KnownPeptideRegistry()
    peptides = registry.list()
    assert [item.slug for item in peptides] == ["neurokinin-a", "substance-p"]
    assert all(item.precursor_uniprot == "P20366" for item in peptides)
    assert all("C-terminal amidation" in item.terminal_modifications for item in peptides)
    assert "No sequence generation" in registry.notice


def test_substance_p_calculations_match_declared_sequence_chemistry() -> None:
    analysis = analyze_known_peptide("substance-p")
    calculated = analysis.calculated_properties
    assert calculated.sequence_length == 11
    assert calculated.amino_acid_composition.counts["F"] == 2
    assert sum(calculated.amino_acid_composition.fractions.values()) == pytest.approx(1.0)
    assert calculated.approximate_molecular_weight_da == pytest.approx(1347.645, abs=0.01)
    assert calculated.estimated_net_charge == pytest.approx(2.994, abs=0.01)
    assert calculated.estimated_isoelectric_point is None
    assert 0 <= calculated.normalized_sequence_entropy <= 1


def test_root_found_isoelectric_point_and_charge_shift_for_neurokinin_a() -> None:
    analysis = analyze_known_peptide("neurokinin-a", pH=7.4)
    calculated = analysis.calculated_properties
    estimated_pi = calculated.estimated_isoelectric_point
    assert estimated_pi is not None
    assert estimated_pi == pytest.approx(10.095, abs=0.01)
    peptide = analysis.peptide
    assert estimated_net_charge(peptide, 3.0) > estimated_net_charge(peptide, 11.0)
    assert estimated_net_charge(peptide, estimated_pi) == pytest.approx(0.0, abs=1e-9)
    with pytest.raises(ValueError, match="between 0 and 14"):
        estimated_net_charge(peptide, 15.0)


def test_outputs_separate_measurement_annotation_calculation_and_prediction() -> None:
    analysis = analyze_known_peptide("substance-p")
    assert analysis.measured_properties == {}
    assert analysis.database_annotations["known_targets"]
    assert analysis.database_annotations["available_structures"]
    assert analysis.model_predictions.unsupported_activity_prediction is False
    assert analysis.model_predictions.amphipathicity_indicator == "moderate"
    assert any(
        "No sequence calculation establishes" in item for item in analysis.unsupported_assumptions
    )
    assert "No novel sequence generation" in analysis.safety_notice


def test_known_peptide_comparison_reports_literal_alignment_and_conserved_positions() -> None:
    comparison = compare_known_peptides("substance-p", "neurokinin-a")
    assert len(comparison.aligned_a) == len(comparison.aligned_b)
    assert comparison.sequence_identity == pytest.approx(5 / 11)
    assert "".join(item.residue for item in comparison.conserved_positions) == "KFGLM"
    assert comparison.scoring == {"match": 1, "mismatch": 0, "gap": -1}
    assert "do not establish" in comparison.interpretation


def test_registry_rejects_unknown_and_malformed_records(tmp_path: Path) -> None:
    with pytest.raises(KeyError, match="Unknown known peptide"):
        KnownPeptideRegistry().get("invented-sequence")

    malformed = {
        "version": "test",
        "notice": "test fixture",
        "peptides": [
            {
                "slug": "invalid",
                "name": "Invalid",
                "sequence": "ABCZ",
                "organism": "synthetic test",
                "precursor": "none",
                "precursor_uniprot": "none",
                "source_url": "https://example.org",
                "known_targets": [],
                "reported_biological_context": [],
                "evidence_stage": "none",
                "annotation_limitations": [],
            }
        ],
    }
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(malformed), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported amino-acid codes"):
        KnownPeptideRegistry(path)
