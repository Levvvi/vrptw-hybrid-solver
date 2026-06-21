"""Parser for Solomon VRPTW benchmark text files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
from numpy.typing import NDArray

from vrptw_hybrid.core.models import Customer, VehicleSpec, VRPTWInstance


class SolomonParseError(ValueError):
    """Raised when a Solomon benchmark file cannot be parsed."""


@dataclass(frozen=True, slots=True)
class _CustomerRecord:
    customer_id: int
    x: float
    y: float
    demand: int
    ready_time: float
    due_time: float
    service_time: float

    def to_customer(self) -> Customer:
        return Customer(
            id=self.customer_id,
            x=self.x,
            y=self.y,
            demand=self.demand,
            ready_time=self.ready_time,
            due_time=self.due_time,
            service_time=self.service_time,
        )


def parse_solomon(path: str | Path, limit_customers: int | None = None) -> VRPTWInstance:
    """Parse a Solomon VRPTW instance file into a :class:`VRPTWInstance`."""

    if limit_customers is not None and limit_customers < 0:
        raise ValueError("limit_customers must be non-negative")

    file_path = Path(path)
    lines = file_path.read_text(encoding="utf-8").splitlines()
    name = _parse_instance_name(lines, file_path)
    vehicle = _parse_vehicle_spec(lines)
    records = _parse_customer_records(lines)
    if not records:
        raise SolomonParseError(f"No customer records found in {file_path}")

    depot = records[0].to_customer()
    customer_records = records[1:]
    if limit_customers is not None:
        customer_records = customer_records[:limit_customers]
    customers = tuple(record.to_customer() for record in customer_records)

    nodes = (depot, *customers)
    matrix = _euclidean_matrix(nodes)
    return VRPTWInstance(
        name=name,
        depot=depot,
        customers=customers,
        vehicle=vehicle,
        distance_matrix=matrix,
        time_matrix=matrix.copy(),
        metadata={
            "format": "solomon",
            "source_path": str(file_path),
            "limit_customers": limit_customers,
        },
    )


def _parse_instance_name(lines: list[str], path: Path) -> str:
    for line in lines:
        stripped = line.strip()
        if stripped:
            return stripped
    raise SolomonParseError(f"Empty Solomon file: {path}")


def _parse_vehicle_spec(lines: list[str]) -> VehicleSpec:
    in_vehicle_section = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper().startswith("VEHICLE"):
            in_vehicle_section = True
            continue
        if not in_vehicle_section or not _starts_with_number(stripped):
            continue

        parts = stripped.split()
        if len(parts) < 2:
            raise SolomonParseError("Vehicle section must contain NUMBER and CAPACITY")
        try:
            count = int(float(parts[0]))
            capacity = int(float(parts[1]))
        except ValueError as exc:
            raise SolomonParseError(f"Invalid vehicle specification line: {stripped}") from exc
        return VehicleSpec(count=count, capacity=capacity)

    raise SolomonParseError("Vehicle section not found")


def _parse_customer_records(lines: list[str]) -> list[_CustomerRecord]:
    records: list[_CustomerRecord] = []
    in_customer_section = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper().startswith("CUSTOMER"):
            in_customer_section = True
            continue
        if not in_customer_section or not _starts_with_number(stripped):
            continue

        parts = stripped.split()
        if len(parts) != 7:
            raise SolomonParseError(
                f"Expected 7 customer fields, got {len(parts)} in line: {stripped}"
            )
        records.append(_parse_customer_record(parts, stripped))
    return records


def _parse_customer_record(parts: list[str], line: str) -> _CustomerRecord:
    try:
        return _CustomerRecord(
            customer_id=int(float(parts[0])),
            x=float(parts[1]),
            y=float(parts[2]),
            demand=int(float(parts[3])),
            ready_time=float(parts[4]),
            due_time=float(parts[5]),
            service_time=float(parts[6]),
        )
    except ValueError as exc:
        raise SolomonParseError(f"Invalid customer record line: {line}") from exc


def _euclidean_matrix(nodes: tuple[Customer, ...]) -> NDArray[np.float64]:
    coordinates = np.array([(node.x, node.y) for node in nodes], dtype=float)
    deltas = coordinates[:, np.newaxis, :] - coordinates[np.newaxis, :, :]
    return cast("NDArray[np.float64]", np.linalg.norm(deltas, axis=2))


def _starts_with_number(line: str) -> bool:
    first = line.split(maxsplit=1)[0]
    try:
        float(first)
    except ValueError:
        return False
    return True
