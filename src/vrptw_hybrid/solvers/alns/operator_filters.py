"""Operator pool filtering for ALNS ablation experiments."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

from vrptw_hybrid.solvers.alns.destroy import DESTROY_OPERATORS, DestroyOperator
from vrptw_hybrid.solvers.alns.repair import REPAIR_OPERATORS, RepairOperator

OperatorT = TypeVar("OperatorT", DestroyOperator, RepairOperator)


def filter_destroy_operators(
    *,
    enabled_names: Iterable[str] | None = None,
    disabled_names: Iterable[str] | None = None,
    operators: tuple[DestroyOperator, ...] = DESTROY_OPERATORS,
) -> tuple[DestroyOperator, ...]:
    """Return a validated destroy operator subset."""

    return _filter_operators(
        operators,
        enabled_names=enabled_names,
        disabled_names=disabled_names,
        kind="destroy",
    )


def filter_repair_operators(
    *,
    enabled_names: Iterable[str] | None = None,
    disabled_names: Iterable[str] | None = None,
    operators: tuple[RepairOperator, ...] = REPAIR_OPERATORS,
) -> tuple[RepairOperator, ...]:
    """Return a validated repair operator subset."""

    return _filter_operators(
        operators,
        enabled_names=enabled_names,
        disabled_names=disabled_names,
        kind="repair",
    )


def _filter_operators(
    operators: tuple[OperatorT, ...],
    *,
    enabled_names: Iterable[str] | None,
    disabled_names: Iterable[str] | None,
    kind: str,
) -> tuple[OperatorT, ...]:
    available_names = {operator.name for operator in operators}
    enabled = set(enabled_names or ())
    disabled = set(disabled_names or ())

    unknown = (enabled | disabled) - available_names
    if unknown:
        raise ValueError(f"Unknown {kind} operator(s): {', '.join(sorted(unknown))}")

    overlap = enabled & disabled
    if overlap:
        raise ValueError(
            f"{kind} operator(s) cannot be both enabled and disabled: "
            f"{', '.join(sorted(overlap))}"
        )

    filtered = tuple(
        operator
        for operator in operators
        if (not enabled or operator.name in enabled) and operator.name not in disabled
    )
    if not filtered:
        raise ValueError(f"{kind} operator filter removed every operator")
    return filtered
