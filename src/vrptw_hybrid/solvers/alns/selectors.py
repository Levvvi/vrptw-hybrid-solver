"""Operator selection interfaces for ALNS."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from vrptw_hybrid.solvers.alns.destroy import DESTROY_OPERATORS, DestroyOperator
from vrptw_hybrid.solvers.alns.repair import REPAIR_OPERATORS, RepairOperator

OperatorT = TypeVar("OperatorT", DestroyOperator, RepairOperator)


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


class RouletteWheelSelector:
    """Segment-based roulette wheel selector with ALNS-style rewards."""

    def __init__(
        self,
        destroy_operators: tuple[DestroyOperator, ...] = DESTROY_OPERATORS,
        repair_operators: tuple[RepairOperator, ...] = REPAIR_OPERATORS,
        *,
        segment_length: int = 100,
        reaction_factor: float = 0.2,
        exploration_floor: float = 0.05,
    ) -> None:
        if not destroy_operators:
            raise ValueError("at least one destroy operator is required")
        if not repair_operators:
            raise ValueError("at least one repair operator is required")
        if segment_length <= 0:
            raise ValueError("segment_length must be positive")
        if not 0 <= reaction_factor <= 1:
            raise ValueError("reaction_factor must be in [0, 1]")
        if exploration_floor < 0:
            raise ValueError("exploration_floor must be non-negative")

        self.destroy_operators = destroy_operators
        self.repair_operators = repair_operators
        self.segment_length = segment_length
        self.reaction_factor = reaction_factor
        self.exploration_floor = exploration_floor
        self.events_seen = 0
        self.destroy_weights = {operator.name: 1.0 for operator in destroy_operators}
        self.repair_weights = {operator.name: 1.0 for operator in repair_operators}
        self._destroy_segment_scores = {operator.name: 0.0 for operator in destroy_operators}
        self._repair_segment_scores = {operator.name: 0.0 for operator in repair_operators}
        self._destroy_segment_counts = {operator.name: 0 for operator in destroy_operators}
        self._repair_segment_counts = {operator.name: 0 for operator in repair_operators}

    def select_destroy(self, rng: random.Random) -> DestroyOperator:
        return _weighted_choice(
            self.destroy_operators,
            self._probabilities(self.destroy_weights),
            rng,
        )

    def select_repair(self, rng: random.Random) -> RepairOperator:
        return _weighted_choice(
            self.repair_operators,
            self._probabilities(self.repair_weights),
            rng,
        )

    def update(self, event: OperatorEvent) -> None:
        reward = _reward(event)
        self.events_seen += 1
        if event.destroy_name in self._destroy_segment_scores:
            self._destroy_segment_scores[event.destroy_name] += reward
            self._destroy_segment_counts[event.destroy_name] += 1
        if event.repair_name in self._repair_segment_scores:
            self._repair_segment_scores[event.repair_name] += reward
            self._repair_segment_counts[event.repair_name] += 1
        if self.events_seen % self.segment_length == 0:
            self._apply_segment_update()

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": "roulette",
            "events_seen": self.events_seen,
            "segment_length": self.segment_length,
            "reaction_factor": self.reaction_factor,
            "exploration_floor": self.exploration_floor,
            "destroy_weights": dict(self.destroy_weights),
            "repair_weights": dict(self.repair_weights),
            "destroy_probabilities": self._probabilities(self.destroy_weights),
            "repair_probabilities": self._probabilities(self.repair_weights),
            "destroy_segment_scores": dict(self._destroy_segment_scores),
            "repair_segment_scores": dict(self._repair_segment_scores),
        }

    def _apply_segment_update(self) -> None:
        _update_weights(
            self.destroy_weights,
            self._destroy_segment_scores,
            self._destroy_segment_counts,
            self.reaction_factor,
        )
        _update_weights(
            self.repair_weights,
            self._repair_segment_scores,
            self._repair_segment_counts,
            self.reaction_factor,
        )
        self._destroy_segment_scores = {operator.name: 0.0 for operator in self.destroy_operators}
        self._repair_segment_scores = {operator.name: 0.0 for operator in self.repair_operators}
        self._destroy_segment_counts = {operator.name: 0 for operator in self.destroy_operators}
        self._repair_segment_counts = {operator.name: 0 for operator in self.repair_operators}

    def _probabilities(self, weights: dict[str, float]) -> dict[str, float]:
        names = list(weights)
        if not names:
            return {}
        if self.exploration_floor * len(names) >= 1.0:
            return {name: 1.0 / len(names) for name in names}
        total_weight = sum(max(weights[name], 0.0) for name in names)
        if total_weight <= 0:
            base = {name: 1.0 / len(names) for name in names}
        else:
            remaining = 1.0 - self.exploration_floor * len(names)
            base = {
                name: self.exploration_floor
                + remaining * max(weights[name], 0.0) / total_weight
                for name in names
            }
        return _normalize(base)


def _reward(event: OperatorEvent) -> float:
    if event.new_best:
        return 5.0
    if event.accepted and event.delta_cost < 0:
        return 3.0
    if event.accepted:
        return 1.0
    if event.feasible:
        return 0.2
    return 0.0


def _update_weights(
    weights: dict[str, float],
    scores: dict[str, float],
    counts: dict[str, int],
    reaction_factor: float,
) -> None:
    for name, old_weight in list(weights.items()):
        if counts.get(name, 0) == 0:
            continue
        average_score = scores[name] / counts[name]
        weights[name] = (1.0 - reaction_factor) * old_weight + reaction_factor * average_score


def _weighted_choice(
    operators: tuple[OperatorT, ...],
    probabilities: dict[str, float],
    rng: random.Random,
) -> OperatorT:
    threshold = rng.random()
    cumulative = 0.0
    for operator in operators:
        cumulative += probabilities[operator.name]
        if threshold <= cumulative:
            return operator
    return operators[-1]


def _normalize(probabilities: dict[str, float]) -> dict[str, float]:
    total = sum(probabilities.values())
    if total <= 0:
        return {name: 1.0 / len(probabilities) for name in probabilities}
    return {name: value / total for name, value in probabilities.items()}
