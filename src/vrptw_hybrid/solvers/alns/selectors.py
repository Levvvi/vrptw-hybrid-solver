"""Operator selection interfaces for ALNS."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from math import exp, sqrt
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


class MOSADEInspiredSelector:
    """Pair-level adaptive selector inspired by MOSADE strategy selection."""

    def __init__(
        self,
        destroy_operators: tuple[DestroyOperator, ...] = DESTROY_OPERATORS,
        repair_operators: tuple[RepairOperator, ...] = REPAIR_OPERATORS,
        *,
        temperature: float = 1.0,
        decay: float = 0.8,
        memory_size: int = 50,
        exploration_floor: float = 0.05,
    ) -> None:
        if not destroy_operators:
            raise ValueError("at least one destroy operator is required")
        if not repair_operators:
            raise ValueError("at least one repair operator is required")
        if temperature <= 0:
            raise ValueError("temperature must be positive")
        if not 0 <= decay < 1:
            raise ValueError("decay must be in [0, 1)")
        if memory_size <= 0:
            raise ValueError("memory_size must be positive")
        if not 0 <= exploration_floor <= 1:
            raise ValueError("exploration_floor must be in [0, 1]")

        self.destroy_operators = destroy_operators
        self.repair_operators = repair_operators
        self.temperature = temperature
        self.decay = decay
        self.memory_size = memory_size
        self.exploration_floor = exploration_floor
        self.events_seen = 0
        self._pairs = tuple(
            (destroy_operator, repair_operator)
            for destroy_operator in destroy_operators
            for repair_operator in repair_operators
        )
        self._pair_credit = {_pair_key(*pair): 0.0 for pair in self._pairs}
        self._recent_rewards: deque[tuple[str, float]] = deque(maxlen=memory_size)
        self._pair_stats = {
            _pair_key(*pair): {
                "selected": 0,
                "accepted": 0,
                "new_best": 0,
                "reward_sum": 0.0,
                "improvement_sum": 0.0,
            }
            for pair in self._pairs
        }
        self._pending_pair: tuple[DestroyOperator, RepairOperator] | None = None

    def select_destroy(self, rng: random.Random) -> DestroyOperator:
        self._pending_pair = _weighted_pair_choice(self._pairs, self._pair_probabilities(), rng)
        return self._pending_pair[0]

    def select_repair(self, rng: random.Random) -> RepairOperator:
        if self._pending_pair is None:
            self._pending_pair = _weighted_pair_choice(self._pairs, self._pair_probabilities(), rng)
        repair_operator = self._pending_pair[1]
        self._pending_pair = None
        return repair_operator

    def update(self, event: OperatorEvent) -> None:
        pair_key = _pair_key_from_names(event.destroy_name, event.repair_name)
        if pair_key not in self._pair_credit:
            return

        reward = self._reward(event, pair_key)
        self.events_seen += 1
        self._recent_rewards.append((pair_key, reward))
        stats = self._pair_stats[pair_key]
        stats["selected"] += 1
        stats["accepted"] += int(event.accepted)
        stats["new_best"] += int(event.new_best)
        stats["reward_sum"] += reward
        stats["improvement_sum"] += max(0.0, -event.delta_cost) if event.feasible else 0.0
        self._update_credit_from_memory()

    def snapshot(self) -> dict[str, Any]:
        probabilities = self._pair_probabilities()
        return {
            "name": "mosade_inspired",
            "events_seen": self.events_seen,
            "temperature": self.temperature,
            "decay": self.decay,
            "memory_size": self.memory_size,
            "exploration_floor": self.exploration_floor,
            "pair_credit": dict(self._pair_credit),
            "pair_probabilities": probabilities,
            "pair_heatmap": [
                {
                    "destroy": destroy_operator.name,
                    "repair": repair_operator.name,
                    "credit": self._pair_credit[_pair_key(destroy_operator, repair_operator)],
                    "probability": probabilities[_pair_key(destroy_operator, repair_operator)],
                }
                for destroy_operator, repair_operator in self._pairs
            ],
            "pair_stats": {key: dict(value) for key, value in self._pair_stats.items()},
        }

    def _reward(self, event: OperatorEvent, pair_key: str) -> float:
        diversity_bonus = 0.1 / sqrt(1.0 + self._pair_stats[pair_key]["selected"])
        normalized_improvement = 0.0
        if event.feasible and event.delta_cost < 0:
            normalized_improvement = min(1.0, -event.delta_cost / (1.0 + abs(event.delta_cost)))
        return (
            5.0 * int(event.new_best)
            + 3.0 * int(event.accepted and event.delta_cost < 0)
            + 1.0 * int(event.accepted)
            + 0.2 * int(event.feasible)
            + diversity_bonus
            + normalized_improvement
        )

    def _update_credit_from_memory(self) -> None:
        rewards_by_pair: dict[str, list[float]] = {key: [] for key in self._pair_credit}
        for pair_key, reward in self._recent_rewards:
            rewards_by_pair[pair_key].append(reward)
        for pair_key, old_credit in list(self._pair_credit.items()):
            recent_rewards = rewards_by_pair[pair_key]
            recent_reward = sum(recent_rewards) / len(recent_rewards) if recent_rewards else 0.0
            self._pair_credit[pair_key] = (
                self.decay * old_credit + (1.0 - self.decay) * recent_reward
            )

    def _pair_probabilities(self) -> dict[str, float]:
        logits = {
            pair_key: credit / self.temperature for pair_key, credit in self._pair_credit.items()
        }
        softmax_probabilities = _softmax(logits)
        pair_count = len(softmax_probabilities)
        return {
            pair_key: (1.0 - self.exploration_floor) * probability
            + self.exploration_floor / pair_count
            for pair_key, probability in softmax_probabilities.items()
        }


def _softmax(logits: dict[str, float]) -> dict[str, float]:
    if not logits:
        return {}
    max_logit = max(logits.values())
    exp_values = {key: exp(value - max_logit) for key, value in logits.items()}
    return _normalize(exp_values)


def _weighted_pair_choice(
    pairs: tuple[tuple[DestroyOperator, RepairOperator], ...],
    probabilities: dict[str, float],
    rng: random.Random,
) -> tuple[DestroyOperator, RepairOperator]:
    threshold = rng.random()
    cumulative = 0.0
    for pair in pairs:
        cumulative += probabilities[_pair_key(*pair)]
        if threshold <= cumulative:
            return pair
    return pairs[-1]


def _pair_key(destroy_operator: DestroyOperator, repair_operator: RepairOperator) -> str:
    return _pair_key_from_names(destroy_operator.name, repair_operator.name)


def _pair_key_from_names(destroy_name: str, repair_name: str) -> str:
    return f"{destroy_name}|{repair_name}"
