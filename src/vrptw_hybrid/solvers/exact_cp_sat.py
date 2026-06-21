"""Small-scale CP-SAT arc-flow solver for VRPTW validation."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter
from typing import Any

from ortools.sat.python import cp_model

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.core.models import Route, RouteStop, Solution, VRPTWInstance
from vrptw_hybrid.core.objective import composite_objective
from vrptw_hybrid.data.distance_matrix import scale_to_int
from vrptw_hybrid.solvers.base import BaseSolver


class CPSATRuntimeError(RuntimeError):
    """Raised when the installed OR-Tools CP-SAT runtime is not usable."""


@dataclass(frozen=True, slots=True)
class _ModelData:
    model: cp_model.CpModel
    x: dict[tuple[int, int, int], cp_model.IntVar]
    used: dict[int, cp_model.IntVar]
    start: dict[tuple[int, int], cp_model.IntVar]
    distance_matrix: list[list[int]]
    time_matrix: list[list[int]]


class CPSATVRPTWSolver(BaseSolver):
    """Exact CP-SAT model intended for small VRPTW instances."""

    def __init__(
        self,
        *,
        time_limit_sec: float = 30.0,
        scale_factor: int = 100,
        vehicle_weight: float = 100000.0,
        num_workers: int = 1,
    ) -> None:
        if time_limit_sec <= 0:
            raise ValueError("time_limit_sec must be positive")
        if scale_factor <= 0:
            raise ValueError("scale_factor must be positive")
        if vehicle_weight < 0:
            raise ValueError("vehicle_weight must be non-negative")
        if num_workers <= 0:
            raise ValueError("num_workers must be positive")

        self.time_limit_sec = time_limit_sec
        self.scale_factor = scale_factor
        self.vehicle_weight = vehicle_weight
        self.num_workers = num_workers

    def solve(
        self,
        instance: VRPTWInstance,
        config: Mapping[str, Any] | None = None,
        seed: int | None = None,
    ) -> Solution:
        """Build and solve a CP-SAT arc-flow model for a small instance."""

        if not is_cp_sat_runtime_available():
            raise CPSATRuntimeError(
                "OR-Tools CP-SAT is installed but failed a subprocess smoke test. "
                "Use a supported Python/OR-Tools combination before running exact_cp_sat."
            )

        start_time = perf_counter()
        model_data = self._build_model(instance)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_sec
        solver.parameters.num_search_workers = self.num_workers

        status = solver.solve(model_data.model)
        runtime_sec = perf_counter() - start_time
        status_name = solver.status_name(status)
        metadata = {
            "status": status_name,
            "best_bound": solver.best_objective_bound,
            "cp_sat_objective": solver.objective_value
            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
            else None,
            "scale_factor": self.scale_factor,
            "time_limit_sec": self.time_limit_sec,
        }

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return Solution(
                instance_name=instance.name,
                solver_name="cp_sat",
                routes=(),
                objective=float("inf"),
                vehicles_used=0,
                total_distance=0.0,
                total_duration=0.0,
                feasible=False,
                runtime_sec=runtime_sec,
                metadata=metadata,
            )

        routes = self._extract_routes(instance, model_data, solver)
        vehicles_used = len(routes)
        total_distance = sum(route.distance for route in routes)
        total_duration = sum(route.duration for route in routes)
        solution = Solution(
            instance_name=instance.name,
            solver_name="cp_sat",
            routes=routes,
            objective=composite_objective(vehicles_used, total_distance, self.vehicle_weight),
            vehicles_used=vehicles_used,
            total_distance=total_distance,
            total_duration=total_duration,
            feasible=False,
            runtime_sec=runtime_sec,
            metadata=metadata,
        )
        report = check_solution(solution, instance)
        return Solution(
            instance_name=solution.instance_name,
            solver_name=solution.solver_name,
            routes=solution.routes,
            objective=solution.objective,
            vehicles_used=solution.vehicles_used,
            total_distance=solution.total_distance,
            total_duration=solution.total_duration,
            feasible=report.feasible,
            runtime_sec=solution.runtime_sec,
            metadata={
                **solution.metadata,
                "feasibility_violations": list(report.violations),
            },
        )

    def _build_model(self, instance: VRPTWInstance) -> _ModelData:
        node_count = instance.node_count
        vehicles = range(instance.vehicle.count)
        customers = range(1, node_count)
        nodes = range(node_count)
        distance_matrix = scale_to_int(instance.distance_matrix, self.scale_factor).tolist()
        time_matrix = scale_to_int(instance.time_matrix, self.scale_factor).tolist()
        model = cp_model.CpModel()

        x: dict[tuple[int, int, int], cp_model.IntVar] = {}
        for vehicle_id in vehicles:
            for from_index in nodes:
                for to_index in nodes:
                    if from_index == to_index:
                        continue
                    x[from_index, to_index, vehicle_id] = model.new_bool_var(
                        f"x_{from_index}_{to_index}_{vehicle_id}"
                    )

        used = {vehicle_id: model.new_bool_var(f"used_{vehicle_id}") for vehicle_id in vehicles}
        horizon = self._time_horizon(instance, time_matrix)
        start = {
            (customer_index, vehicle_id): model.new_int_var(
                0,
                horizon,
                f"start_{customer_index}_{vehicle_id}",
            )
            for customer_index in customers
            for vehicle_id in vehicles
        }

        self._add_visit_constraints(model, x, used, instance)
        self._add_capacity_constraints(model, x, instance)
        self._add_time_constraints(model, x, start, instance, time_matrix)

        vehicle_weight_int = round(self.vehicle_weight * self.scale_factor)
        model.minimize(
            vehicle_weight_int * sum(used.values())
            + sum(
                distance_matrix[from_index][to_index] * variable
                for (from_index, to_index, _vehicle_id), variable in x.items()
            )
        )
        return _ModelData(
            model=model,
            x=x,
            used=used,
            start=start,
            distance_matrix=distance_matrix,
            time_matrix=time_matrix,
        )

    def _add_visit_constraints(
        self,
        model: cp_model.CpModel,
        x: dict[tuple[int, int, int], cp_model.IntVar],
        used: dict[int, cp_model.IntVar],
        instance: VRPTWInstance,
    ) -> None:
        node_count = instance.node_count
        vehicles = range(instance.vehicle.count)
        customers = range(1, node_count)
        nodes = range(node_count)

        for customer_index in customers:
            model.add(
                sum(
                    x[from_index, customer_index, vehicle_id]
                    for vehicle_id in vehicles
                    for from_index in nodes
                    if from_index != customer_index
                )
                == 1
            )

        for vehicle_id in vehicles:
            model.add(
                sum(x[0, to_index, vehicle_id] for to_index in customers) == used[vehicle_id]
            )
            model.add(
                sum(x[from_index, 0, vehicle_id] for from_index in customers)
                == used[vehicle_id]
            )
            for customer_index in customers:
                incoming = sum(
                    x[from_index, customer_index, vehicle_id]
                    for from_index in nodes
                    if from_index != customer_index
                )
                outgoing = sum(
                    x[customer_index, to_index, vehicle_id]
                    for to_index in nodes
                    if to_index != customer_index
                )
                model.add(incoming == outgoing)

    def _add_capacity_constraints(
        self,
        model: cp_model.CpModel,
        x: dict[tuple[int, int, int], cp_model.IntVar],
        instance: VRPTWInstance,
    ) -> None:
        node_count = instance.node_count
        vehicles = range(instance.vehicle.count)
        customers = range(1, node_count)
        nodes = range(node_count)

        for vehicle_id in vehicles:
            model.add(
                sum(
                    instance.nodes[customer_index].demand
                    * sum(
                        x[from_index, customer_index, vehicle_id]
                        for from_index in nodes
                        if from_index != customer_index
                    )
                    for customer_index in customers
                )
                <= instance.vehicle.capacity
            )

    def _add_time_constraints(
        self,
        model: cp_model.CpModel,
        x: dict[tuple[int, int, int], cp_model.IntVar],
        start: dict[tuple[int, int], cp_model.IntVar],
        instance: VRPTWInstance,
        time_matrix: list[list[int]],
    ) -> None:
        node_count = instance.node_count
        vehicles = range(instance.vehicle.count)
        customers = range(1, node_count)
        nodes = range(node_count)
        depot_ready = _scaled(
            instance.depot.ready_time + instance.depot.service_time,
            self.scale_factor,
        )
        depot_due = _scaled(instance.depot.due_time, self.scale_factor)

        for vehicle_id in vehicles:
            for customer_index in customers:
                served = model.new_bool_var(f"served_{customer_index}_{vehicle_id}")
                model.add(
                    sum(
                        x[from_index, customer_index, vehicle_id]
                        for from_index in nodes
                        if from_index != customer_index
                    )
                    == served
                )
                customer = instance.nodes[customer_index]
                ready_time = _scaled(customer.ready_time, self.scale_factor)
                due_time = _scaled(customer.due_time, self.scale_factor)
                model.add(start[customer_index, vehicle_id] >= ready_time).only_enforce_if(served)
                model.add(start[customer_index, vehicle_id] <= due_time).only_enforce_if(served)

            for to_index in customers:
                model.add(
                    start[to_index, vehicle_id] >= depot_ready + time_matrix[0][to_index]
                ).only_enforce_if(x[0, to_index, vehicle_id])

            for from_index in customers:
                from_customer = instance.nodes[from_index]
                service_time = _scaled(from_customer.service_time, self.scale_factor)
                model.add(
                    start[from_index, vehicle_id] + service_time + time_matrix[from_index][0]
                    <= depot_due
                ).only_enforce_if(x[from_index, 0, vehicle_id])

            for from_index in customers:
                from_customer = instance.nodes[from_index]
                service_time = _scaled(from_customer.service_time, self.scale_factor)
                for to_index in customers:
                    if from_index == to_index:
                        continue
                    model.add(
                        start[to_index, vehicle_id]
                        >= start[from_index, vehicle_id]
                        + service_time
                        + time_matrix[from_index][to_index]
                    ).only_enforce_if(x[from_index, to_index, vehicle_id])

    def _extract_routes(
        self,
        instance: VRPTWInstance,
        model_data: _ModelData,
        solver: cp_model.CpSolver,
    ) -> tuple[Route, ...]:
        routes: list[Route] = []
        for vehicle_id in range(instance.vehicle.count):
            if solver.boolean_value(model_data.used[vehicle_id]) is False:
                continue
            customer_indices = self._extract_customer_indices(
                vehicle_id,
                instance,
                model_data,
                solver,
            )
            route = _build_route(instance, vehicle_id, customer_indices)
            if route.stops:
                routes.append(route)
        return tuple(routes)

    def _extract_customer_indices(
        self,
        vehicle_id: int,
        instance: VRPTWInstance,
        model_data: _ModelData,
        solver: cp_model.CpSolver,
    ) -> tuple[int, ...]:
        sequence: list[int] = []
        current_index = 0
        visited_guard = 0
        while visited_guard <= instance.node_count:
            next_indices = [
                to_index
                for to_index in range(instance.node_count)
                if to_index != current_index
                and solver.boolean_value(model_data.x[current_index, to_index, vehicle_id])
            ]
            if not next_indices:
                break
            next_index = next_indices[0]
            if next_index == 0:
                break
            sequence.append(next_index)
            current_index = next_index
            visited_guard += 1
        return tuple(sequence)

    def _time_horizon(self, instance: VRPTWInstance, time_matrix: list[list[int]]) -> int:
        max_due = max(_scaled(node.due_time, self.scale_factor) for node in instance.nodes)
        max_service = max(_scaled(node.service_time, self.scale_factor) for node in instance.nodes)
        max_travel = max(max(row) for row in time_matrix)
        return max_due + max_service + max_travel


def solve_cp_sat(
    instance: VRPTWInstance,
    *,
    time_limit_sec: float = 30.0,
    scale_factor: int = 100,
    vehicle_weight: float = 100000.0,
    num_workers: int = 1,
) -> Solution:
    """Convenience wrapper around :class:`CPSATVRPTWSolver`."""

    return CPSATVRPTWSolver(
        time_limit_sec=time_limit_sec,
        scale_factor=scale_factor,
        vehicle_weight=vehicle_weight,
        num_workers=num_workers,
    ).solve(instance)


@lru_cache(maxsize=1)
def is_cp_sat_runtime_available() -> bool:
    """Return whether CP-SAT can solve a trivial model without crashing."""

    code = (
        "from ortools.sat.python import cp_model\n"
        "m = cp_model.CpModel()\n"
        "x = m.new_bool_var('x')\n"
        "m.maximize(x)\n"
        "s = cp_model.CpSolver()\n"
        "status = s.solve(m)\n"
        "raise SystemExit(0 if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 1)\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _build_route(
    instance: VRPTWInstance,
    vehicle_id: int,
    customer_indices: tuple[int, ...],
) -> Route:
    stops: list[RouteStop] = []
    load = 0
    previous_index = 0
    previous_departure = instance.depot.ready_time
    distance = 0.0

    for customer_index in customer_indices:
        customer = instance.nodes[customer_index]
        travel_time = float(instance.time_matrix[previous_index, customer_index])
        arrival_time = previous_departure + travel_time
        start_service_time = max(arrival_time, customer.ready_time)
        departure_time = start_service_time + customer.service_time
        load += customer.demand
        distance += float(instance.distance_matrix[previous_index, customer_index])
        stops.append(
            RouteStop(
                customer_id=customer.id,
                arrival_time=arrival_time,
                start_service_time=start_service_time,
                departure_time=departure_time,
                load_after=load,
            )
        )
        previous_index = customer_index
        previous_departure = departure_time

    return_time = previous_departure + float(instance.time_matrix[previous_index, 0])
    distance += float(instance.distance_matrix[previous_index, 0])
    return Route(
        vehicle_id=vehicle_id,
        stops=tuple(stops),
        distance=distance,
        duration=return_time - instance.depot.ready_time,
        load=load,
    )


def _scaled(value: float, scale_factor: int) -> int:
    return round(value * scale_factor)
