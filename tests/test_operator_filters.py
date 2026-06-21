import pytest

from vrptw_hybrid.solvers.alns.destroy import DESTROY_OPERATORS
from vrptw_hybrid.solvers.alns.operator_filters import (
    filter_destroy_operators,
    filter_repair_operators,
)
from vrptw_hybrid.solvers.alns.repair import REPAIR_OPERATORS


def test_filter_destroy_operators_removes_disabled_name() -> None:
    filtered = filter_destroy_operators(disabled_names=("shaw_related_removal",))

    assert "shaw_related_removal" not in {operator.name for operator in filtered}
    assert len(filtered) == len(DESTROY_OPERATORS) - 1


def test_filter_repair_operators_can_enable_specific_subset() -> None:
    filtered = filter_repair_operators(
        enabled_names=("greedy_cheapest_insertion", "noise_insertion"),
    )

    assert tuple(operator.name for operator in filtered) == (
        "greedy_cheapest_insertion",
        "noise_insertion",
    )


def test_filter_operators_reject_unknown_or_empty_pool() -> None:
    with pytest.raises(ValueError, match="Unknown destroy operator"):
        filter_destroy_operators(disabled_names=("does_not_exist",))

    with pytest.raises(ValueError, match="removed every operator"):
        filter_repair_operators(
            disabled_names=tuple(operator.name for operator in REPAIR_OPERATORS),
        )
