"""Operator selection interfaces for ALNS."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Protocol

from vrptw_hybrid.solvers.alns.destroy import DESTROY_OPERATORS, DestroyOperator
from vrptw_hybrid.solvers.alns.repair import REPAIR_OPERATORS, RepairOperator


@dataclass(frozen=True, slots=True)
class OperatorEvent:
    destroy_name: str
    repair_name: str
    accepted: bool
    new_best: bool
    delta_cost: float
    feasible: bool


class OperatorSelector(Protocol):
    """Interface for selecting and updating ALNS operators."""

    def select_destroy(self, rng: random.Random) -> DestroyOperator:
        """Select one destroy operator."""

    def select_repair(self, rng: random.Random) -> RepairOperator:
        """Select one repair operator."""

    def update(self, event: OperatorEvent) -> None:
        """Update selector state after an iteration."""

    def snapshot(self) -> dict[str, Any]:
        """Return JSON-serializable selector state."""


class UniformSelector:
    """Uniform random operator selector with event accounting."""

    def __init__(
        self,
        destroy_operators: tuple[DestroyOperator, ...] = DESTROY_OPERATORS,
        repair_operators: tuple[RepairOperator, ...] = REPAIR_OPERATORS,
    ) -> None:
        if not destroy_operators:
            raise ValueError("at least one destroy operator is required")
        if not repair_operators:
            raise ValueError("at least one repair operator is required")
        self.destroy_operators = destroy_operators
        self.repair_operators = repair_operators
        self.events_seen = 0

    def select_destroy(self, rng: random.Random) -> DestroyOperator:
        return rng.choice(self.destroy_operators)

    def select_repair(self, rng: random.Random) -> RepairOperator:
        return rng.choice(self.repair_operators)

    def update(self, event: OperatorEvent) -> None:
        self.events_seen += 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": "uniform",
            "events_seen": self.events_seen,
            "destroy_operators": [operator.name for operator in self.destroy_operators],
            "repair_operators": [operator.name for operator in self.repair_operators],
            "destroy_probabilities": {
                operator.name: 1.0 / len(self.destroy_operators)
                for operator in self.destroy_operators
            },
            "repair_probabilities": {
                operator.name: 1.0 / len(self.repair_operators)
                for operator in self.repair_operators
            },
        }
