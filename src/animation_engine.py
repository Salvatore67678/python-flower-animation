"""
animation_engine.py
===================
Converts a RoseGeometry into a sequence of frames that progressively
reveal the rose stroke-by-stroke.

Animation phases
----------------
1  Tiny pink glow dot at centre
2  Inner petals draw themselves
3  Middle petals appear
4  Outer petals grow
5  Stem extends downward
6  Leaves (outline + veins) appear
7  Decorative particles fade in
8  Glow ring pulses
9  Final hold (complete image, optionally slow-zoom)

The engine returns a list of PIL Image objects (or a generator) so that
callers can either collect all frames or write them one by one.
"""

from __future__ import annotations

import math
from typing import Dict, Generator, List, Optional

import numpy as np
from PIL import Image

from .path_geometry import DrawPath, RoseGeometry, partial_path
from .neon_renderer import render_frame


# ---------------------------------------------------------------------------
# Phase timing table  (phase → normalised time range [0, 1])
# ---------------------------------------------------------------------------

PHASE_RANGES = {
    1: (0.00, 0.04),   # centre glow dot
    2: (0.04, 0.22),   # inner petals
    3: (0.22, 0.45),   # middle petals
    4: (0.45, 0.72),   # outer petals
    5: (0.72, 0.80),   # stem
    6: (0.80, 0.92),   # leaves
    7: (0.92, 0.97),   # particles
    8: (0.97, 1.00),   # glow ring
    9: (1.00, 1.00),   # hold (handled separately)
}


def _ease_in_out(t: float) -> float:
    """Smooth cubic ease-in-out."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _ease_out(t: float) -> float:
    return 1 - (1 - t) ** 2


def compute_fraction_map(
    geometry: RoseGeometry,
    global_t: float,  # [0, 1] — drawing progress (not including hold)
) -> Dict[int, float]:
    """
    For every DrawPath in *geometry*, return a dict {path_index: draw_fraction}.
    *global_t* = 0 → nothing drawn; *global_t* = 1 → fully drawn.
    """
    fmap: Dict[int, float] = {}
    paths = geometry.paths

    for i, path in enumerate(paths):
        phase = path.phase
        p_start_t, p_end_t = PHASE_RANGES.get(phase, (0.0, 1.0))
        if p_end_t <= p_start_t:
            fmap[i] = 1.0 if global_t >= p_start_t else 0.0
            continue

        # How far through this phase?
        phase_len = p_end_t - p_start_t
        local_t = (global_t - p_start_t) / phase_len  # can be <0 or >1

        # Within the phase, apply the path's own phase_start offset
        # so that multiple paths within one phase stagger nicely.
        path_start = p_start_t + path.phase_start * phase_len
        path_local = (global_t - path_start) / (phase_len * (1 - path.phase_start + 0.01))
        path_local = max(0.0, min(path_local, 1.0))

        fmap[i] = _ease_in_out(path_local)

    return fmap


# ---------------------------------------------------------------------------
# Zoom helper
# ---------------------------------------------------------------------------

def apply_slow_zoom(image: Image.Image, zoom_factor: float) -> Image.Image:
    """
    Zoom into the centre of the image by *zoom_factor* (1.0 = no zoom).
    Returns cropped + resized image at original size.
    """
    if abs(zoom_factor - 1.0) < 0.001:
        return image
    W, H = image.size
    new_w = int(W / zoom_factor)
    new_h = int(H / zoom_factor)
    x0 = (W - new_w) // 2
    y0 = (H - new_h) // 2
    cropped = image.crop((x0, y0, x0 + new_w, y0 + new_h))
    return cropped.resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------------------
# Frame generator
# ---------------------------------------------------------------------------

def generate_frames(
    geometry: RoseGeometry,
    fps: int = 30,
    drawing_duration: float = 9.0,
    hold_duration: float = 3.0,
    glow_intensity: float = 1.0,
    enable_zoom: bool = False,
    zoom_amount: float = 1.08,
    supersampling: int = 2,
    progress_callback=None,
) -> Generator[Image.Image, None, None]:
    """
    Yield PIL Image frames one at a time.

    *progress_callback(fraction)*: called each frame, 0→1.
    """
    draw_frames = max(1, int(drawing_duration * fps))
    hold_frames = max(1, int(hold_duration * fps))
    total_frames = draw_frames + hold_frames

    for frame_idx in range(total_frames):
        # Drawing phase
        if frame_idx < draw_frames:
            global_t = frame_idx / draw_frames
        else:
            global_t = 1.0  # fully drawn during hold

        fmap = compute_fraction_map(geometry, global_t)
        frame = render_frame(geometry, fraction_map=fmap,
                             glow_intensity=glow_intensity,
                             supersampling=supersampling)

        # Optional slow zoom during hold
        if enable_zoom and frame_idx >= draw_frames:
            hold_t = (frame_idx - draw_frames) / max(hold_frames - 1, 1)
            zf = 1.0 + (zoom_amount - 1.0) * _ease_out(hold_t)
            frame = apply_slow_zoom(frame, zf)

        if progress_callback:
            progress_callback(frame_idx / total_frames)

        yield frame


def collect_frames(
    geometry: RoseGeometry,
    fps: int = 30,
    drawing_duration: float = 9.0,
    hold_duration: float = 3.0,
    glow_intensity: float = 1.0,
    enable_zoom: bool = False,
    zoom_amount: float = 1.08,
    supersampling: int = 2,
    progress_callback=None,
) -> List[Image.Image]:
    """Collect and return all frames as a list."""
    return list(generate_frames(
        geometry, fps=fps,
        drawing_duration=drawing_duration,
        hold_duration=hold_duration,
        glow_intensity=glow_intensity,
        enable_zoom=enable_zoom,
        zoom_amount=zoom_amount,
        supersampling=supersampling,
        progress_callback=progress_callback,
    ))
