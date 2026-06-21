import random

import pytest

from vrptw_hybrid.solvers.alns.destroy import DESTROY_OPERATORS
from vrptw_hybrid.solvers.alns.repair import REPAIR_OPERATORS
from vrptw_hybrid.solvers.alns.selectors import (
    OperatorEvent,
    RouletteWheelSelector,
    UniformSelector,
)


def make_event() -> OperatorEvent:
    return OperatorEvent(
        destroy_name="random_removal",
        repair_name="greedy_cheapest_insertion",
        accepted=True,
        new_best=False,
        delta_cost=-1.0,
        feasible=True,
    )


def test_uniform_selector_selects_registered_operators() -> None:
    selector = UniformSelector()
    rng = random.Random(42)

    destroy = selector.select_destroy(rng)
    repair = selector.select_repair(rng)

    assert destroy in DESTROY_OPERATORS
    assert repair in REPAIR_OPERATORS


def test_uniform_selector_update_and_snapshot() -> None:
    selector = UniformSelector()

    selector.update(make_event())
    snapshot = selector.snapshot()

    assert snapshot["name"] == "uniform"
    assert snapshot["events_seen"] == 1
    assert set(snapshot["destroy_operators"]) == {operator.name for operator in DESTROY_OPERATORS}
    assert set(snapshot["repair_operators"]) == {operator.name for operator in REPAIR_OPERATORS}
    assert sum(snapshot["destroy_probabilities"].values()) == pytest.approx(1.0)
    assert sum(snapshot["repair_probabilities"].values()) == pytest.approx(1.0)


def test_uniform_selector_rejects_empty_operator_pools() -> None:
    with pytest.raises(ValueError, match="at least one destroy operator"):
        UniformSelector(destroy_operators=())
    with pytest.raises(ValueError, match="at least one repair operator"):
        UniformSelector(repair_operators=())


def test_roulette_reward_event_updates_operator_weights() -> None:
    selector = RouletteWheelSelector(
        segment_length=1,
        reaction_factor=1.0,
        exploration_floor=0.01,
    )
    event = OperatorEvent(
        destroy_name=DESTROY_OPERATORS[0].name,
        repair_name=REPAIR_OPERATORS[0].name,
        accepted=True,
        new_best=True,
        delta_cost=-10.0,
        feasible=True,
    )

    selector.update(event)
    snapshot = selector.snapshot()

    assert snapshot["destroy_weights"][DESTROY_OPERATORS[0].name] == pytest.approx(5.0)
    assert snapshot["repair_weights"][REPAIR_OPERATORS[0].name] == pytest.approx(5.0)
    assert sum(snapshot["destroy_probabilities"].values()) == pytest.approx(1.0)
    assert sum(snapshot["repair_probabilities"].values()) == pytest.approx(1.0)
    assert all(probability >= 0.01 for probability in snapshot["destroy_probabilities"].values())


def test_roulette_selector_selects_valid_operator() -> None:
    selector = RouletteWheelSelector(segment_length=2, reaction_factor=0.5)
    rng = random.Random(5)

    assert selector.select_destroy(rng) in DESTROY_OPERATORS
    assert selector.select_repair(rng) in REPAIR_OPERATORS
