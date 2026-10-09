"""Transparent calculations for known, curated peptide sequences.

The public functions accept registry slugs rather than arbitrary sequences.  This
keeps the module in an annotation and analysis role: it neither designs peptides
nor supplies synthesis or use instructions.  Physicochemical outputs are simple
sequence calculations, not measurements, activity predictions, or safety claims.
"""

from __future__ import annotations

import json
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import Field, HttpUrl, model_validator
from scipy.optimize import brentq

from causalbio.domain.models import DomainModel

_AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
_AVERAGE_FREE_AMINO_ACID_MASS = {
    "A": 89.094,
    "R": 174.203,
    "N": 132.119,
    "D": 133.104,
    "C": 121.154,
    "E": 147.131,
    "Q": 146.146,
    "G": 75.067,
    "H": 155.156,
    "I": 131.175,
    "L": 131.175,
    "K": 146.189,
    "M": 149.208,
    "F": 165.192,
    "P": 115.132,
    "S": 105.093,
    "T": 119.119,
    "W": 204.228,
    "Y": 181.191,
    "V": 117.148,
}
_KYTE_DOOLITTLE = {
    "A": 1.8,
    "C": 2.5,
    "D": -3.5,
    "E": -3.5,
    "F": 2.8,
    "G": -0.4,
    "H": -3.2,
    "I": 4.5,
    "K": -3.9,
    "L": 3.8,
    "M": 1.9,
    "N": -3.5,
    "P": -1.6,
    "Q": -3.5,
    "R": -4.5,
    "S": -0.8,
    "T": -0.7,
    "V": 4.2,
    "W": -0.9,
    "Y": -1.3,
}
_SIDE_CHAIN_PKA = {"D": 3.9, "E": 4.1, "C": 8.3, "Y": 10.1, "H": 6.0, "K": 10.5, "R": 12.5}
_WATER_MASS = 18.01528
_AMIDATION_MASS_DELTA = -0.984016
_N_TERMINUS_PKA = 9.69
_C_TERMINUS_PKA = 2.34


class PeptideTargetAnnotation(DomainModel):
    name: str
    identifier: str
    relationship: str
    source_url: HttpUrl


class PeptideStructureAnnotation(DomainModel):
    identifier: str
    description: str
    source_url: HttpUrl


class KnownPeptide(DomainModel):
    slug: str
    name: str
    sequence: str
    organism: str
    precursor: str
    precursor_uniprot: str
    source_url: HttpUrl
    terminal_modifications: tuple[str, ...] = ()
    known_targets: tuple[PeptideTargetAnnotation, ...]
    reported_biological_context: tuple[str, ...]
    available_structures: tuple[PeptideStructureAnnotation, ...] = ()
    evidence_stage: str
    measured_properties: dict[str, float | str] = Field(default_factory=dict)
    annotation_limitations: tuple[str, ...]

    @model_validator(mode="after")
    def validate_sequence(self) -> KnownPeptide:
        sequence = self.sequence.strip().upper()
        if sequence != self.sequence or not sequence:
            raise ValueError("known peptide sequences must be non-empty uppercase strings")
        invalid = sorted(set(sequence) - set(_AMINO_ACIDS))
        if invalid:
            raise ValueError(f"unsupported amino-acid codes: {', '.join(invalid)}")
        return self


class AminoAcidComposition(DomainModel):
    counts: dict[str, int]
    fractions: dict[str, float]


class CalculatedPeptideProperties(DomainModel):
    sequence_length: int
    amino_acid_composition: AminoAcidComposition
    approximate_molecular_weight_da: float
    estimated_net_charge: float
    charge_pH: float
    estimated_isoelectric_point: float | None
    mean_kyte_doolittle_hydrophobicity: float
    signed_charge_density: float
    absolute_charge_density: float
    alpha_helix_hydrophobic_moment: float
    beta_strand_hydrophobic_moment: float
    normalized_sequence_entropy: float


class PeptideModelPredictions(DomainModel):
    amphipathicity_indicator: Literal["low", "moderate", "high"]
    rule: str
    unsupported_activity_prediction: Literal[False] = False


class KnownPeptideAnalysis(DomainModel):
    peptide: KnownPeptide
    measured_properties: dict[str, float | str]
    calculated_properties: CalculatedPeptideProperties
    database_annotations: dict[str, Any]
    model_predictions: PeptideModelPredictions
    unsupported_assumptions: tuple[str, ...]
    calculation_notes: tuple[str, ...]
    safety_notice: str


class ConservedPosition(DomainModel):
    peptide_a_position: int
    peptide_b_position: int
    residue: str


class PeptideSequenceComparison(DomainModel):
    peptide_a: str
    peptide_b: str
    aligned_a: str
    aligned_b: str
    sequence_identity: float = Field(ge=0, le=1)
    conserved_positions: tuple[ConservedPosition, ...]
    scoring: dict[str, int]
    interpretation: str


class KnownPeptideRegistry:
    """Load the reviewable, versioned known-peptide pack."""

    def __init__(self, path: Path | None = None) -> None:
        source = path or self._default_path()
        try:
            raw = cast(dict[str, Any], json.loads(source.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not load known peptide registry from {source}") from exc
        self.version = str(raw["version"])
        self.notice = str(raw["notice"])
        peptides = tuple(
            KnownPeptide.model_validate(item) for item in cast(list[Any], raw["peptides"])
        )
        if len({item.slug for item in peptides}) != len(peptides):
            raise ValueError("known peptide slugs must be unique")
        self._peptides = {item.slug: item for item in peptides}

    @staticmethod
    def _default_path() -> Path:
        configured = os.getenv("CAUSALBIO_WORKSPACE_ROOT")
        if configured:
            root = Path(configured).resolve()
        else:
            located_root = next(
                (
                    candidate
                    for candidate in Path(__file__).resolve().parents
                    if (candidate / "pyproject.toml").is_file()
                ),
                None,
            )
            if located_root is None:
                raise RuntimeError("Could not locate the CausalBio Lab workspace root")
            root = located_root
        return root / "data" / "demo" / "peptides" / "known-peptides.json"

    def list(self) -> tuple[KnownPeptide, ...]:
        return tuple(self._peptides[key] for key in sorted(self._peptides))

    def get(self, slug: str) -> KnownPeptide:
        try:
            return self._peptides[slug]
        except KeyError as exc:
            raise KeyError(f"Unknown known peptide: {slug}") from exc


def _is_amidated(peptide: KnownPeptide) -> bool:
    return any("amidation" in item.casefold() for item in peptide.terminal_modifications)


def estimated_net_charge(peptide: KnownPeptide, pH: float) -> float:
    """Estimate charge with Henderson-Hasselbalch terms and declared termini."""

    if not 0 <= pH <= 14:
        raise ValueError("pH must be between 0 and 14")
    counts = Counter(peptide.sequence)
    positive = 1.0 / (1.0 + 10.0 ** (pH - _N_TERMINUS_PKA))
    for residue in ("H", "K", "R"):
        positive += counts[residue] / (1.0 + 10.0 ** (pH - _SIDE_CHAIN_PKA[residue]))
    negative = 0.0 if _is_amidated(peptide) else 1.0 / (1.0 + 10.0 ** (_C_TERMINUS_PKA - pH))
    for residue in ("D", "E", "C", "Y"):
        negative += counts[residue] / (1.0 + 10.0 ** (_SIDE_CHAIN_PKA[residue] - pH))
    return float(positive - negative)


def _molecular_weight(peptide: KnownPeptide) -> float:
    weight = sum(_AVERAGE_FREE_AMINO_ACID_MASS[residue] for residue in peptide.sequence)
    weight -= _WATER_MASS * (len(peptide.sequence) - 1)
    if _is_amidated(peptide):
        weight += _AMIDATION_MASS_DELTA
    return weight


def _hydrophobic_moment(sequence: str, angle_degrees: float) -> float:
    angle = math.radians(angle_degrees)
    cosine = sum(
        _KYTE_DOOLITTLE[residue] * math.cos(index * angle) for index, residue in enumerate(sequence)
    )
    sine = sum(
        _KYTE_DOOLITTLE[residue] * math.sin(index * angle) for index, residue in enumerate(sequence)
    )
    return math.hypot(cosine, sine) / len(sequence)


def _sequence_entropy(sequence: str) -> float:
    counts = Counter(sequence)
    entropy = -sum(
        (count / len(sequence)) * math.log2(count / len(sequence)) for count in counts.values()
    )
    return entropy / math.log2(min(20, len(sequence))) if len(sequence) > 1 else 0.0


def analyze_known_peptide(slug: str, *, pH: float = 7.4) -> KnownPeptideAnalysis:
    """Calculate properties for one registry peptide without activity prediction."""

    peptide = KnownPeptideRegistry().get(slug)
    counts = Counter(peptide.sequence)
    composition = AminoAcidComposition(
        counts={residue: counts[residue] for residue in _AMINO_ACIDS},
        fractions={residue: counts[residue] / len(peptide.sequence) for residue in _AMINO_ACIDS},
    )
    charge = estimated_net_charge(peptide, pH)
    try:
        pI: float | None = float(
            brentq(lambda value: estimated_net_charge(peptide, value), 0.0, 14.0)
        )
    except ValueError:
        # An amidated peptide with no acidic side chains can approach neutrality
        # without crossing zero in the physical pH interval. Reporting no finite
        # root is more faithful than manufacturing a threshold-dependent pI.
        pI = None
    mean_hydrophobicity = sum(_KYTE_DOOLITTLE[item] for item in peptide.sequence) / len(
        peptide.sequence
    )
    alpha_moment = _hydrophobic_moment(peptide.sequence, 100.0)
    beta_moment = _hydrophobic_moment(peptide.sequence, 160.0)
    max_moment = max(alpha_moment, beta_moment)
    indicator: Literal["low", "moderate", "high"]
    if max_moment >= 1.5:
        indicator = "high"
    elif max_moment >= 0.75:
        indicator = "moderate"
    else:
        indicator = "low"
    calculated = CalculatedPeptideProperties(
        sequence_length=len(peptide.sequence),
        amino_acid_composition=composition,
        approximate_molecular_weight_da=_molecular_weight(peptide),
        estimated_net_charge=charge,
        charge_pH=pH,
        estimated_isoelectric_point=pI,
        mean_kyte_doolittle_hydrophobicity=mean_hydrophobicity,
        signed_charge_density=charge / len(peptide.sequence),
        absolute_charge_density=abs(charge) / len(peptide.sequence),
        alpha_helix_hydrophobic_moment=alpha_moment,
        beta_strand_hydrophobic_moment=beta_moment,
        normalized_sequence_entropy=_sequence_entropy(peptide.sequence),
    )
    return KnownPeptideAnalysis(
        peptide=peptide,
        measured_properties=peptide.measured_properties,
        calculated_properties=calculated,
        database_annotations={
            "precursor": peptide.precursor,
            "precursor_uniprot": peptide.precursor_uniprot,
            "known_targets": tuple(item.model_dump(mode="json") for item in peptide.known_targets),
            "reported_biological_context": peptide.reported_biological_context,
            "available_structures": tuple(
                item.model_dump(mode="json") for item in peptide.available_structures
            ),
            "evidence_stage": peptide.evidence_stage,
            "source_url": str(peptide.source_url),
        },
        model_predictions=PeptideModelPredictions(
            amphipathicity_indicator=indicator,
            rule=(
                "Heuristic label from max(alpha-helix 100-degree, beta-strand 160-degree) "
                "Kyte-Doolittle hydrophobic moment: low <0.75, moderate <1.5, high >=1.5."
            ),
        ),
        unsupported_assumptions=(
            "No sequence calculation establishes receptor binding, biological activity, delivery, efficacy, or safety.",
            "The charge estimate assumes independent ionizable groups and standard aqueous pKa values.",
            "The hydrophobic moments assume idealized residue angles rather than a measured conformation.",
        ),
        calculation_notes=(
            "Molecular weight uses average free amino-acid masses, subtracts water per peptide bond, and applies declared terminal amidation.",
            "Isoelectric point uses Brent root finding over pH 0-14; no value is reported when the explicit charge model has no finite zero crossing.",
            "Normalized Shannon entropy describes sequence diversity only.",
        ),
        safety_notice=(
            "Research annotation only. No novel sequence generation, synthesis protocol, dosing, "
            "personal-use guidance, or claim of activity or safety is provided."
        ),
    )


def _global_alignment(left: str, right: str) -> tuple[str, str]:
    match, mismatch, gap = 1, 0, -1
    scores = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    moves = [[""] * (len(right) + 1) for _ in range(len(left) + 1)]
    for row in range(1, len(left) + 1):
        scores[row][0] = row * gap
        moves[row][0] = "up"
    for column in range(1, len(right) + 1):
        scores[0][column] = column * gap
        moves[0][column] = "left"
    for row in range(1, len(left) + 1):
        for column in range(1, len(right) + 1):
            diagonal = scores[row - 1][column - 1] + (
                match if left[row - 1] == right[column - 1] else mismatch
            )
            candidates = (
                (diagonal, "diagonal"),
                (scores[row - 1][column] + gap, "up"),
                (scores[row][column - 1] + gap, "left"),
            )
            scores[row][column], moves[row][column] = max(
                candidates, key=lambda item: (item[0], item[1] == "diagonal", item[1] == "up")
            )
    aligned_left: list[str] = []
    aligned_right: list[str] = []
    row, column = len(left), len(right)
    while row or column:
        move = moves[row][column]
        if move == "diagonal":
            aligned_left.append(left[row - 1])
            aligned_right.append(right[column - 1])
            row -= 1
            column -= 1
        elif move == "up":
            aligned_left.append(left[row - 1])
            aligned_right.append("-")
            row -= 1
        else:
            aligned_left.append("-")
            aligned_right.append(right[column - 1])
            column -= 1
    return "".join(reversed(aligned_left)), "".join(reversed(aligned_right))


def compare_known_peptides(slug_a: str, slug_b: str) -> PeptideSequenceComparison:
    """Globally align two registry peptides and report literal conserved residues."""

    registry = KnownPeptideRegistry()
    peptide_a = registry.get(slug_a)
    peptide_b = registry.get(slug_b)
    aligned_a, aligned_b = _global_alignment(peptide_a.sequence, peptide_b.sequence)
    matches = sum(left == right for left, right in zip(aligned_a, aligned_b, strict=True))
    position_a = 0
    position_b = 0
    conserved: list[ConservedPosition] = []
    for left, right in zip(aligned_a, aligned_b, strict=True):
        position_a += int(left != "-")
        position_b += int(right != "-")
        if left == right and left != "-":
            conserved.append(
                ConservedPosition(
                    peptide_a_position=position_a,
                    peptide_b_position=position_b,
                    residue=left,
                )
            )
    return PeptideSequenceComparison(
        peptide_a=peptide_a.slug,
        peptide_b=peptide_b.slug,
        aligned_a=aligned_a,
        aligned_b=aligned_b,
        sequence_identity=matches / len(aligned_a),
        conserved_positions=tuple(conserved),
        scoring={"match": 1, "mismatch": 0, "gap": -1},
        interpretation=(
            "Global sequence identity and conserved positions are descriptive only; they do not "
            "establish shared targets, potency, efficacy, or safety."
        ),
    )
