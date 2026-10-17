"""
rose_generator.py
=================
Mathematical art engine. Generates all drawable paths that make up the
botanical neon rose:
- Phase 1: Core spiral whorl (golden logarithmic spiral)
- Phase 2: Concentric bud cups & tightly curled inner petals with delicate striations
- Phase 3: Broad cupped middle petals with reflexed rim highlights and organic venation
- Phase 4: Large sweeping outer petals with ruffled contours and reflexed edges
- Phase 5: Calyx cup, sepals, gracefully arched stem, and rose thorns
- Phase 6: Botanical leaflets with petioles, midribs, and lateral pinnate veins
- Phase 7: Floating neon sparkles & ambient pollen particles
- Phase 8: Radiant outer aura glow rings

All paths are returned as DrawPath objects with full metadata:
coordinates, color, stroke_width, glow_intensity, phase, and phase_start.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from .path_geometry import (
    DrawPath, RoseGeometry,
    cubic_bezier, quadratic_bezier,
    rotate_points, scale_points, translate_points,
)

# ---------------------------------------------------------------------------
# Default Palette Constants
# ---------------------------------------------------------------------------
C_BRIGHT_PINK   = "#FF4FD8"   # Primary neon
C_SOFT_PINK     = "#FFB5F2"   # Secondary glow
C_PURPLE        = "#A855F7"   # Accent colour
C_WHITE_PINK    = "#FFF0FB"   # White-hot core highlight
C_PALE          = "#FFE8FA"   # Luminous pale pink
C_DEEP_VIOLET   = "#7E22CE"   # Deep ambient ring


# ---------------------------------------------------------------------------
# Rose Configuration Data Class
# ---------------------------------------------------------------------------
class RoseConfig:
    """All user-tunable parameters for the rose generation engine."""

    def __init__(
        self,
        seed: int = 42,
        n_inner: int = 6,
        n_middle: int = 9,
        n_outer: int = 13,
        stem_curvature: float = 0.35,
        n_leaves: int = 2,
        line_thickness: float = 1.5,
        detail_level: int = 3,
        primary_color: str = C_BRIGHT_PINK,
        secondary_color: str = C_SOFT_PINK,
        accent_color: str = C_PURPLE,
        glow_intensity: float = 1.0,
        canvas_w: int = 1080,
        canvas_h: int = 1920,
        show_particles: bool = True,
    ):
        self.seed = int(seed)
        self.n_inner = max(3, int(n_inner))
        self.n_middle = max(4, int(n_middle))
        self.n_outer = max(5, int(n_outer))
        self.stem_curvature = float(np.clip(stem_curvature, 0.0, 1.0))
        self.n_leaves = max(0, min(int(n_leaves), 4))
        self.line_thickness = float(np.clip(line_thickness, 0.5, 5.0))
        self.detail_level = int(np.clip(detail_level, 1, 5))
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.accent_color = accent_color
        self.glow_intensity = float(np.clip(glow_intensity, 0.1, 3.0))
        self.canvas_w = int(canvas_w)
        self.canvas_h = int(canvas_h)
        self.show_particles = bool(show_particles)


# ---------------------------------------------------------------------------
# Main Rose Generator Engine
# ---------------------------------------------------------------------------
class RoseGenerator:
    """
    Deterministic botanical rose geometry generator.

    Usage::

        cfg = RoseConfig(seed=42)
        geo = RoseGenerator(cfg).generate()
        # geo.paths is a list of DrawPath objects
    """

    def __init__(self, config: RoseConfig):
        self.cfg = config
        self.rng = random.Random(config.seed)
        self.np_rng = np.random.default_rng(config.seed)

    def generate(self) -> RoseGeometry:
        cfg = self.cfg
        rng = self.rng
        
        # Position rose proportionally on canvas
        # Slightly above vertical center (at 0.38 of height) to leave room for stem
        center_x = cfg.canvas_w / 2.0
        center_y = cfg.canvas_h * 0.38
        rose_radius = min(cfg.canvas_w, cfg.canvas_h) * 0.23

        geo = RoseGeometry(
            canvas_w=float(cfg.canvas_w),
            canvas_h=float(cfg.canvas_h),
            center_x=center_x,
            center_y=center_y,
            rose_radius=rose_radius,
        )

        cx, cy, R = geo.center_x, geo.center_y, geo.rose_radius
        lw = cfg.line_thickness
        pri = cfg.primary_color
        sec = cfg.secondary_color
        acc = cfg.accent_color
        gi  = cfg.glow_intensity

        paths: List[DrawPath] = []

        # ===================================================================
        # Phase 1: Core Spiral Whorl (The bud's center)
        # ===================================================================
        theta = np.linspace(0.4, 5.8 * math.pi, 260)
        r_spiral = (R * 0.010) * (theta ** 1.38)
        whorl_x = cx + r_spiral * np.cos(theta)
        whorl_y = cy + r_spiral * np.sin(theta) * 0.88
        spiral_pts = np.stack([whorl_x, whorl_y], axis=1)
        paths.append(DrawPath(
            coords=spiral_pts,
            color=C_WHITE_PINK,
            stroke_width=lw * 1.5,
            glow_intensity=gi * 1.5,
            layer_order=0,
            phase=1,
            phase_start=0.0,
        ))

        # Nested concentric bud cups
        n_bud_cups = 5
        for i in range(n_bud_cups):
            t_start = (i * 1.35) + rng.uniform(-0.08, 0.08)
            arc_len = math.pi * rng.uniform(1.15, 1.45)
            th_arc = np.linspace(t_start, t_start + arc_len, 80)
            r_arc = (R * 0.075) * (1.0 + 0.38 * i)
            bx = cx + r_arc * np.cos(th_arc) * rng.uniform(0.96, 1.04)
            by = cy + r_arc * np.sin(th_arc) * 0.86
            cup_pts = np.stack([bx, by], axis=1)

            paths.append(DrawPath(
                coords=cup_pts,
                color=pri,
                stroke_width=lw * 1.3,
                glow_intensity=gi * 1.2,
                layer_order=1,
                phase=2,
                phase_start=i / n_bud_cups * 0.5,
            ))
            if len(cup_pts) > 24:
                paths.append(DrawPath(
                    coords=cup_pts[12:-12],
                    color=sec,
                    stroke_width=lw * 0.6,
                    glow_intensity=gi * 0.8,
                    layer_order=2,
                    phase=2,
                    phase_start=(i + 0.2) / n_bud_cups * 0.5,
                ))

        # ===================================================================
        # Phase 2: Inner Petals
        # ===================================================================
        n_inner = cfg.n_inner
        for i in range(n_inner):
            angle = (2 * math.pi * i / n_inner) + (i * 0.32) + rng.uniform(-0.1, 0.1)
            dist = R * rng.uniform(0.12, 0.18)
            base_pt = [cx + dist * math.cos(angle), cy + dist * math.sin(angle) * 0.86]
            petal_len = R * rng.uniform(0.34, 0.44)
            petal_w = petal_len * rng.uniform(0.78, 0.98)
            axis_angle = angle + rng.uniform(0.4, 0.75)

            pts = self._build_curved_petal(base_pt, axis_angle, petal_len, petal_w,
                                          curl=rng.uniform(0.1, 0.25),
                                          roundness=0.92)
            paths.append(DrawPath(
                coords=pts,
                color=pri,
                stroke_width=lw * 1.4,
                glow_intensity=gi * 1.2,
                layer_order=10,
                phase=2,
                phase_start=0.5 + 0.5 * (i / n_inner),
            ))

            # Inner delicate striations
            if cfg.detail_level >= 2:
                for fi in [-0.22, 0.0, 0.22]:
                    fold = self._build_curved_striation(base_pt, axis_angle,
                                                        petal_len * 0.65, fi, petal_w)
                    paths.append(DrawPath(
                        coords=fold,
                        color=acc,
                        stroke_width=lw * 0.5,
                        glow_intensity=gi * 0.6,
                        layer_order=11,
                        phase=2,
                        phase_start=0.5 + 0.5 * ((i + 0.3) / n_inner),
                    ))

        # ===================================================================
        # Phase 3: Middle Petals
        # ===================================================================
        golden_angle = 2.3999632  # ~137.5 degrees
        n_middle = cfg.n_middle
        for i in range(n_middle):
            angle = (i * golden_angle) + rng.uniform(-0.1, 0.1)
            dist = R * rng.uniform(0.22, 0.36)
            base_pt = [cx + dist * math.cos(angle), cy + dist * math.sin(angle) * 0.86]
            petal_len = R * rng.uniform(0.56, 0.72)
            petal_w = petal_len * rng.uniform(0.85, 1.15)
            axis_angle = angle + rng.uniform(0.18, 0.45)

            pts = self._build_curved_petal(base_pt, axis_angle, petal_len, petal_w,
                                          curl=rng.uniform(0.15, 0.32),
                                          roundness=1.0)
            paths.append(DrawPath(
                coords=pts,
                color=pri,
                stroke_width=lw * 1.5,
                glow_intensity=gi * 1.1,
                layer_order=20,
                phase=3,
                phase_start=i / n_middle,
            ))

            # Reflexed rim highlight
            rim = pts[len(pts)//4 : 3*len(pts)//4]
            paths.append(DrawPath(
                coords=rim,
                color=C_WHITE_PINK,
                stroke_width=lw * 0.75,
                glow_intensity=gi * 1.0,
                layer_order=21,
                phase=3,
                phase_start=(i + 0.2) / n_middle,
            ))

            # Contour striations
            if cfg.detail_level >= 2:
                for fi in [-0.3, -0.12, 0.12, 0.3]:
                    fold = self._build_curved_striation(base_pt, axis_angle,
                                                        petal_len * rng.uniform(0.6, 0.78),
                                                        fi, petal_w)
                    paths.append(DrawPath(
                        coords=fold,
                        color=acc,
                        stroke_width=lw * 0.5,
                        glow_intensity=gi * 0.5,
                        layer_order=22,
                        phase=3,
                        phase_start=(i + 0.35) / n_middle,
                    ))

        # ===================================================================
        # Phase 4: Outer Petals
        # ===================================================================
        n_outer = cfg.n_outer
        for i in range(n_outer):
            angle = (i * golden_angle * 1.01) + rng.uniform(-0.12, 0.12)
            dist = R * rng.uniform(0.38, 0.52)
            base_pt = [cx + dist * math.cos(angle), cy + dist * math.sin(angle) * 0.86]
            petal_len = R * rng.uniform(0.82, 1.08)
            petal_w = petal_len * rng.uniform(0.92, 1.25)
            axis_angle = angle + rng.uniform(0.08, 0.32)

            pts = self._build_curved_petal(base_pt, axis_angle, petal_len, petal_w,
                                          curl=rng.uniform(0.2, 0.45),
                                          roundness=1.1)
            paths.append(DrawPath(
                coords=pts,
                color=pri,
                stroke_width=lw * 1.6,
                glow_intensity=gi * 1.0,
                layer_order=30,
                phase=4,
                phase_start=i / n_outer,
            ))

            # Rim highlight
            rim = pts[len(pts)//4 : 3*len(pts)//4]
            paths.append(DrawPath(
                coords=rim,
                color=sec,
                stroke_width=lw * 0.85,
                glow_intensity=gi * 0.9,
                layer_order=31,
                phase=4,
                phase_start=(i + 0.2) / n_outer,
            ))

            # Radiating striations
            if cfg.detail_level >= 3:
                for fi in [-0.35, -0.18, 0.0, 0.18, 0.35]:
                    fold = self._build_curved_striation(base_pt, axis_angle,
                                                        petal_len * rng.uniform(0.65, 0.82),
                                                        fi, petal_w)
                    paths.append(DrawPath(
                        coords=fold,
                        color=acc,
                        stroke_width=lw * 0.45,
                        glow_intensity=gi * 0.45,
                        layer_order=32,
                        phase=4,
                        phase_start=(i + 0.4) / n_outer,
                    ))

        # ===================================================================
        # Phase 5: Calyx, Sepals, Stem & Thorns
        # ===================================================================
        calyx_cx = cx + rng.uniform(-6, 6)
        calyx_cy = cy + R * 0.74
        calyx_cup_w = R * 0.22
        calyx_cup_h = R * 0.15

        # Receptacle cup
        cup_l = np.array([calyx_cx - calyx_cup_w * 0.5, calyx_cy])
        cup_r = np.array([calyx_cx + calyx_cup_w * 0.5, calyx_cy])
        cup_bot = np.array([calyx_cx, calyx_cy + calyx_cup_h])
        cup_arc = quadratic_bezier(cup_l, cup_bot, cup_r, n=40)
        paths.append(DrawPath(
            coords=cup_arc,
            color=acc,
            stroke_width=lw * 1.5,
            glow_intensity=gi * 1.0,
            layer_order=39,
            phase=5,
            phase_start=0.0,
        ))

        # Sepals arching outward
        sepal_angles = [math.radians(160), math.radians(135), math.radians(45), math.radians(20)]
        for s_ang in sepal_angles:
            s_len = R * rng.uniform(0.48, 0.70)
            s_base = np.array([calyx_cx + rng.uniform(-6, 6), calyx_cy + calyx_cup_h * 0.3])
            s_tip = s_base + s_len * np.array([math.cos(s_ang), math.sin(s_ang)])
            s_c1 = s_base + s_len * 0.4 * np.array([math.cos(s_ang), math.sin(s_ang) * 0.5])
            s_c2 = s_tip - s_len * 0.3 * np.array([math.cos(s_ang), -0.2])
            sepal_line = cubic_bezier(s_base, s_c1, s_c2, s_tip, n=50)
            paths.append(DrawPath(
                coords=sepal_line,
                color=acc,
                stroke_width=lw * 1.2,
                glow_intensity=gi * 0.85,
                layer_order=38,
                phase=5,
                phase_start=0.02,
            ))

        # Stem (originates at base of calyx)
        stem_top = np.array([calyx_cx, calyx_cy + calyx_cup_h])
        stem_bottom = np.array([cx + rng.uniform(-16, 16), cfg.canvas_h * 0.94])
        stem_h = stem_bottom[1] - stem_top[1]

        curve_dir = 1 if rng.random() > 0.5 else -1
        ctrl1 = np.array([calyx_cx + cfg.stem_curvature * R * 1.6 * curve_dir,
                          stem_top[1] + stem_h * 0.35])
        ctrl2 = np.array([calyx_cx - cfg.stem_curvature * R * 1.2 * curve_dir,
                          stem_top[1] + stem_h * 0.72])

        stem_pts = cubic_bezier(stem_top, ctrl1, ctrl2, stem_bottom, n=240)
        paths.append(DrawPath(
            coords=stem_pts,
            color=acc,
            stroke_width=lw * 2.0,
            glow_intensity=gi * 1.1,
            layer_order=5,
            phase=5,
            phase_start=0.05,
        ))

        # Parallel stem highlight lines
        for off in [-2.5, 2.5]:
            off_pts = stem_pts + np.array([off, 0])
            paths.append(DrawPath(
                coords=off_pts,
                color=sec,
                stroke_width=lw * 0.6,
                glow_intensity=gi * 0.6,
                layer_order=6,
                phase=5,
                phase_start=0.1,
            ))

        # Thorns
        thorn_fractions = [0.22, 0.44, 0.68, 0.82]
        thorn_sides = [curve_dir, -curve_dir, curve_dir, -curve_dir]
        for frac, side in zip(thorn_fractions, thorn_sides):
            idx = int(frac * (len(stem_pts) - 1))
            t_base = stem_pts[idx]
            t_tip = t_base + np.array([side * R * 0.12, R * 0.05])
            t_c1 = t_base + np.array([side * R * 0.03, -R * 0.02])
            t_c2 = t_tip - np.array([side * R * 0.02, R * 0.03])
            thorn_pts = cubic_bezier(t_base, t_c1, t_c2, t_tip, n=30)
            paths.append(DrawPath(
                coords=thorn_pts,
                color=pri,
                stroke_width=lw * 1.0,
                glow_intensity=gi * 0.8,
                layer_order=7,
                phase=5,
                phase_start=frac,
            ))

        # ===================================================================
        # Phase 6: Botanical Leaves
        # ===================================================================
        if cfg.n_leaves > 0:
            leaf_fracs = [0.28, 0.52, 0.74, 0.88][:cfg.n_leaves]
            leaf_sides = [-curve_dir, curve_dir, -curve_dir, curve_dir][:cfg.n_leaves]

            for frac, side in zip(leaf_fracs, leaf_sides):
                idx = int(frac * (len(stem_pts) - 1))
                attach = stem_pts[idx]

                # Leaf petiole
                petiole_len = R * 0.38
                petiole_angle = (math.radians(25) if side > 0 else math.radians(155)) + rng.uniform(-0.08, 0.08)
                p_leaf_base = attach + petiole_len * np.array([math.cos(petiole_angle), math.sin(petiole_angle)])
                petiole_pts = np.linspace(attach, p_leaf_base, 30)
                paths.append(DrawPath(
                    coords=petiole_pts,
                    color=acc,
                    stroke_width=lw * 1.2,
                    glow_intensity=gi * 0.8,
                    layer_order=8,
                    phase=6,
                    phase_start=frac,
                ))

                # Leaf blade
                leaf_len = R * rng.uniform(0.72, 0.92)
                leaf_w = leaf_len * rng.uniform(0.50, 0.65)
                leaf_angle = petiole_angle + side * rng.uniform(-0.12, 0.12)
                blade_pts = self._build_rose_leaflet(p_leaf_base, leaf_angle, leaf_len, leaf_w)
                paths.append(DrawPath(
                    coords=blade_pts,
                    color=pri,
                    stroke_width=lw * 1.3,
                    glow_intensity=gi * 1.0,
                    layer_order=9,
                    phase=6,
                    phase_start=frac + 0.04,
                ))

                # Midrib
                midrib_tip = p_leaf_base + leaf_len * np.array([math.cos(leaf_angle), math.sin(leaf_angle)])
                midrib = np.linspace(p_leaf_base, midrib_tip, 60)
                paths.append(DrawPath(
                    coords=midrib,
                    color=sec,
                    stroke_width=lw * 0.8,
                    glow_intensity=gi * 0.8,
                    layer_order=10,
                    phase=6,
                    phase_start=frac + 0.08,
                ))

                # Pinnate veins
                n_veins = 5
                for vi in range(1, n_veins):
                    t_v = vi / n_veins
                    v_start = p_leaf_base + t_v * (midrib_tip - p_leaf_base)
                    cur_w = leaf_w * math.sin(t_v * math.pi) * 0.45
                    for v_side in [-1, 1]:
                        v_ang = leaf_angle + v_side * math.radians(52)
                        v_end = v_start + cur_w * np.array([math.cos(v_ang), math.sin(v_ang)])
                        v_c = (v_start + v_end) / 2 + 5 * np.array([math.cos(leaf_angle), math.sin(leaf_angle)])
                        vein_line = quadratic_bezier(v_start, v_c, v_end, n=25)
                        paths.append(DrawPath(
                            coords=vein_line,
                            color=acc,
                            stroke_width=lw * 0.5,
                            glow_intensity=gi * 0.5,
                            layer_order=11,
                            phase=6,
                            phase_start=frac + 0.08 + vi * 0.02,
                        ))

        # ===================================================================
        # Phase 7: Floating Neon Sparkles
        # ===================================================================
        if cfg.show_particles:
            n_sparkles = 16 + cfg.detail_level * 3
            for _ in range(n_sparkles):
                s_ang = rng.uniform(0, 2 * math.pi)
                s_dist = R * rng.uniform(0.9, 2.1)
                px = cx + s_dist * math.cos(s_ang)
                py = cy + s_dist * math.sin(s_ang) * 1.15
                sz = rng.uniform(2.5, 7.0)

                sparkle_pts = []
                for rot in [0, math.pi / 2]:
                    p1 = [px + sz * math.cos(rot), py + sz * math.sin(rot)]
                    p2 = [px - sz * math.cos(rot), py - sz * math.sin(rot)]
                    sparkle_pts.append(np.array([p1, p2]))

                s_col = rng.choice([C_WHITE_PINK, pri, sec, acc])
                for seg in sparkle_pts:
                    paths.append(DrawPath(
                        coords=seg,
                        color=s_col,
                        stroke_width=lw * 0.75,
                        glow_intensity=gi * 1.3,
                        layer_order=50,
                        phase=7,
                        phase_start=rng.uniform(0.0, 0.8),
                    ))

        # ===================================================================
        # Phase 8: Outer Glow Ring
        # ===================================================================
        for r_f, col, w in [(1.08, acc, 0.7), (1.14, pri, 0.4), (1.20, C_DEEP_VIOLET, 0.3)]:
            th = np.linspace(0, 2 * math.pi, 200)
            ring_pts = np.stack([cx + R * r_f * np.cos(th),
                                 cy + R * r_f * np.sin(th) * 0.95], axis=1)
            paths.append(DrawPath(
                coords=ring_pts,
                color=col,
                stroke_width=lw * w,
                glow_intensity=gi * 0.6,
                layer_order=60,
                phase=8,
                phase_start=0.0,
            ))

        geo.paths = paths
        return geo

    # -----------------------------------------------------------------------
    # Petal & Leaf Geometry Helpers
    # -----------------------------------------------------------------------
    def _build_curved_petal(self, base_pt, angle, length, width, curl=0.2, roundness=1.0):
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        u_ax = np.array([cos_a, sin_a])
        u_perp = np.array([-sin_a, cos_a])

        p_base = np.array(base_pt)
        half_w = width * 0.5 * roundness

        p_sl = p_base + u_ax * (length * 0.58) - u_perp * half_w
        p_sr = p_base + u_ax * (length * 0.58) + u_perp * half_w
        p_tip = p_base + u_ax * length

        c1_l = p_base + u_ax * (length * 0.22) - u_perp * (half_w * 0.8)
        c2_l = p_sl - u_ax * (length * 0.15) - u_perp * (half_w * 0.15)

        c1_tl = p_sl + u_ax * (length * 0.28) + u_perp * (half_w * 0.1)
        c2_tl = p_tip - u_ax * (length * 0.08) - u_perp * (half_w * 0.25 * curl)

        c1_tr = p_tip - u_ax * (length * 0.08) + u_perp * (half_w * 0.25 * curl)
        c2_tr = p_sr + u_ax * (length * 0.28) - u_perp * (half_w * 0.1)

        c1_r = p_sr - u_ax * (length * 0.15) + u_perp * (half_w * 0.15)
        c2_r = p_base + u_ax * (length * 0.22) + u_perp * (half_w * 0.8)

        n_pts = 160
        l_pts = cubic_bezier(p_base, c1_l, c2_l, p_sl, n=n_pts//4)
        tl_pts = cubic_bezier(p_sl, c1_tl, c2_tl, p_tip, n=n_pts//4)
        tr_pts = cubic_bezier(p_tip, c1_tr, c2_tr, p_sr, n=n_pts//4)
        r_pts = cubic_bezier(p_sr, c1_r, c2_r, p_base, n=n_pts//4)

        return np.vstack([l_pts, tl_pts, tr_pts, r_pts])

    def _build_curved_striation(self, base_pt, angle, length, offset_frac, width):
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        u_ax = np.array([cos_a, sin_a])
        u_perp = np.array([-sin_a, cos_a])

        p0 = np.array(base_pt) + u_perp * (width * 0.1 * offset_frac)
        p3 = p0 + u_ax * length + u_perp * (width * 0.45 * offset_frac)

        p1 = p0 + u_ax * (length * 0.35) + u_perp * (width * 0.15 * offset_frac)
        p2 = p0 + u_ax * (length * 0.70) + u_perp * (width * 0.32 * offset_frac)
        return cubic_bezier(p0, p1, p2, p3, n=35)

    def _build_rose_leaflet(self, base_pt, angle, length, width):
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        u_ax = np.array([cos_a, sin_a])
        u_perp = np.array([-sin_a, cos_a])

        p0 = np.array(base_pt)
        tip = p0 + u_ax * length
        half_w = width * 0.5

        p_sl = p0 + u_ax * (length * 0.38) - u_perp * half_w
        p_sr = p0 + u_ax * (length * 0.38) + u_perp * half_w

        c1_l = p0 + u_ax * (length * 0.15) - u_perp * (half_w * 0.6)
        c2_l = p_sl - u_ax * (length * 0.08)

        c1_tl = p_sl + u_ax * (length * 0.28)
        c2_tl = tip - u_ax * (length * 0.22) - u_perp * (half_w * 0.1)

        c1_tr = tip - u_ax * (length * 0.22) + u_perp * (half_w * 0.1)
        c2_tr = p_sr + u_ax * (length * 0.28)

        c1_r = p_sr - u_ax * (length * 0.08)
        c2_r = p0 + u_ax * (length * 0.15) + u_perp * (half_w * 0.6)

        n_pts = 120
        p_left1 = cubic_bezier(p0, c1_l, c2_l, p_sl, n=n_pts//4)
        p_left2 = cubic_bezier(p_sl, c1_tl, c2_tl, tip, n=n_pts//4)
        p_right1 = cubic_bezier(tip, c1_tr, c2_tr, p_sr, n=n_pts//4)
        p_right2 = cubic_bezier(p_sr, c1_r, c2_r, p0, n=n_pts//4)

        return np.vstack([p_left1, p_left2, p_right1, p_right2])
