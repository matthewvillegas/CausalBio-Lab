"""Execution engine for curated discrete and continuous Petri nets.

The engine deliberately supports only rate laws whose numerical semantics are
implemented here. It does not infer executable models from causal-graph edges.
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from typing import TypeAlias, cast
from uuid import NAMESPACE_URL, UUID, uuid5

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

from causalbio import __version__
from causalbio.domain.enums import PetriArcType, RateLawType, SimulationState
from causalbio.domain.models import (
    PetriArc,
    PetriModel,
    PetriTransition,
    SimulationParameters,
    SimulationRun,
)

Marking: TypeAlias = dict[UUID, float]
MarkingState: TypeAlias = tuple[tuple[UUID, float], ...]

_ABSOLUTE_TOLERANCE = 1e-10
_STATE_DECIMAL_PLACES = 12
_RUN_ID_NAMESPACE = "causalbio:petri-continuous:v3"
_MAX_DERIVATIVE_EVALUATIONS = 100_000

SAFETY_NOTICE = "Model-based simulation, not a personalized biological prediction."


class PetriEngineError(RuntimeError):
    """Base error for Petri-net execution."""


class PetriModelValidationError(PetriEngineError, ValueError):
    """Raised when an internally inconsistent model reaches the engine."""


class TransitionNotEnabledError(PetriEngineError):
    """Raised when a caller attempts to fire a disabled transition."""


class PetriSimulationError(PetriEngineError):
    """Raised when a continuous simulation cannot be completed faithfully."""


@dataclass(frozen=True, slots=True)
class ReachabilityEdge:
    """A directed edge in a finite reachability exploration."""

    source_index: int
    transition_id: UUID
    target_index: int


@dataclass(frozen=True, slots=True)
class ReachabilityResult:
    """Deterministically ordered states discovered by bounded breadth-first search.

    ``truncated`` is true whenever depth or state limits prevented exhaustive
    exploration. Callers must not interpret a truncated result as a boundedness
    proof.
    """

    markings: tuple[MarkingState, ...]
    edges: tuple[ReachabilityEdge, ...]
    deadlock_indices: tuple[int, ...]
    truncated: bool

    def marking(self, index: int) -> Marking:
        """Return one canonical state as a mutable marking copy."""

        return dict(self.markings[index])

    @property
    def deadlocks(self) -> tuple[MarkingState, ...]:
        """Return canonical states with no enabled transitions."""

        return tuple(self.markings[index] for index in self.deadlock_indices)


class PetriEngine:
    """Validate and execute one curated Petri model."""

    def __init__(self, model: PetriModel) -> None:
        self.model = model
        self._validate_model(model)

        self._places = tuple(sorted(model.places, key=lambda place: str(place.id)))
        self._transitions = tuple(
            sorted(model.transitions, key=lambda transition: str(transition.id))
        )
        self._place_by_id = {place.id: place for place in self._places}
        self._transition_by_id = {transition.id: transition for transition in self._transitions}
        self._arcs_by_transition = {
            transition.id: tuple(
                sorted(
                    (arc for arc in model.arcs if arc.transition_id == transition.id),
                    key=lambda arc: str(arc.id),
                )
            )
            for transition in self._transitions
        }
        self._stoichiometry = {
            transition.id: self._transition_stoichiometry(transition.id)
            for transition in self._transitions
        }

    @staticmethod
    def _validate_model(model: PetriModel) -> None:
        if not model.places:
            raise PetriModelValidationError("A Petri model needs at least one place")
        if not model.transitions:
            raise PetriModelValidationError("A Petri model needs at least one transition")

        place_ids = [place.id for place in model.places]
        transition_ids = [transition.id for transition in model.transitions]
        arc_ids = [arc.id for arc in model.arcs]
        PetriEngine._require_unique(place_ids, "place")
        PetriEngine._require_unique(transition_ids, "transition")
        PetriEngine._require_unique(arc_ids, "arc")

        place_id_set = set(place_ids)
        transition_id_set = set(transition_ids)
        for place in model.places:
            if not all(
                isfinite(value) for value in (place.valid_min, place.valid_max, place.initial_value)
            ):
                raise PetriModelValidationError(
                    f"Place {place.id} has a non-finite range or initial value"
                )
            if place.valid_min < 0:
                raise PetriModelValidationError(
                    f"Place {place.id} has a negative minimum; token values must be non-negative"
                )
            if place.valid_max <= place.valid_min:
                raise PetriModelValidationError(
                    f"Place {place.id} must have valid_max greater than valid_min"
                )

        arc_keys: set[tuple[UUID, UUID, PetriArcType]] = set()
        state_changing_transitions: set[UUID] = set()
        for arc in model.arcs:
            if arc.place_id not in place_id_set:
                raise PetriModelValidationError(
                    f"Arc {arc.id} references unknown place {arc.place_id}"
                )
            if arc.transition_id not in transition_id_set:
                raise PetriModelValidationError(
                    f"Arc {arc.id} references unknown transition {arc.transition_id}"
                )
            if not isfinite(arc.weight) or not isfinite(arc.threshold):
                raise PetriModelValidationError(f"Arc {arc.id} has a non-finite value")
            key = (arc.place_id, arc.transition_id, arc.arc_type)
            if key in arc_keys:
                raise PetriModelValidationError(
                    "Duplicate arcs with the same place, transition, and type are ambiguous"
                )
            arc_keys.add(key)
            if arc.arc_type in {PetriArcType.INPUT, PetriArcType.OUTPUT}:
                state_changing_transitions.add(arc.transition_id)

        for transition in model.transitions:
            if transition.id not in state_changing_transitions:
                raise PetriModelValidationError(
                    f"Transition {transition.id} has no input or output arc"
                )
            PetriEngine._validate_rate_law(transition)

    @staticmethod
    def _require_unique(values: list[UUID], kind: str) -> None:
        if len(values) != len(set(values)):
            raise PetriModelValidationError(f"Petri {kind} identifiers must be unique")

    @staticmethod
    def _validate_rate_law(transition: PetriTransition) -> None:
        expected_parameter = PetriEngine._rate_parameter_name(transition.rate_law)
        if expected_parameter not in transition.parameters:
            raise PetriModelValidationError(
                f"Transition {transition.id} requires parameter '{expected_parameter}'"
            )
        for name, value in transition.parameters.items():
            if not isfinite(value) or value < 0:
                raise PetriModelValidationError(
                    f"Transition {transition.id} parameter '{name}' must be finite and non-negative"
                )

    @staticmethod
    def _rate_parameter_name(rate_law: RateLawType) -> str:
        if rate_law is RateLawType.CONSTANT:
            return "rate"
        if rate_law is RateLawType.MASS_ACTION:
            return "rate_constant"
        raise PetriModelValidationError(
            f"Rate law '{rate_law.value}' is not implemented by this engine"
        )

    def _transition_stoichiometry(self, transition_id: UUID) -> dict[UUID, float]:
        changes = {place.id: 0.0 for place in self._places}
        for arc in self._arcs_for(transition_id):
            if arc.arc_type is PetriArcType.INPUT:
                changes[arc.place_id] -= arc.weight
            elif arc.arc_type is PetriArcType.OUTPUT:
                changes[arc.place_id] += arc.weight
        return {place_id: change for place_id, change in changes.items() if change != 0.0}

    def _arcs_for(self, transition_id: UUID) -> tuple[PetriArc, ...]:
        # During __init__, this helper is called before the cached mapping exists.
        if hasattr(self, "_arcs_by_transition"):
            return self._arcs_by_transition[transition_id]
        return tuple(
            sorted(
                (arc for arc in self.model.arcs if arc.transition_id == transition_id),
                key=lambda arc: str(arc.id),
            )
        )

    def initial_marking(self, overrides: Mapping[UUID | str, float] | None = None) -> Marking:
        """Build a complete initial marking, optionally overriding IDs or unique names."""

        marking = {place.id: float(place.initial_value) for place in self._places}
        resolved: set[UUID] = set()
        for reference, value in (overrides or {}).items():
            place_id = self._resolve_place_reference(reference)
            if place_id in resolved:
                raise PetriModelValidationError(
                    f"Multiple initial overrides resolve to place {place_id}"
                )
            resolved.add(place_id)
            marking[place_id] = float(value)
        return self.validate_marking(marking)

    def validate_marking(self, marking: Mapping[UUID, float]) -> Marking:
        """Validate a complete or sparse marking and return a canonical full copy.

        Omitted places default to zero, provided zero is in the place's valid range.
        """

        unknown = set(marking) - set(self._place_by_id)
        if unknown:
            unknown_text = ", ".join(sorted(str(identifier) for identifier in unknown))
            raise PetriModelValidationError(f"Marking contains unknown places: {unknown_text}")

        normalized: Marking = {}
        for place in self._places:
            value = float(marking.get(place.id, 0.0))
            if not isfinite(value):
                raise PetriModelValidationError(f"Marking for place {place.id} must be finite")
            if value < place.valid_min - _ABSOLUTE_TOLERANCE:
                raise PetriModelValidationError(
                    f"Marking for place {place.id} is below its valid minimum"
                )
            if value > place.valid_max + _ABSOLUTE_TOLERANCE:
                raise PetriModelValidationError(
                    f"Marking for place {place.id} is above its valid maximum"
                )
            value = min(max(value, place.valid_min), place.valid_max)
            normalized[place.id] = self._stable_number(value)
        return normalized

    def enabled_transitions(self, marking: Mapping[UUID, float]) -> tuple[PetriTransition, ...]:
        """Return enabled transitions in stable UUID order."""

        normalized = self.validate_marking(marking)
        return tuple(
            transition
            for transition in self._transitions
            if self._is_enabled_normalized(transition.id, normalized)
        )

    def enabled_transition_ids(self, marking: Mapping[UUID, float]) -> tuple[UUID, ...]:
        """Return stable identifiers for all enabled transitions."""

        return tuple(transition.id for transition in self.enabled_transitions(marking))

    def is_enabled(self, transition: UUID | PetriTransition, marking: Mapping[UUID, float]) -> bool:
        """Return whether one transition may fire at the supplied marking."""

        transition_id = self._resolve_transition(transition).id
        return self._is_enabled_normalized(transition_id, self.validate_marking(marking))

    def _is_enabled_normalized(self, transition_id: UUID, marking: Marking) -> bool:
        for arc in self._arcs_for(transition_id):
            value = marking[arc.place_id]
            if arc.arc_type is PetriArcType.INPUT:
                required = max(arc.weight, arc.threshold)
                if value + _ABSOLUTE_TOLERANCE < required:
                    return False
            elif arc.arc_type is PetriArcType.READ:
                if value + _ABSOLUTE_TOLERANCE < self._modifier_threshold(arc):
                    return False
            elif arc.arc_type is PetriArcType.INHIBITORY:
                if value >= self._modifier_threshold(arc) - _ABSOLUTE_TOLERANCE:
                    return False

        for place_id, change in self._stoichiometry[transition_id].items():
            place = self._place_by_id[place_id]
            candidate = marking[place_id] + change
            if candidate < place.valid_min - _ABSOLUTE_TOLERANCE:
                return False
            if candidate > place.valid_max + _ABSOLUTE_TOLERANCE:
                return False
        return True

    @staticmethod
    def _modifier_threshold(arc: PetriArc) -> float:
        # A positive explicit threshold wins. Weight is the conventional
        # read/inhibitor threshold and keeps default-threshold models useful.
        return arc.threshold if arc.threshold > 0 else arc.weight

    def fire(self, transition: UUID | PetriTransition, marking: Mapping[UUID, float]) -> Marking:
        """Fire an enabled transition without mutating the caller's marking."""

        resolved = self._resolve_transition(transition)
        normalized = self.validate_marking(marking)
        if not self._is_enabled_normalized(resolved.id, normalized):
            raise TransitionNotEnabledError(
                f"Transition {resolved.id} is not enabled at the supplied marking"
            )
        result = normalized.copy()
        for place_id, change in self._stoichiometry[resolved.id].items():
            result[place_id] = self._stable_number(result[place_id] + change)
        return self.validate_marking(result)

    def is_deadlocked(self, marking: Mapping[UUID, float]) -> bool:
        """Return true when no transition can fire."""

        return not self.enabled_transitions(marking)

    def explore_reachability(
        self,
        marking: Mapping[UUID, float] | None = None,
        *,
        max_depth: int = 100,
        max_states: int = 1000,
    ) -> ReachabilityResult:
        """Explore a small discrete state space with deterministic breadth-first search."""

        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")
        if max_states < 1:
            raise ValueError("max_states must be at least one")

        start_source = self.initial_marking() if marking is None else marking
        start = self.validate_marking(start_source)
        start_state = self._marking_state(start)
        states: list[MarkingState] = [start_state]
        state_indices = {start_state: 0}
        queue: deque[tuple[int, int]] = deque([(0, 0)])
        edges: list[ReachabilityEdge] = []
        deadlocks: list[int] = []
        truncated = False

        while queue:
            source_index, depth = queue.popleft()
            current = dict(states[source_index])
            enabled = self.enabled_transitions(current)
            if not enabled:
                deadlocks.append(source_index)
                continue
            if depth >= max_depth:
                truncated = True
                continue

            for transition in enabled:
                target = self.fire(transition, current)
                target_state = self._marking_state(target)
                target_index = state_indices.get(target_state)
                if target_index is None:
                    if len(states) >= max_states:
                        truncated = True
                        continue
                    target_index = len(states)
                    state_indices[target_state] = target_index
                    states.append(target_state)
                    queue.append((target_index, depth + 1))
                edges.append(
                    ReachabilityEdge(
                        source_index=source_index,
                        transition_id=transition.id,
                        target_index=target_index,
                    )
                )

        return ReachabilityResult(
            markings=tuple(states),
            edges=tuple(edges),
            deadlock_indices=tuple(deadlocks),
            truncated=truncated,
        )

    def reachable_markings(
        self,
        marking: Mapping[UUID, float] | None = None,
        *,
        max_depth: int = 100,
        max_states: int = 1000,
    ) -> tuple[Marking, ...]:
        """Convenience view of states returned by :meth:`explore_reachability`."""

        result = self.explore_reachability(marking, max_depth=max_depth, max_states=max_states)
        return tuple(dict(state) for state in result.markings)

    def simulate_continuous(self, parameters: SimulationParameters) -> SimulationRun:
        """Integrate supported constant and mass-action transitions as an ODE system.

        Read arcs are hard prerequisite gates and inhibitory arcs are hard upper
        threshold gates. Neither modifier changes its place directly. Input and
        output arc weights define stoichiometric coefficients; mass-action input
        weights also define kinetic orders.
        """

        if parameters.model_id != self.model.id:
            raise PetriModelValidationError(
                "Simulation parameters reference a different Petri model"
            )

        initial = self.initial_marking(
            cast(Mapping[UUID | str, float], parameters.initial_overrides)
        )
        transition_parameters = self._effective_transition_parameters(
            parameters.parameter_overrides
        )
        initial_vector = np.asarray([initial[place.id] for place in self._places], dtype=np.float64)
        times = np.linspace(0.0, float(parameters.duration), parameters.steps, dtype=np.float64)
        evaluations = 0

        def derivative(_time: float, state: NDArray[np.float64]) -> NDArray[np.float64]:
            nonlocal evaluations
            evaluations += 1
            if evaluations > _MAX_DERIVATIVE_EVALUATIONS:
                raise PetriSimulationError(
                    "The continuous solver exceeded its evaluation budget. Hard-gate chattering "
                    "or stiff kinetics may require another model or solver; no complete result is available."
                )
            rates = self._all_effective_rates(state, transition_parameters)
            result = np.zeros(len(self._places), dtype=np.float64)
            for transition_index, transition in enumerate(self._transitions):
                rate = rates[transition_index]
                for place_id, coefficient in self._stoichiometry[transition.id].items():
                    result[self._place_index(place_id)] += coefficient * rate
            return result

        max_step = float(parameters.duration) / float(parameters.steps - 1)
        solution = solve_ivp(
            derivative,
            (0.0, float(parameters.duration)),
            initial_vector,
            t_eval=times,
            method="RK45",
            rtol=1e-8,
            atol=1e-10,
            max_step=max_step,
        )
        if not solution.success:
            raise PetriSimulationError(f"SciPy ODE integration failed: {solution.message}")
        raw_values = np.asarray(solution.y, dtype=np.float64)
        if raw_values.shape != (len(self._places), parameters.steps):
            raise PetriSimulationError("SciPy returned an incomplete simulation trajectory")
        if not np.all(np.isfinite(raw_values)):
            raise PetriSimulationError("Simulation produced non-finite trajectory values")

        values = raw_values.copy()
        warnings: list[str] = []
        constrained = False
        for index, place in enumerate(self._places):
            below = values[index] < place.valid_min - _ABSOLUTE_TOLERANCE
            above = values[index] > place.valid_max + _ABSOLUTE_TOLERANCE
            constrained = constrained or bool(np.any(below) or np.any(above))
            values[index] = np.clip(values[index], place.valid_min, place.valid_max)
        if constrained:
            warnings.append(
                "Numerical trajectories reached declared place bounds and were constrained to valid ranges."
            )

        activity_matrix = np.column_stack(
            [
                self._all_effective_rates(values[:, index], transition_parameters)
                for index in range(parameters.steps)
            ]
        )
        trajectories = {
            str(place.id): tuple(float(value) for value in values[index])
            for index, place in enumerate(self._places)
        }
        transition_activity = {
            str(transition.id): tuple(float(value) for value in activity_matrix[index])
            for index, transition in enumerate(self._transitions)
        }

        return SimulationRun(
            id=self._simulation_run_id(parameters),
            state=SimulationState.COMPLETE,
            model_id=self.model.id,
            parameters=parameters,
            times=tuple(float(value) for value in times),
            trajectories=trajectories,
            transition_activity=transition_activity,
            summary=(
                SAFETY_NOTICE,
                f"Continuous ODE simulation completed for curated model '{self.model.name}'.",
                "Transition activity uses explicit constant or mass-action kinetics with declared arc modifiers.",
            ),
            warnings=tuple(warnings),
            software_version=__version__,
            model_version=self.model.model_version,
        )

    def _all_effective_rates(
        self,
        state: NDArray[np.float64],
        transition_parameters: Mapping[UUID, Mapping[str, float]],
    ) -> NDArray[np.float64]:
        return np.asarray(
            [
                self._effective_rate(transition, state, transition_parameters[transition.id])
                for transition in self._transitions
            ],
            dtype=np.float64,
        )

    def _effective_rate(
        self,
        transition: PetriTransition,
        state: NDArray[np.float64],
        parameters: Mapping[str, float],
    ) -> float:
        arcs = self._arcs_for(transition.id)
        for arc in arcs:
            value = max(float(state[self._place_index(arc.place_id)]), 0.0)
            # A constant-rate self-loop still needs its substrate to exist,
            # even when matching output cancels the input in the net stoichiometry.
            if arc.arc_type is PetriArcType.INPUT and value <= 0:
                return 0.0
            threshold = self._modifier_threshold(arc)
            if arc.arc_type is PetriArcType.READ and value < threshold:
                return 0.0
            if arc.arc_type is PetriArcType.INHIBITORY and value >= threshold:
                return 0.0

        parameter_name = self._rate_parameter_name(transition.rate_law)
        rate = float(parameters[parameter_name])
        if transition.rate_law is RateLawType.MASS_ACTION:
            for arc in arcs:
                if arc.arc_type is PetriArcType.INPUT:
                    concentration = max(float(state[self._place_index(arc.place_id)]), 0.0)
                    rate *= concentration**arc.weight

        if not isfinite(rate):
            raise PetriSimulationError(f"Transition {transition.id} produced a non-finite rate")

        # Prevent a transition from pushing a bounded place farther past a
        # declared boundary. Applying this per transition preserves its
        # stoichiometric coupling better than clipping individual derivatives.
        for place_id, coefficient in self._stoichiometry[transition.id].items():
            place = self._place_by_id[place_id]
            value = float(state[self._place_index(place_id)])
            if coefficient < 0 and value <= place.valid_min + _ABSOLUTE_TOLERANCE:
                return 0.0
            if coefficient > 0 and value >= place.valid_max - _ABSOLUTE_TOLERANCE:
                return 0.0
        return rate

    def _effective_transition_parameters(
        self, overrides: Mapping[str, float]
    ) -> dict[UUID, dict[str, float]]:
        result = {transition.id: dict(transition.parameters) for transition in self._transitions}
        resolved_keys: set[tuple[UUID, str]] = set()
        for reference, value in overrides.items():
            if not isfinite(value) or value < 0:
                raise PetriModelValidationError(
                    f"Parameter override '{reference}' must be finite and non-negative"
                )
            transition_id, parameter_name = self._resolve_parameter_reference(reference)
            key = (transition_id, parameter_name)
            if key in resolved_keys:
                raise PetriModelValidationError(
                    f"Multiple overrides resolve to transition parameter '{reference}'"
                )
            resolved_keys.add(key)
            result[transition_id][parameter_name] = float(value)
        return result

    def _resolve_parameter_reference(self, reference: str) -> tuple[UUID, str]:
        transition_reference, separator, parameter_name = reference.rpartition(".")
        if separator:
            transition = self._resolve_transition_reference(transition_reference)
            if parameter_name not in transition.parameters:
                raise PetriModelValidationError(
                    f"Transition {transition.id} has no parameter '{parameter_name}'"
                )
            return transition.id, parameter_name

        candidates = [
            transition for transition in self._transitions if reference in transition.parameters
        ]
        if len(candidates) != 1:
            raise PetriModelValidationError(
                f"Unqualified parameter '{reference}' must identify exactly one transition"
            )
        return candidates[0].id, reference

    def _resolve_place_reference(self, reference: UUID | str) -> UUID:
        if isinstance(reference, UUID):
            if reference in self._place_by_id:
                return reference
            raise PetriModelValidationError(f"Unknown place {reference}")
        try:
            identifier = UUID(reference)
        except ValueError:
            matches = [place.id for place in self._places if place.name == reference]
            if len(matches) != 1:
                raise PetriModelValidationError(
                    f"Place name '{reference}' must identify exactly one place"
                ) from None
            return matches[0]
        if identifier not in self._place_by_id:
            raise PetriModelValidationError(f"Unknown place {identifier}")
        return identifier

    def _resolve_transition_reference(self, reference: str) -> PetriTransition:
        try:
            identifier = UUID(reference)
        except ValueError:
            matches = [
                transition for transition in self._transitions if transition.name == reference
            ]
            if len(matches) != 1:
                raise PetriModelValidationError(
                    f"Transition name '{reference}' must identify exactly one transition"
                ) from None
            return matches[0]
        return self._resolve_transition(identifier)

    def _resolve_transition(self, transition: UUID | PetriTransition) -> PetriTransition:
        identifier = transition.id if isinstance(transition, PetriTransition) else transition
        try:
            return self._transition_by_id[identifier]
        except KeyError as error:
            raise PetriModelValidationError(f"Unknown transition {identifier}") from error

    def _place_index(self, place_id: UUID) -> int:
        # Models are small and this keeps the cached representation immutable.
        return next(index for index, place in enumerate(self._places) if place.id == place_id)

    def _marking_state(self, marking: Mapping[UUID, float]) -> MarkingState:
        return tuple((place.id, self._stable_number(marking[place.id])) for place in self._places)

    @staticmethod
    def _stable_number(value: float) -> float:
        rounded = round(float(value), _STATE_DECIMAL_PLACES)
        return 0.0 if abs(rounded) < 10 ** (-_STATE_DECIMAL_PLACES) else rounded

    def _simulation_run_id(self, parameters: SimulationParameters) -> UUID:
        payload = json.dumps(
            {
                "model": self.model.model_dump(mode="json"),
                "parameters": parameters.model_dump(mode="json"),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return uuid5(
            NAMESPACE_URL,
            f"{_RUN_ID_NAMESPACE}:{self.model.model_version}:{payload}",
        )


__all__ = [
    "SAFETY_NOTICE",
    "Marking",
    "MarkingState",
    "PetriEngine",
    "PetriEngineError",
    "PetriModelValidationError",
    "PetriSimulationError",
    "ReachabilityEdge",
    "ReachabilityResult",
    "TransitionNotEnabledError",
]
