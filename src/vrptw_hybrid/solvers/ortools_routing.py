"""OR-Tools RoutingModel baseline for VRPTW."""

from __future__ import annotations

from collections.abc import Mapping
from time import perf_counter
from typing import Any

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.core.models import Route, RouteStop, Solution, VRPTWInstance
from vrptw_hybrid.core.objective import composite_objective
from vrptw_hybrid.data.distance_matrix import scale_to_int
from vrptw_hybrid.solvers.base import BaseSolver


class ORToolsRoutingSolver(BaseSolver):
    """Industrial OR-Tools routing baseline for VRPTW comparison."""

    def __init__(
        self,
        *,
        time_limit_sec: float = 30.0,
        scale_factor: int = 100,
        vehicle_weight: float = 100000.0,
        first_solution_strategy: str = "PATH_CHEAPEST_ARC",
        local_search_metaheuristic: str = "GUIDED_LOCAL_SEARCH",
    ) -> None:
        if time_limit_sec <= 0:
            raise ValueError("time_limit_sec must be positive")
        if scale_factor <= 0:
            raise ValueError("scale_factor must be positive")
        if vehicle_weight < 0:
            raise ValueError("vehicle_weight must be non-negative")

        self.time_limit_sec = time_limit_sec
        self.scale_factor = scale_factor
        self.vehicle_weight = vehicle_weight
        self.first_solution_strategy = first_solution_strategy
        self.local_search_metaheuristic = local_search_metaheuristic

    def solve(
        self,
        instance: VRPTWInstance,
        config: Mapping[str, Any] | None = None,
        seed: int | None = None,
    ) -> Solution:
        """Solve a VRPTW instance using OR-Tools RoutingModel."""

        start_time = perf_counter()
        manager = pywrapcp.RoutingIndexManager(
            instance.node_count,
            instance.vehicle.count,
            0,
        )
        routing = pywrapcp.RoutingModel(manager)
        distance_matrix = scale_to_int(instance.distance_matrix, self.scale_factor).tolist()
        time_matrix = scale_to_int(instance.time_matrix, self.scale_factor).tolist()
        service_times = [_scaled(node.service_time, self.scale_factor) for node in instance.nodes]

        distance_callback_index = routing.RegisterTransitCallback(
            lambda from_index, to_index: distance_matrix[manager.IndexToNode(from_index)][
                manager.IndexToNode(to_index)
            ]
        )
        routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)

        demand_callback_index = routing.RegisterUnaryTransitCallback(
            lambda from_index: instance.nodes[manager.IndexToNode(from_index)].demand
        )
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,
            [instance.vehicle.capacity] * instance.vehicle.count,
            True,
            "Capacity",
        )

        time_callback_index = routing.RegisterTransitCallback(
            lambda from_index, to_index: service_times[manager.IndexToNode(from_index)]
            + time_matrix[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]
        )
        horizon = self._time_horizon(instance, time_matrix)
        routing.AddDimension(
            time_callback_index,
            horizon,
            horizon,
            False,
            "Time",
        )
        time_dimension = routing.GetDimensionOrDie("Time")
        self._apply_time_windows(instance, manager, routing, time_dimension)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = _enum_value(
            routing_enums_pb2.FirstSolutionStrategy,
            self.first_solution_strategy,
        )
        search_parameters.local_search_metaheuristic = _enum_value(
            routing_enums_pb2.LocalSearchMetaheuristic,
            self.local_search_metaheuristic,
        )
        seconds = int(self.time_limit_sec)
        nanos = int((self.time_limit_sec - seconds) * 1_000_000_000)
        search_parameters.time_limit.seconds = seconds
        search_parameters.time_limit.nanos = nanos

        assignment = routing.SolveWithParameters(search_parameters)
        runtime_sec = perf_counter() - start_time
        metadata: dict[str, Any] = {
            "status": "SOLUTION_FOUND" if assignment is not None else "NO_SOLUTION",
            "first_solution_strategy": self.first_solution_strategy,
            "local_search_metaheuristic": self.local_search_metaheuristic,
            "scale_factor": self.scale_factor,
            "time_limit_sec": self.time_limit_sec,
        }
        if assignment is None:
            return Solution(
                instance_name=instance.name,
                solver_name="ortools_routing",
                routes=(),
                objective=float("inf"),
                vehicles_used=0,
                total_distance=0.0,
                total_duration=0.0,
                feasible=False,
                runtime_sec=runtime_sec,
                metadata=metadata,
            )

        routes = self._extract_routes(instance, manager, routing, assignment, time_dimension)
        vehicles_used = len(routes)
        total_distance = sum(route.distance for route in routes)
        total_duration = sum(route.duration for route in routes)
        solution = Solution(
            instance_name=instance.name,
            solver_name="ortools_routing",
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

    def _apply_time_windows(
        self,
        instance: VRPTWInstance,
        manager: pywrapcp.RoutingIndexManager,
        routing: pywrapcp.RoutingModel,
        time_dimension: pywrapcp.RoutingDimension,
    ) -> None:
        for node_index, node in enumerate(instance.nodes):
            if node_index == 0:
                continue
            routing_index = manager.NodeToIndex(node_index)
            time_dimension.CumulVar(routing_index).SetRange(
                _scaled(node.ready_time, self.scale_factor),
                _scaled(node.due_time, self.scale_factor),
            )

        depot_start = _scaled(instance.depot.ready_time, self.scale_factor)
        depot_due = _scaled(instance.depot.due_time, self.scale_factor)
        for vehicle_id in range(instance.vehicle.count):
            time_dimension.CumulVar(routing.Start(vehicle_id)).SetRange(depot_start, depot_due)
            time_dimension.CumulVar(routing.End(vehicle_id)).SetRange(depot_start, depot_due)

    def _extract_routes(
        self,
        instance: VRPTWInstance,
        manager: pywrapcp.RoutingIndexManager,
        routing: pywrapcp.RoutingModel,
        assignment: pywrapcp.Assignment,
        time_dimension: pywrapcp.RoutingDimension,
    ) -> tuple[Route, ...]:
        routes: list[Route] = []
        for vehicle_id in range(instance.vehicle.count):
            route = self._extract_route(
                instance,
                manager,
                routing,
                assignment,
                time_dimension,
                vehicle_id,
            )
            if route.stops:
                routes.append(route)
        return tuple(routes)

    def _extract_route(
        self,
        instance: VRPTWInstance,
        manager: pywrapcp.RoutingIndexManager,
        routing: pywrapcp.RoutingModel,
        assignment: pywrapcp.Assignment,
        time_dimension: pywrapcp.RoutingDimension,
        vehicle_id: int,
    ) -> Route:
        index = routing.Start(vehicle_id)
        depot_start_time = assignment.Value(time_dimension.CumulVar(index)) / self.scale_factor
        previous_node = 0
        previous_departure = depot_start_time + instance.depot.service_time
        stops: list[RouteStop] = []
        distance = 0.0
        load = 0

        while not routing.IsEnd(index):
            next_index = assignment.Value(routing.NextVar(index))
            if routing.IsEnd(next_index):
                distance += float(instance.distance_matrix[previous_node, 0])
                scaled_end_time = (
                    assignment.Value(time_dimension.CumulVar(next_index)) / self.scale_factor
                )
                physical_end_time = previous_departure + float(
                    instance.time_matrix[previous_node, 0]
                )
                end_time = max(scaled_end_time, physical_end_time)
                return Route(
                    vehicle_id=vehicle_id,
                    stops=tuple(stops),
                    distance=distance,
                    duration=end_time - depot_start_time,
                    load=load,
                )

            node_index = manager.IndexToNode(next_index)
            customer = instance.nodes[node_index]
            arrival_time = previous_departure + float(
                instance.time_matrix[previous_node, node_index]
            )
            scaled_start_service_time = (
                assignment.Value(time_dimension.CumulVar(next_index)) / self.scale_factor
            )
            start_service_time = max(
                scaled_start_service_time,
                arrival_time,
                customer.ready_time,
            )
            departure_time = start_service_time + customer.service_time
            load += customer.demand
            distance += float(instance.distance_matrix[previous_node, node_index])
            stops.append(
                RouteStop(
                    customer_id=customer.id,
                    arrival_time=arrival_time,
                    start_service_time=start_service_time,
                    departure_time=departure_time,
                    load_after=load,
                )
            )
            previous_node = node_index
            previous_departure = departure_time
            index = next_index

        return Route(vehicle_id=vehicle_id, stops=(), distance=0.0, duration=0.0, load=0)

    def _time_horizon(self, instance: VRPTWInstance, time_matrix: list[list[int]]) -> int:
        max_due = max(_scaled(node.due_time, self.scale_factor) for node in instance.nodes)
        max_service = max(_scaled(node.service_time, self.scale_factor) for node in instance.nodes)
        max_travel = max(max(row) for row in time_matrix)
        return max_due + max_service + max_travel


def solve_ortools_routing(
    instance: VRPTWInstance,
    *,
    time_limit_sec: float = 30.0,
    scale_factor: int = 100,
    vehicle_weight: float = 100000.0,
    first_solution_strategy: str = "PATH_CHEAPEST_ARC",
    local_search_metaheuristic: str = "GUIDED_LOCAL_SEARCH",
) -> Solution:
    """Convenience wrapper around :class:`ORToolsRoutingSolver`."""

    return ORToolsRoutingSolver(
        time_limit_sec=time_limit_sec,
        scale_factor=scale_factor,
        vehicle_weight=vehicle_weight,
        first_solution_strategy=first_solution_strategy,
        local_search_metaheuristic=local_search_metaheuristic,
    ).solve(instance)


def _enum_value(enum_type: Any, name: str) -> int:
    try:
        return int(enum_type.DESCRIPTOR.enum_values_by_name[name].number)
    except KeyError as exc:
        raise ValueError(f"Unknown OR-Tools enum value: {name}") from exc


def _scaled(value: float, scale_factor: int) -> int:
    return round(value * scale_factor)
