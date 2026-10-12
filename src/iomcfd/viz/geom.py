"""Small geometry helpers for view definitions (numpy only, no ParaView)."""

from __future__ import annotations

import math

import numpy as np


def heel_basis(heel_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """World directions of the boat's y and z axes for a boat heeled about x."""
    h = math.radians(heel_deg)
    return np.array([0.0, math.cos(h), math.sin(h)]), np.array([0.0, -math.sin(h), math.cos(h)])


def box_center(box) -> np.ndarray:
    return 0.5 * (np.asarray(box[:3], float) + np.asarray(box[3:], float))


def box_size(box) -> np.ndarray:
    return np.asarray(box[3:], float) - np.asarray(box[:3], float)


def heeled(point, heel_deg: float, pivot=(0.0, 0.0, 0.0)) -> np.ndarray:
    """Boat-frame point -> world, for a heel rotation about x through pivot."""
    ey, ez = heel_basis(heel_deg)
    q = np.asarray(point, float) - np.asarray(pivot, float)
    return np.asarray(pivot, float) + np.array([q[0], 0, 0]) + q[1] * ey + q[2] * ez
