"""
path_geometry.py
================
Low-level geometry utilities: parametric curves, Bézier evaluation,
rotation / translation helpers, and path interpolation used by the
rose generator and animation engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DrawPath:
    """A single drawable stroke with all rendering metadata."""
    coords: np.ndarray          # shape (N, 2)  — (x, y) in normalised units
    color: str = "#FF4FD8"      # hex colour
    stroke_width: float = 1.5
    glow_intensity: float = 1.0
    layer_order: int = 0        # lower numbers draw first
    phase: int = 1              # animation phase 1-9
    phase_start: float = 0.0   # normalised [0,1] start within phase
    alpha: float = 1.0


@dataclass
class RoseGeometry:
    """Complete geometry description returned by the generator."""
    paths: List[DrawPath] = field(default_factory=list)
    canvas_w: float = 1080.0
    canvas_h: float = 1920.0
    center_x: float = 540.0
    center_y: float = 820.0
    rose_radius: float = 360.0


# ---------------------------------------------------------------------------
# Bézier helpers
# ---------------------------------------------------------------------------

def cubic_bezier(p0, p1, p2, p3, n: int = 120) -> np.ndarray:
    """Return *n* points along a cubic Bézier curve."""
    t = np.linspace(0, 1, n)
    t2 = t * t
    t3 = t2 * t
    mt = 1 - t
    mt2 = mt * mt
    mt3 = mt2 * mt
    p0, p1, p2, p3 = (np.asarray(x, float) for x in (p0, p1, p2, p3))
    pts = (mt3[:, None] * p0 +
           3 * mt2[:, None] * t[:, None] * p1 +
           3 * mt[:, None] * t2[:, None] * p2 +
           t3[:, None] * p3)
    return pts


def quadratic_bezier(p0, p1, p2, n: int = 80) -> np.ndarray:
    """Return *n* points along a quadratic Bézier curve."""
    t = np.linspace(0, 1, n)
    mt = 1 - t
    p0, p1, p2 = (np.asarray(x, float) for x in (p0, p1, p2))
    pts = (mt[:, None] ** 2 * p0 +
           2 * mt[:, None] * t[:, None] * p1 +
           t[:, None] ** 2 * p2)
    return pts


# ---------------------------------------------------------------------------
# Rotation / translation
# ---------------------------------------------------------------------------

def rotate_points(pts: np.ndarray, angle_rad: float,
                  cx: float = 0.0, cy: float = 0.0) -> np.ndarray:
    """Rotate *pts* (N,2) by *angle_rad* around (cx, cy)."""
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)
    R = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
    shifted = pts - np.array([cx, cy])
    return shifted @ R.T + np.array([cx, cy])


def scale_points(pts: np.ndarray, sx: float, sy: float,
                 cx: float = 0.0, cy: float = 0.0) -> np.ndarray:
    """Scale *pts* around (cx, cy)."""
    shifted = pts - np.array([cx, cy])
    scaled = shifted * np.array([sx, sy])
    return scaled + np.array([cx, cy])


def translate_points(pts: np.ndarray, dx: float, dy: float) -> np.ndarray:
    return pts + np.array([dx, dy])


# ---------------------------------------------------------------------------
# Path interpolation for progressive drawing
# ---------------------------------------------------------------------------

def cumulative_arc_length(pts: np.ndarray) -> np.ndarray:
    """Return cumulative arc-length array of shape (N,)."""
    diffs = np.diff(pts, axis=0)
    seg_lens = np.hypot(diffs[:, 0], diffs[:, 1])
    return np.concatenate([[0.0], np.cumsum(seg_lens)])


def partial_path(pts: np.ndarray, fraction: float) -> np.ndarray:
    """Return the first *fraction* (0-1) of path *pts* by arc length."""
    if fraction <= 0:
        return pts[:1]
    if fraction >= 1:
        return pts
    arc = cumulative_arc_length(pts)
    total = arc[-1]
    if total == 0:
        return pts
    target = fraction * total
    idx = np.searchsorted(arc, target)
    idx = min(idx, len(pts) - 1)
    if idx == 0:
        return pts[:1]
    # interpolate last segment
    t_prev = arc[idx - 1]
    t_next = arc[idx]
    seg = t_next - t_prev
    if seg > 0:
        alpha = (target - t_prev) / seg
        interp = pts[idx - 1] + alpha * (pts[idx] - pts[idx - 1])
        return np.vstack([pts[:idx], interp])
    return pts[:idx]


# ---------------------------------------------------------------------------
# Parametric polar curve helpers
# ---------------------------------------------------------------------------

def polar_curve(r_func, theta_start: float = 0, theta_end: float = 2 * math.pi,
                n: int = 512,
                cx: float = 0.0, cy: float = 0.0) -> np.ndarray:
    """Sample a polar curve r(theta) and return Cartesian (x, y) points."""
    thetas = np.linspace(theta_start, theta_end, n)
    r = np.array([r_func(th) for th in thetas])
    x = cx + r * np.cos(thetas)
    y = cy + r * np.sin(thetas)
    return np.stack([x, y], axis=1)


def smooth_closed_curve(pts: np.ndarray, n_out: int = 300) -> np.ndarray:
    """
    Given a set of key points, produce a smooth closed curve using a
    simple centripetal Catmull-Rom spline.
    """
    # Close the loop
    closed = np.vstack([pts, pts[0]])
    result = []
    n = len(closed) - 1
    for i in range(n):
        p0 = closed[max(i - 1, 0)]
        p1 = closed[i]
        p2 = closed[i + 1]
        p3 = closed[min(i + 2, n)]
        # Catmull-Rom
        t = np.linspace(0, 1, max(n_out // n, 4), endpoint=(i == n - 1))
        for ti in t:
            t2 = ti * ti
            t3 = t2 * ti
            pt = 0.5 * (
                (2 * p1) +
                (-p0 + p2) * ti +
                (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                (-p0 + 3 * p1 - 3 * p2 + p3) * t3
            )
            result.append(pt)
    return np.array(result)
