import pytest

from vrptw_hybrid.data.solomon_bks import bks_gap_fields, get_solomon_bks


def test_get_solomon_bks_returns_verified_reference() -> None:
    reference = get_solomon_bks("C101")

    assert reference is not None
    assert reference.best_vehicles == 10
    assert reference.best_distance == pytest.approx(828.94)
    assert "SINTEF" in reference.source


def test_bks_gap_fields_compute_distance_gap_only_when_vehicle_count_matches() -> None:
    matching = bks_gap_fields("R101", vehicles_used=19, total_distance=1660.80)
    mismatching = bks_gap_fields("R101", vehicles_used=20, total_distance=1660.80)

    assert matching["vehicle_gap"] == 0
    assert matching["vehicle_match"] is True
    assert matching["distance_gap"] == pytest.approx(10.0)
    assert matching["distance_gap_pct"] == pytest.approx(10.0 / 1650.80 * 100.0)
    assert mismatching["vehicle_gap"] == 1
    assert mismatching["vehicle_match"] is False
    assert mismatching["distance_gap"] is None
    assert mismatching["distance_gap_pct"] is None


def test_unknown_bks_returns_empty_gap_fields() -> None:
    fields = bks_gap_fields("MINI_C101", vehicles_used=2, total_distance=150.0)

    assert fields["bks_vehicles"] is None
    assert fields["bks_distance"] is None
    assert fields["vehicle_gap"] is None
