"""Distance and travel-time matrix utilities."""

from __future__ import annotations

from typing import cast

import numpy as np
from numpy.typing import ArrayLike, NDArray


def euclidean_distance_matrix(points: ArrayLike) -> NDArray[np.float64]:
    """Compute a pairwise Euclidean distance matrix for 2D or higher-dimensional points."""

    coordinates = np.asarray(points, dtype=float)
    if coordinates.ndim != 2:
        raise ValueError("points must be a 2D array-like object")
    if coordinates.shape[0] == 0:
        raise ValueError("points must contain at least one point")
    if coordinates.shape[1] == 0:
        raise ValueError("points must contain at least one coordinate dimension")
    if not np.isfinite(coordinates).all():
        raise ValueError("points must contain only finite values")

    deltas = coordinates[:, np.newaxis, :] - coordinates[np.newaxis, :, :]
    return cast("NDArray[np.float64]", np.linalg.norm(deltas, axis=2))


def round_matrix(matrix: ArrayLike, decimals: int | None = None) -> NDArray[np.float64]:
    """Return a float matrix copy, optionally rounded to a fixed number of decimals."""

    values = _as_finite_matrix(matrix)
    if decimals is None:
        return values.copy()
    return cast("NDArray[np.float64]", np.round(values, decimals=decimals))


def scale_to_int(matrix: ArrayLike, factor: float) -> NDArray[np.int64]:
    """Scale a numeric matrix and round it to int64 values for integer solvers."""

    if factor <= 0:
        raise ValueError("factor must be positive")

    values = _as_finite_matrix(matrix)
    scaled = np.rint(values * factor).astype(np.int64)
    return cast("NDArray[np.int64]", scaled)


def _as_finite_matrix(matrix: ArrayLike) -> NDArray[np.float64]:
    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2:
        raise ValueError("matrix must be a 2D array-like object")
    if not np.isfinite(values).all():
        raise ValueError("matrix must contain only finite values")
    return cast("NDArray[np.float64]", values)
