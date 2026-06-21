import random

import pytest

from vrptw_hybrid.solvers.alns.acceptance import (
    AlwaysBetterAcceptance,
    MaxIterationsStop,
    NoImprovementStop,
    SimulatedAnnealingAcceptance,
    TimeLimitStop,
)


def test_always_better_accepts_only_non_worse_candidates() -> None:
    acceptance = AlwaysBetterAcceptance()

    assert acceptance.accept(100.0, 90.0, random.Random(1))
    assert acceptance.accept(100.0, 100.0, random.Random(1))
    assert not acceptance.accept(100.0, 110.0, random.Random(1))


def test_simulated_annealing_accepts_better_and_cools() -> None:
    acceptance = SimulatedAnnealingAcceptance(
        initial_temperature=10.0,
        cooling_rate=0.5,
        minimum_temperature=1.0,
    )

    assert acceptance.accept(100.0, 90.0, random.Random(1))
    assert acceptance.temperature == pytest.approx(5.0)


def test_simulated_annealing_can_accept_worse_by_probability() -> None:
    acceptance = SimulatedAnnealingAcceptance(
        initial_temperature=100.0,
        cooling_rate=1.0,
        minimum_temperature=1.0,
    )

    assert acceptance.accept(100.0, 101.0, random.Random(1))


def test_simulated_annealing_temperature_has_floor() -> None:
    acceptance = SimulatedAnnealingAcceptance(
        initial_temperature=2.0,
        cooling_rate=0.1,
        minimum_temperature=1.0,
    )

    acceptance.cool()
    acceptance.cool()

    assert acceptance.temperature == pytest.approx(1.0)


def test_stopping_criteria_boundaries() -> None:
    assert MaxIterationsStop(10).should_stop(
        iteration=10,
        elapsed_sec=0.0,
        no_improvement_iterations=0,
    )
    assert TimeLimitStop(5.0).should_stop(
        iteration=0,
        elapsed_sec=5.0,
        no_improvement_iterations=0,
    )
    assert NoImprovementStop(3).should_stop(
        iteration=0,
        elapsed_sec=0.0,
        no_improvement_iterations=3,
    )


def test_invalid_acceptance_and_stopping_parameters_are_rejected() -> None:
    with pytest.raises(ValueError, match="initial_temperature must be positive"):
        SimulatedAnnealingAcceptance(initial_temperature=0.0, cooling_rate=0.9)
    with pytest.raises(ValueError, match="cooling_rate must be"):
        SimulatedAnnealingAcceptance(initial_temperature=1.0, cooling_rate=0.0)
    with pytest.raises(ValueError, match="max_iterations must be positive"):
        MaxIterationsStop(0)
