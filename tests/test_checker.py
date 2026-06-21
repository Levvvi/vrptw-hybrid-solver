import numpy as np

from vrptw_hybrid.core.checker import check_solution
from vrptw_hybrid.core.models import (
    Customer,
    Route,
    RouteStop,
    Solution,
    VehicleSpec,
    VRPTWInstance,
)


def make_instance(capacity: int = 10, vehicle_count: int = 2) -> VRPTWInstance:
    depot = Customer(id=0, x=0.0, y=0.0, demand=0, ready_time=0.0, due_time=100.0, service_time=0.0)
    customers = (
        Customer(id=1, x=3.0, y=4.0, demand=2, ready_time=0.0, due_time=50.0, service_time=1.0),
        Customer(id=2, x=6.0, y=8.0, demand=3, ready_time=0.0, due_time=60.0, service_time=1.0),
    )
    matrix = np.array(
        [
            [0.0, 5.0, 10.0],
            [5.0, 0.0, 5.0],
            [10.0, 5.0, 0.0],
        ]
    )
    return VRPTWInstance(
        name="checker-mini",
        depot=depot,
        customers=customers,
        vehicle=VehicleSpec(capacity=capacity, count=vehicle_count),
        distance_matrix=matrix,
        time_matrix=matrix,
        metadata={},
    )


def make_feasible_solution() -> Solution:
    route = Route(
        vehicle_id=0,
        stops=(
            RouteStop(
                customer_id=1,
                arrival_time=5.0,
                start_service_time=5.0,
                departure_time=6.0,
                load_after=2,
            ),
            RouteStop(
                customer_id=2,
                arrival_time=11.0,
                start_service_time=11.0,
                departure_time=12.0,
                load_after=5,
            ),
        ),
        distance=20.0,
        duration=22.0,
        load=5,
    )
    return Solution(
        instance_name="checker-mini",
        solver_name="unit",
        routes=(route,),
        objective=100020.0,
        vehicles_used=1,
        total_distance=20.0,
        total_duration=22.0,
        feasible=True,
        runtime_sec=0.01,
        metadata={},
    )


def violation_text(solution: Solution, instance: VRPTWInstance) -> str:
    return "\n".join(check_solution(solution, instance).violations)


def test_feasible_solution_passes() -> None:
    report = check_solution(make_feasible_solution(), make_instance())

    assert report.feasible
    assert report.violations == ()


def test_missing_customer_is_reported() -> None:
    route = Route(
        vehicle_id=0,
        stops=(
            RouteStop(
                customer_id=1,
                arrival_time=5.0,
                start_service_time=5.0,
                departure_time=6.0,
                load_after=2,
            ),
        ),
        distance=10.0,
        duration=11.0,
        load=2,
    )
    solution = Solution(
        instance_name="checker-mini",
        solver_name="unit",
        routes=(route,),
        objective=100010.0,
        vehicles_used=1,
        total_distance=10.0,
        total_duration=11.0,
        feasible=False,
        runtime_sec=0.01,
        metadata={},
    )

    text = violation_text(solution, make_instance())

    assert "customer 2 was not visited" in text


def test_duplicate_customer_is_reported() -> None:
    route = Route(
        vehicle_id=0,
        stops=(
            RouteStop(1, 5.0, 5.0, 6.0, 2),
            RouteStop(1, 11.0, 11.0, 12.0, 4),
            RouteStop(2, 17.0, 17.0, 18.0, 7),
        ),
        distance=30.0,
        duration=28.0,
        load=7,
    )
    solution = Solution(
        instance_name="checker-mini",
        solver_name="unit",
        routes=(route,),
        objective=100030.0,
        vehicles_used=1,
        total_distance=30.0,
        total_duration=28.0,
        feasible=False,
        runtime_sec=0.01,
        metadata={},
    )

    text = violation_text(solution, make_instance())

    assert "customer 1 was visited 2 times" in text


def test_capacity_violation_is_reported() -> None:
    text = violation_text(make_feasible_solution(), make_instance(capacity=4))

    assert "capacity exceeded" in text


def test_time_window_violation_is_reported() -> None:
    route = Route(
        vehicle_id=0,
        stops=(
            RouteStop(1, 5.0, 5.0, 6.0, 2),
            RouteStop(2, 11.0, 70.0, 71.0, 5),
        ),
        distance=20.0,
        duration=81.0,
        load=5,
    )
    solution = Solution(
        instance_name="checker-mini",
        solver_name="unit",
        routes=(route,),
        objective=100020.0,
        vehicles_used=1,
        total_distance=20.0,
        total_duration=81.0,
        feasible=False,
        runtime_sec=0.01,
        metadata={},
    )

    text = violation_text(solution, make_instance())

    assert "violates time window" in text


def test_travel_time_violation_is_reported() -> None:
    route = Route(
        vehicle_id=0,
        stops=(
            RouteStop(1, 5.0, 5.0, 6.0, 2),
            RouteStop(2, 7.0, 7.0, 8.0, 5),
        ),
        distance=20.0,
        duration=18.0,
        load=5,
    )
    solution = Solution(
        instance_name="checker-mini",
        solver_name="unit",
        routes=(route,),
        objective=100020.0,
        vehicles_used=1,
        total_distance=20.0,
        total_duration=18.0,
        feasible=False,
        runtime_sec=0.01,
        metadata={},
    )

    text = violation_text(solution, make_instance())

    assert "earlier than travel-time minimum" in text


def test_depot_as_customer_is_reported() -> None:
    route = Route(
        vehicle_id=0,
        stops=(RouteStop(0, 0.0, 0.0, 0.0, 0),),
        distance=0.0,
        duration=0.0,
        load=0,
    )
    solution = Solution(
        instance_name="checker-mini",
        solver_name="unit",
        routes=(route,),
        objective=100000.0,
        vehicles_used=1,
        total_distance=0.0,
        total_duration=0.0,
        feasible=False,
        runtime_sec=0.01,
        metadata={},
    )

    text = violation_text(solution, make_instance())

    assert "depot cannot be visited as a customer" in text


def test_too_many_vehicles_is_reported() -> None:
    solution = make_feasible_solution()

    text = violation_text(solution, make_instance(vehicle_count=0))

    assert "route count 1 exceeds available vehicles 0" in text
    assert "vehicles_used 1 exceeds available vehicles 0" in text
