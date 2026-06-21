from pathlib import Path

import numpy as np
import pytest

from vrptw_hybrid.data.solomon import SolomonParseError, parse_solomon

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "mini_solomon.txt"


def test_parse_solomon_fixture() -> None:
    instance = parse_solomon(FIXTURE)

    assert instance.name == "MINI_C101"
    assert instance.depot.id == 0
    assert len(instance.customers) == 10
    assert instance.vehicle.count == 3
    assert instance.vehicle.capacity == 15
    assert instance.distance_matrix.shape == (11, 11)
    assert np.allclose(instance.distance_matrix, instance.distance_matrix.T)
    assert np.allclose(np.diag(instance.distance_matrix), 0.0)
    assert np.allclose(instance.time_matrix, instance.distance_matrix)


def test_parse_solomon_limit_customers() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=8)

    assert len(instance.customers) == 8
    assert instance.node_count == 9
    assert instance.distance_matrix.shape == (9, 9)
    assert instance.metadata["limit_customers"] == 8


def test_parse_solomon_uses_euclidean_distance() -> None:
    instance = parse_solomon(FIXTURE, limit_customers=1)

    assert instance.distance_matrix[0, 1] == pytest.approx(5.0)


def test_parse_solomon_rejects_bad_customer_field_count(tmp_path: Path) -> None:
    malformed = tmp_path / "bad_solomon.txt"
    malformed.write_text(
        "\n".join(
            [
                "BAD",
                "VEHICLE",
                "NUMBER CAPACITY",
                "1 10",
                "CUSTOMER",
                "CUST NO. XCOORD. YCOORD. DEMAND READY TIME DUE DATE SERVICE TIME",
                "0 0 0 0 0 100",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(SolomonParseError, match="Expected 7 customer fields"):
        parse_solomon(malformed)


def test_parse_solomon_rejects_negative_limit() -> None:
    with pytest.raises(ValueError, match="limit_customers must be non-negative"):
        parse_solomon(FIXTURE, limit_customers=-1)
