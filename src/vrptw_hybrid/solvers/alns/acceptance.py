"""Acceptance criteria and stopping conditions for ALNS."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AlwaysBetterAcceptance:
    """Accept only candidates that are no worse than the current solution."""

    def accept(self, current_cost: float, candidate_cost: float, rng: random.Random) -> bool:
        return candidate_cost <= current_cost


@dataclass(slots=True)
class SimulatedAnnealingAcceptance:
    """Simulated annealing acceptance with geometric cooling."""

    initial_temperature: float
    cooling_rate: float
    minimum_temperature: float = 1e-6
    temperature: float | None = None

    def __post_init__(self) -> None:
        if self.initial_temperature <= 0:
            raise ValueError("initial_temperature must be positive")
        if not 0 < self.cooling_rate <= 1:
            raise ValueError("cooling_rate must be in (0, 1]")
        if self.minimum_temperature <= 0:
            raise ValueError("minimum_temperature must be positive")
        if self.temperature is None:
            self.temperature = self.initial_temperature

    def accept(self, current_cost: float, candidate_cost: float, rng: random.Random) -> bool:
        assert self.temperature is not None
        if candidate_cost <= current_cost:
            accepted = True
        else:
            delta = candidate_cost - current_cost
            probability = math.exp(-delta / max(self.temperature, self.minimum_temperature))
            accepted = rng.random() < probability
        self.cool()
        return accepted

    def cool(self) -> None:
        assert self.temperature is not None
        self.temperature = max(self.minimum_temperature, self.temperature * self.cooling_rate)


@dataclass(frozen=True, slots=True)
class MaxIterationsStop:
    max_iterations: int

    def __post_init__(self) -> None:
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")

    def should_stop(
        self,
        *,
        iteration: int,
        elapsed_sec: float,
        no_improvement_iterations: int,
    ) -> bool:
        return iteration >= self.max_iterations


@dataclass(frozen=True, slots=True)
class TimeLimitStop:
    time_limit_sec: float

    def __post_init__(self) -> None:
        if self.time_limit_sec <= 0:
            raise ValueError("time_limit_sec must be positive")

    def should_stop(
        self,
        *,
        iteration: int,
        elapsed_sec: float,
        no_improvement_iterations: int,
    ) -> bool:
        return elapsed_sec >= self.time_limit_sec


@dataclass(frozen=True, slots=True)
class NoImprovementStop:
    max_no_improvement_iterations: int

    def __post_init__(self) -> None:
        if self.max_no_improvement_iterations <= 0:
            raise ValueError("max_no_improvement_iterations must be positive")

    def should_stop(
        self,
        *,
        iteration: int,
        elapsed_sec: float,
        no_improvement_iterations: int,
    ) -> bool:
        return no_improvement_iterations >= self.max_no_improvement_iterations
