import numpy as np
import pytest

from vrptw_hybrid.data.distance_matrix import (
    euclidean_distance_matrix,
    round_matrix,
    scale_to_int,
)


def test_euclidean_distance_matrix_uses_3_4_5_triangle() -> None:
    matrix = euclidean_distance_matrix([(0.0, 0.0), (3.0, 4.0)])

    assert matrix.shape == (2, 2)
    assert matrix[0, 1] == pytest.approx(5.0)
    assert matrix[1, 0] == pytest.approx(5.0)
    assert matrix[0, 0] == pytest.approx(0.0)


def test_round_matrix_returns_rounded_float_copy() -> None:
    matrix = np.array([[0.0, 1.2345], [1.2345, 0.0]])

    rounded = round_matrix(matrix, decimals=2)

    assert rounded.dtype.kind == "f"
    assert rounded[0, 1] == pytest.approx(1.23)
    assert matrix[0, 1] == pytest.approx(1.2345)


def test_round_matrix_without_decimals_returns_copy() -> None:
    matrix = np.array([[0.0, 1.25], [1.25, 0.0]])

    copied = round_matrix(matrix)
    copied[0, 1] = 9.0

    assert matrix[0, 1] == pytest.approx(1.25)


def test_scale_to_int_rounds_to_integer_matrix() -> None:
    matrix = np.array([[0.0, 1.234], [1.234, 0.0]])

    scaled = scale_to_int(matrix, factor=100)

    assert scaled.dtype == np.int64
    assert scaled[0, 1] == 123


def test_scale_to_int_rejects_non_positive_factor() -> None:
    with pytest.raises(ValueError, match="factor must be positive"):
        scale_to_int([[0.0]], factor=0)
