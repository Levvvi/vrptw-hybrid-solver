import random

import pytest

from vrptw_hybrid.solvers.alns.destroy import DESTROY_OPERATORS
from vrptw_hybrid.solvers.alns.repair import REPAIR_OPERATORS
from vrptw_hybrid.solvers.alns.selectors import (
    MOSADEInspiredSelector,
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


def test_mosade_pair_reward_increases_pair_probability() -> None:
    selector = MOSADEInspiredSelector(
        destroy_operators=DESTROY_OPERATORS[:2],
        repair_operators=REPAIR_OPERATORS[:2],
        temperature=0.5,
        decay=0.0,
        memory_size=5,
        exploration_floor=0.05,
    )
    pair_key = f"{DESTROY_OPERATORS[0].name}|{REPAIR_OPERATORS[0].name}"
    before = selector.snapshot()["pair_probabilities"][pair_key]
    event = OperatorEvent(
        destroy_name=DESTROY_OPERATORS[0].name,
        repair_name=REPAIR_OPERATORS[0].name,
        accepted=True,
        new_best=True,
        delta_cost=-10.0,
        feasible=True,
    )

    for _ in range(3):
        selector.update(event)
    snapshot = selector.snapshot()

    assert snapshot["pair_probabilities"][pair_key] > before
    assert snapshot["pair_stats"][pair_key]["selected"] == 3
    assert sum(snapshot["pair_probabilities"].values()) == pytest.approx(1.0)


def test_mosade_exploration_floor_keeps_all_pairs_available() -> None:
    selector = MOSADEInspiredSelector(
        destroy_operators=DESTROY_OPERATORS[:2],
        repair_operators=REPAIR_OPERATORS[:2],
        temperature=0.1,
        decay=0.0,
        memory_size=5,
        exploration_floor=0.2,
    )
    event = OperatorEvent(
        destroy_name=DESTROY_OPERATORS[0].name,
        repair_name=REPAIR_OPERATORS[0].name,
        accepted=True,
        new_best=True,
        delta_cost=-100.0,
        feasible=True,
    )

    for _ in range(5):
        selector.update(event)
    probabilities = selector.snapshot()["pair_probabilities"]
    floor = 0.2 / len(probabilities)

    assert all(probability >= floor - 1e-12 for probability in probabilities.values())
    assert sum(probabilities.values()) == pytest.approx(1.0)


def test_mosade_seed_reproducibility_for_adaptive_pair_sequence() -> None:
    first = MOSADEInspiredSelector(
        destroy_operators=DESTROY_OPERATORS[:2],
        repair_operators=REPAIR_OPERATORS[:2],
    )
    second = MOSADEInspiredSelector(
        destroy_operators=DESTROY_OPERATORS[:2],
        repair_operators=REPAIR_OPERATORS[:2],
    )
    first_rng = random.Random(123)
    second_rng = random.Random(123)

    for index in range(5):
        first_destroy = first.select_destroy(first_rng)
        first_repair = first.select_repair(first_rng)
        second_destroy = second.select_destroy(second_rng)
        second_repair = second.select_repair(second_rng)

        assert (first_destroy.name, first_repair.name) == (
            second_destroy.name,
            second_repair.name,
        )

        event = OperatorEvent(
            destroy_name=first_destroy.name,
            repair_name=first_repair.name,
            accepted=True,
            new_best=index == 0,
            delta_cost=-2.0,
            feasible=True,
        )
        first.update(event)
        second.update(event)


def test_mosade_can_disable_pair_memory_and_diversity_bonus() -> None:
    selector = MOSADEInspiredSelector(
        destroy_operators=DESTROY_OPERATORS[:1],
        repair_operators=REPAIR_OPERATORS[:1],
        decay=0.0,
        use_pair_memory=False,
        use_diversity_bonus=False,
    )
    event = OperatorEvent(
        destroy_name=DESTROY_OPERATORS[0].name,
        repair_name=REPAIR_OPERATORS[0].name,
        accepted=False,
        new_best=False,
        delta_cost=float("inf"),
        feasible=False,
    )

    selector.update(event)
    snapshot = selector.snapshot()

    assert snapshot["use_pair_memory"] is False
    assert snapshot["use_diversity_bonus"] is False
    assert snapshot["pair_credit"][f"{DESTROY_OPERATORS[0].name}|{REPAIR_OPERATORS[0].name}"] == 0.0
