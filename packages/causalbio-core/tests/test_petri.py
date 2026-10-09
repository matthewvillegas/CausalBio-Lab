"""Focused tests for validated Petri-net execution."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

import numpy as np
import pytest
from causalbio.domain.enums import PetriArcType, RateLawType, SimulationState
from causalbio.domain.models import (
    PetriArc,
    PetriModel,
    PetriPlace,
    PetriTransition,
    SimulationParameters,
)
from causalbio.petri import (
    PetriEngine,
    PetriModelValidationError,
    PetriSimulationError,
    TransitionNotEnabledError,
)
from causalbio.petri import engine as engine_module


def uid(value: int) -> UUID:
    return UUID(int=value)


def place(
    value: int,
    name: str,
    initial: float,
    *,
    valid_max: float = 10.0,
) -> PetriPlace:
    return PetriPlace(
        id=uid(value),
        name=name,
        description=f"Curated state variable for {name}",
        representation="tokens or normalized concentration",
        units="dimensionless",
        compartment="test compartment",
        valid_min=0.0,
        valid_max=valid_max,
        initial_value=initial,
    )


def transition(
    value: int,
    name: str,
    *,
    rate_law: RateLawType = RateLawType.CONSTANT,
    parameters: dict[str, float] | None = None,
) -> PetriTransition:
    default_parameters = {"rate": 1.0 if rate_law is RateLawType.CONSTANT else 0.5}
    if rate_law is RateLawType.MASS_ACTION:
        default_parameters = {"rate_constant": 0.5}
    return PetriTransition(
        id=uid(value),
        name=name,
        biological_event=f"Curated event for {name}",
        rate_law=rate_law,
        parameters=parameters or default_parameters,
        evidence_ids=(),
        assumptions=("Synthetic test model only.",),
    )


def arc(
    value: int,
    place_id: UUID,
    transition_id: UUID,
    arc_type: PetriArcType,
    *,
    weight: float = 1.0,
    threshold: float = 0.0,
) -> PetriArc:
    return PetriArc(
        id=uid(value),
        place_id=place_id,
        transition_id=transition_id,
        arc_type=arc_type,
        weight=weight,
        threshold=threshold,
    )


def model(
    places: Iterable[PetriPlace],
    transitions: Iterable[PetriTransition],
    arcs: Iterable[PetriArc],
    *,
    value: int = 1000,
) -> PetriModel:
    return PetriModel(
        id=uid(value),
        slug=f"test-model-{value}",
        name="Curated synthetic test model",
        description="A deterministic synthetic model for engine tests.",
        model_version="1.0.0",
        places=tuple(places),
        transitions=tuple(transitions),
        arcs=tuple(arcs),
        assumptions=("Educational synthetic behavior, not a biological prediction.",),
    )


def test_enabled_and_fire_respect_input_output_read_and_inhibitory_arcs() -> None:
    substrate = place(1, "substrate", 2.0)
    product = place(2, "product", 0.0)
    catalyst = place(3, "catalyst", 1.0)
    inhibitor = place(4, "inhibitor", 0.0)
    conversion = transition(10, "conversion")
    engine = PetriEngine(
        model(
            [substrate, product, catalyst, inhibitor],
            [conversion],
            [
                arc(20, substrate.id, conversion.id, PetriArcType.INPUT, weight=2.0),
                arc(21, product.id, conversion.id, PetriArcType.OUTPUT),
                arc(
                    22,
                    catalyst.id,
                    conversion.id,
                    PetriArcType.READ,
                    threshold=1.0,
                ),
                arc(
                    23,
                    inhibitor.id,
                    conversion.id,
                    PetriArcType.INHIBITORY,
                    threshold=1.0,
                ),
            ],
        )
    )

    initial = engine.initial_marking()
    assert engine.enabled_transition_ids(initial) == (conversion.id,)

    fired = engine.fire(conversion.id, initial)
    assert fired[substrate.id] == 0.0
    assert fired[product.id] == 1.0
    assert fired[catalyst.id] == initial[catalyst.id]
    assert fired[inhibitor.id] == initial[inhibitor.id]
    assert initial[substrate.id] == 2.0  # firing never mutates caller state
    assert engine.is_deadlocked(fired)

    inhibited = engine.initial_marking({inhibitor.id: 1.0})
    assert not engine.is_enabled(conversion.id, inhibited)
    with pytest.raises(TransitionNotEnabledError):
        engine.fire(conversion.id, inhibited)


def test_read_arc_weight_is_the_default_threshold() -> None:
    source = place(1, "source", 1.0)
    product = place(2, "product", 0.0)
    read_marker = place(3, "read marker", 1.0)
    event = transition(10, "event")
    engine = PetriEngine(
        model(
            [source, product, read_marker],
            [event],
            [
                arc(20, source.id, event.id, PetriArcType.INPUT),
                arc(21, product.id, event.id, PetriArcType.OUTPUT),
                arc(22, read_marker.id, event.id, PetriArcType.READ, weight=2.0),
            ],
        )
    )

    assert not engine.is_enabled(event, engine.initial_marking())
    assert engine.is_enabled(event, engine.initial_marking({read_marker.id: 2.0}))


def test_reachability_finds_deadlock_in_stable_breadth_first_order() -> None:
    available = place(1, "available", 2.0, valid_max=2.0)
    used = place(2, "used", 0.0, valid_max=2.0)
    consume = transition(10, "consume")
    engine = PetriEngine(
        model(
            [available, used],
            [consume],
            [
                arc(20, available.id, consume.id, PetriArcType.INPUT),
                arc(21, used.id, consume.id, PetriArcType.OUTPUT),
            ],
        )
    )

    result = engine.explore_reachability()
    assert result.truncated is False
    assert len(result.markings) == 3
    assert [result.marking(index)[available.id] for index in range(3)] == [2.0, 1.0, 0.0]
    assert result.deadlock_indices == (2,)
    assert result.deadlocks == (result.markings[2],)
    assert tuple(edge.transition_id for edge in result.edges) == (consume.id, consume.id)
    assert engine.is_deadlocked(result.marking(2))


def test_reachability_reports_truncation_instead_of_implying_boundedness() -> None:
    accumulator = place(1, "accumulator", 0.0, valid_max=100.0)
    produce = transition(10, "produce")
    engine = PetriEngine(
        model(
            [accumulator],
            [produce],
            [arc(20, accumulator.id, produce.id, PetriArcType.OUTPUT)],
        )
    )

    result = engine.explore_reachability(max_depth=2)
    assert len(result.markings) == 3
    assert result.truncated is True
    assert result.deadlocks == ()


def test_engine_rejects_dangling_arcs_and_unsupported_rate_laws() -> None:
    state = place(1, "state", 1.0)
    event = transition(10, "event")
    dangling = arc(20, uid(999), event.id, PetriArcType.INPUT)
    with pytest.raises(PetriModelValidationError, match="unknown place"):
        PetriEngine(model([state], [event], [dangling]))

    unsupported = transition(
        11,
        "unsupported",
        rate_law=RateLawType.HILL_ACTIVATION,
        parameters={"rate": 1.0},
    )
    with pytest.raises(PetriModelValidationError, match="not implemented"):
        PetriEngine(
            model(
                [state],
                [unsupported],
                [arc(21, state.id, unsupported.id, PetriArcType.OUTPUT)],
            )
        )


def test_constant_ode_simulation_is_reproducible_and_bounded() -> None:
    accumulated = place(1, "accumulated", 0.0, valid_max=10.0)
    source = transition(10, "constant source", parameters={"rate": 2.0})
    petri_model = model(
        [accumulated],
        [source],
        [arc(20, accumulated.id, source.id, PetriArcType.OUTPUT)],
    )
    engine = PetriEngine(petri_model)
    parameters = SimulationParameters(
        model_id=petri_model.id,
        duration=2.0,
        steps=9,
        seed=7,
    )

    first = engine.simulate_continuous(parameters)
    second = engine.simulate_continuous(parameters)

    assert first == second
    assert first.id == second.id
    assert first.state is SimulationState.COMPLETE
    assert first.trajectories[str(accumulated.id)] == pytest.approx(
        np.linspace(0.0, 4.0, 9), abs=1e-7
    )
    assert first.transition_activity[str(source.id)] == pytest.approx((2.0,) * 9)
    assert "not a personalized biological prediction" in first.summary[0]


def test_mass_action_ode_uses_read_and_inhibitory_gates() -> None:
    substrate = place(1, "substrate", 2.0, valid_max=3.0)
    product = place(2, "product", 0.0, valid_max=3.0)
    catalyst = place(3, "catalyst", 1.0, valid_max=2.0)
    inhibitor = place(4, "inhibitor", 0.0, valid_max=2.0)
    conversion = transition(
        10,
        "conversion",
        rate_law=RateLawType.MASS_ACTION,
        parameters={"rate_constant": 0.5},
    )
    petri_model = model(
        [substrate, product, catalyst, inhibitor],
        [conversion],
        [
            arc(20, substrate.id, conversion.id, PetriArcType.INPUT),
            arc(21, product.id, conversion.id, PetriArcType.OUTPUT),
            arc(
                22,
                catalyst.id,
                conversion.id,
                PetriArcType.READ,
                threshold=1.0,
            ),
            arc(
                23,
                inhibitor.id,
                conversion.id,
                PetriArcType.INHIBITORY,
                threshold=1.0,
            ),
        ],
    )
    engine = PetriEngine(petri_model)
    active_parameters = SimulationParameters(
        model_id=petri_model.id,
        duration=2.0,
        steps=11,
    )
    active = engine.simulate_continuous(active_parameters)

    expected_substrate = 2.0 * np.exp(-0.5 * np.asarray(active.times))
    assert active.trajectories[str(substrate.id)] == pytest.approx(
        expected_substrate, rel=2e-6, abs=2e-7
    )
    assert active.trajectories[str(product.id)] == pytest.approx(
        2.0 - expected_substrate, rel=2e-6, abs=2e-7
    )

    inhibited = engine.simulate_continuous(
        active_parameters.model_copy(update={"initial_overrides": {str(inhibitor.id): 1.0}})
    )
    assert inhibited.trajectories[str(substrate.id)] == pytest.approx((2.0,) * 11)
    assert inhibited.trajectories[str(product.id)] == pytest.approx((0.0,) * 11)
    assert inhibited.transition_activity[str(conversion.id)] == pytest.approx((0.0,) * 11)


def test_continuous_parameter_overrides_are_explicit_and_deterministic() -> None:
    accumulated = place(1, "accumulated", 0.0)
    source = transition(10, "constant source", parameters={"rate": 1.0})
    petri_model = model(
        [accumulated],
        [source],
        [arc(20, accumulated.id, source.id, PetriArcType.OUTPUT)],
    )
    engine = PetriEngine(petri_model)
    parameters = SimulationParameters(
        model_id=petri_model.id,
        duration=1.0,
        steps=5,
        parameter_overrides={f"{source.id}.rate": 3.0},
    )

    run = engine.simulate_continuous(parameters)
    assert run.trajectories[str(accumulated.id)][-1] == pytest.approx(3.0)

    with pytest.raises(PetriModelValidationError, match="has no parameter"):
        engine.simulate_continuous(
            parameters.model_copy(update={"parameter_overrides": {f"{source.id}.unknown": 3.0}})
        )


def test_reversible_mass_action_conserves_total_and_approaches_analytic_equilibrium() -> None:
    a, b = place(1, "A", 3.0), place(2, "B", 1.0)
    forward = transition(
        10, "forward", rate_law=RateLawType.MASS_ACTION, parameters={"rate_constant": 0.7}
    )
    reverse = transition(
        11, "reverse", rate_law=RateLawType.MASS_ACTION, parameters={"rate_constant": 0.3}
    )
    net = model(
        [a, b],
        [forward, reverse],
        [
            arc(20, a.id, forward.id, PetriArcType.INPUT),
            arc(21, b.id, forward.id, PetriArcType.OUTPUT),
            arc(22, b.id, reverse.id, PetriArcType.INPUT),
            arc(23, a.id, reverse.id, PetriArcType.OUTPUT),
        ],
    )
    run = PetriEngine(net).simulate_continuous(
        SimulationParameters(model_id=net.id, duration=20, steps=81)
    )
    observed_a = np.asarray(run.trajectories[str(a.id)])
    observed_b = np.asarray(run.trajectories[str(b.id)])
    equilibrium_a = 4 * 0.3 / (0.7 + 0.3)
    analytic_a = equilibrium_a + (3 - equilibrium_a) * np.exp(-np.asarray(run.times))
    np.testing.assert_allclose(observed_a, analytic_a, atol=2e-8)
    np.testing.assert_allclose(observed_a + observed_b, 4, atol=1e-12)
    assert observed_a[-1] == pytest.approx(equilibrium_a, abs=1e-8)
    assert run.transition_activity[str(forward.id)][-1] == pytest.approx(
        run.transition_activity[str(reverse.id)][-1], abs=1e-8
    )
    assert not run.warnings


def test_weighted_reaction_conserves_stoichiometric_invariant_in_both_modes() -> None:
    a, b = place(1, "monomer", 4.0), place(2, "dimer", 0.0)
    reaction = transition(
        10, "dimerize", rate_law=RateLawType.MASS_ACTION, parameters={"rate_constant": 0.25}
    )
    net = model(
        [a, b],
        [reaction],
        [
            arc(20, a.id, reaction.id, PetriArcType.INPUT, weight=2),
            arc(21, b.id, reaction.id, PetriArcType.OUTPUT),
        ],
    )
    engine = PetriEngine(net)
    run = engine.simulate_continuous(SimulationParameters(model_id=net.id, duration=3, steps=31))
    values_a = np.asarray(run.trajectories[str(a.id)])
    values_b = np.asarray(run.trajectories[str(b.id)])
    expected_a = 4 / (1 + 2 * 0.25 * 4 * np.asarray(run.times))
    np.testing.assert_allclose(values_a, expected_a, rtol=1e-7)
    np.testing.assert_allclose(values_a + 2 * values_b, 4, atol=1e-12)
    reachability = engine.explore_reachability()
    assert not reachability.truncated
    assert len(reachability.markings) == 3
    assert len(reachability.deadlocks) == 1
    for state in reachability.markings:
        marking = dict(state)
        assert marking[a.id] + 2 * marking[b.id] == 4


def test_production_and_consumption_recover_open_system_equilibrium() -> None:
    state = place(1, "pool", 0.0)
    source = transition(10, "source", parameters={"rate": 0.6})
    loss = transition(
        11, "loss", rate_law=RateLawType.MASS_ACTION, parameters={"rate_constant": 0.2}
    )
    net = model(
        [state],
        [source, loss],
        [
            arc(20, state.id, source.id, PetriArcType.OUTPUT),
            arc(21, state.id, loss.id, PetriArcType.INPUT),
        ],
    )
    run = PetriEngine(net).simulate_continuous(
        SimulationParameters(model_id=net.id, duration=40, steps=101)
    )
    expected = 3 * (1 - np.exp(-0.2 * np.asarray(run.times)))
    np.testing.assert_allclose(run.trajectories[str(state.id)], expected, atol=2e-8)
    assert run.trajectories[str(state.id)][-1] == pytest.approx(3, abs=0.002)


def test_continuous_read_and_inhibitory_gates_switch_when_modifier_decays() -> None:
    marker = place(1, "marker", 2.0)
    read_output, inhibited_output = place(2, "read output", 0.0), place(3, "inhibited output", 0.0)
    decay = transition(
        10, "decay", rate_law=RateLawType.MASS_ACTION, parameters={"rate_constant": 1.0}
    )
    read_source, inhibited_source = (
        transition(11, "read source"),
        transition(12, "inhibited source"),
    )
    net = model(
        [marker, read_output, inhibited_output],
        [decay, read_source, inhibited_source],
        [
            arc(20, marker.id, decay.id, PetriArcType.INPUT),
            arc(21, marker.id, read_source.id, PetriArcType.READ, threshold=1),
            arc(22, read_output.id, read_source.id, PetriArcType.OUTPUT),
            arc(23, marker.id, inhibited_source.id, PetriArcType.INHIBITORY, threshold=1),
            arc(24, inhibited_output.id, inhibited_source.id, PetriArcType.OUTPUT),
        ],
    )
    engine = PetriEngine(net)
    config = SimulationParameters(model_id=net.id, duration=2, steps=41)
    run = engine.simulate_continuous(config)
    times = np.asarray(run.times)
    np.testing.assert_allclose(run.trajectories[str(marker.id)], 2 * np.exp(-times), atol=1e-8)
    np.testing.assert_allclose(
        run.trajectories[str(read_output.id)], np.minimum(times, np.log(2)), atol=2e-7
    )
    np.testing.assert_allclose(
        run.trajectories[str(inhibited_output.id)], np.maximum(times - np.log(2), 0), atol=2e-7
    )
    uninhibited = engine.simulate_continuous(
        config.model_copy(update={"initial_overrides": {str(marker.id): 0.0}})
    )
    np.testing.assert_allclose(uninhibited.trajectories[str(inhibited_output.id)], times, atol=1e-8)
    np.testing.assert_allclose(uninhibited.trajectories[str(read_output.id)], 0)


def test_hard_bounds_stop_constant_production_and_consumption() -> None:
    accumulated, substrate = place(1, "accumulated", 0.0, valid_max=1), place(2, "substrate", 1.0)
    source, sink = transition(10, "source"), transition(11, "sink")
    net = model(
        [accumulated, substrate],
        [source, sink],
        [
            arc(20, accumulated.id, source.id, PetriArcType.OUTPUT),
            arc(21, substrate.id, sink.id, PetriArcType.INPUT),
        ],
    )
    run = PetriEngine(net).simulate_continuous(
        SimulationParameters(model_id=net.id, duration=2, steps=41)
    )
    times = np.asarray(run.times)
    np.testing.assert_allclose(
        run.trajectories[str(accumulated.id)], np.minimum(times, 1), atol=2e-7
    )
    np.testing.assert_allclose(
        run.trajectories[str(substrate.id)], np.maximum(1 - times, 0), atol=2e-7
    )
    assert run.transition_activity[str(source.id)][-1] == 0
    assert run.transition_activity[str(sink.id)][-1] == 0


def test_constant_self_loop_requires_available_substrate_even_with_zero_net_consumption() -> None:
    catalyst, product = place(1, "catalyst", 0), place(2, "product", 0)
    reaction = transition(10, "catalytic production")
    net = model(
        [catalyst, product],
        [reaction],
        [
            arc(20, catalyst.id, reaction.id, PetriArcType.INPUT),
            arc(21, catalyst.id, reaction.id, PetriArcType.OUTPUT),
            arc(22, product.id, reaction.id, PetriArcType.OUTPUT),
        ],
    )
    engine = PetriEngine(net)
    config = SimulationParameters(model_id=net.id, duration=1, steps=11)
    blocked = engine.simulate_continuous(config)
    assert blocked.trajectories[str(product.id)] == (0,) * 11
    active = engine.simulate_continuous(
        config.model_copy(update={"initial_overrides": {str(catalyst.id): 1.0}})
    )
    np.testing.assert_allclose(active.trajectories[str(product.id)], active.times, atol=1e-8)
    assert active.trajectories[str(catalyst.id)] == (1,) * 11


def test_solver_evaluation_budget_fails_instead_of_returning_a_partial_trajectory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = place(1, "state", 0)
    source = transition(10, "source")
    net = model([state], [source], [arc(20, state.id, source.id, PetriArcType.OUTPUT)])
    monkeypatch.setattr(engine_module, "_MAX_DERIVATIVE_EVALUATIONS", 5)
    with pytest.raises(PetriSimulationError, match="evaluation budget"):
        PetriEngine(net).simulate_continuous(
            SimulationParameters(model_id=net.id, duration=1, steps=11)
        )


def test_run_identity_tracks_model_content_even_when_a_version_was_not_bumped() -> None:
    state = place(1, "state", 0)
    source = transition(10, "source", parameters={"rate": 1})
    net = model([state], [source], [arc(20, state.id, source.id, PetriArcType.OUTPUT)])
    changed_net = net.model_copy(
        update={"transitions": (source.model_copy(update={"parameters": {"rate": 2}}),)}
    )
    config = SimulationParameters(model_id=net.id, duration=1, steps=11)
    original = PetriEngine(net).simulate_continuous(config)
    changed = PetriEngine(changed_net).simulate_continuous(config)
    assert original.model_id == changed.model_id
    assert original.model_version == changed.model_version
    assert original.id != changed.id
    assert changed.trajectories[str(state.id)][-1] == pytest.approx(2)
