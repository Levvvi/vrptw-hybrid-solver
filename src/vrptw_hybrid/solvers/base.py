"""Common solver interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from vrptw_hybrid.core.models import Solution, VRPTWInstance


class BaseSolver(ABC):
    """Abstract interface shared by all solver implementations."""

    @abstractmethod
    def solve(
        self,
        instance: VRPTWInstance,
        config: Mapping[str, Any] | None = None,
        seed: int | None = None,
    ) -> Solution:
        """Solve an instance and return a unified Solution object."""
