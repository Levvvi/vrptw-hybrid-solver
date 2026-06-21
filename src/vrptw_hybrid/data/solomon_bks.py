"""Small verified Solomon VRPTW best-known-solution reference table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SINTEF_100_CUSTOMERS_URL = "https://www.sintef.no/projectweb/top/vrptw/100-customers/"


@dataclass(frozen=True, slots=True)
class SolomonBKS:
    instance: str
    best_vehicles: int
    best_distance: float
    source: str
    source_url: str


SOLOMON_BKS: dict[str, SolomonBKS] = {
    "c101": SolomonBKS(
        instance="C101",
        best_vehicles=10,
        best_distance=828.94,
        source="SINTEF VRPTW 100 customers table, RT/SAM::OPT entry",
        source_url=SINTEF_100_CUSTOMERS_URL,
    ),
    "r101": SolomonBKS(
        instance="R101",
        best_vehicles=19,
        best_distance=1650.80,
        source="SINTEF VRPTW 100 customers table, Homberger entry",
        source_url=SINTEF_100_CUSTOMERS_URL,
    ),
    "rc101": SolomonBKS(
        instance="RC101",
        best_vehicles=14,
        best_distance=1696.95,
        source="SINTEF VRPTW 100 customers table, corrected RC101B entry",
        source_url=SINTEF_100_CUSTOMERS_URL,
    ),
}


def get_solomon_bks(instance_name: str) -> SolomonBKS | None:
    """Return a verified BKS reference for an instance name when available."""

    return SOLOMON_BKS.get(normalize_instance_name(instance_name))


def bks_gap_fields(
    instance_name: str,
    *,
    vehicles_used: int,
    total_distance: float,
) -> dict[str, Any]:
    """Return CSV-ready BKS and gap fields for a solution."""

    reference = get_solomon_bks(instance_name)
    if reference is None:
        return _empty_gap_fields()

    vehicle_gap = vehicles_used - reference.best_vehicles
    vehicle_match = vehicle_gap == 0
    distance_gap = total_distance - reference.best_distance if vehicle_match else None
    distance_gap_pct = (
        distance_gap / reference.best_distance * 100.0
        if distance_gap is not None and reference.best_distance
        else None
    )
    return {
        "bks_vehicles": reference.best_vehicles,
        "bks_distance": reference.best_distance,
        "bks_source": reference.source,
        "bks_source_url": reference.source_url,
        "vehicle_gap": vehicle_gap,
        "vehicle_match": vehicle_match,
        "distance_gap": distance_gap,
        "distance_gap_pct": distance_gap_pct,
    }


def normalize_instance_name(instance_name: str) -> str:
    """Normalize common Solomon names while preserving strict table lookup."""

    normalized = instance_name.strip().lstrip("\ufeff").lower()
    if "." in normalized:
        normalized = normalized.split(".", 1)[0]
    return normalized


def _empty_gap_fields() -> dict[str, Any]:
    return {
        "bks_vehicles": None,
        "bks_distance": None,
        "bks_source": "",
        "bks_source_url": "",
        "vehicle_gap": None,
        "vehicle_match": None,
        "distance_gap": None,
        "distance_gap_pct": None,
    }
