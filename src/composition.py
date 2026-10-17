"""
composition.py
==============
High-level composition helpers:
- build_rose_image()      – full rose PNG at target resolution
- build_split_image()     – left:rose + right:code-panel composition
- build_preview_image()   – fast preview rendering
- CODE_SNIPPETS            – actual code excerpts from this project
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

from .path_geometry import RoseGeometry
from .neon_renderer import (
    render_frame, add_quote_overlay, render_code_panel, CODE_SNIPPETS
)
from .video_exporter import _fit_on_canvas


# ---------------------------------------------------------------------------
# Actual Project Code Snippets (displayed in Code Panel mode)
# ---------------------------------------------------------------------------
_SNIPPET_PETALS = '''\
def _build_curved_petal(self, base_pt, angle, length, width, curl=0.2):
    """
    Parametric botanical rose petal outline:
    two cubic Bézier curves per flank with cupped shoulders
    and reflexed wavy apex rim.
    """
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    u_ax = np.array([cos_a, sin_a])
    u_perp = np.array([-sin_a, cos_a])
    
    p_base = np.array(base_pt)
    half_w = width * 0.5
    
    # Left & Right shoulders (broadest cupping)
    p_sl = p_base + u_ax * (length * 0.58) - u_perp * half_w
    p_sr = p_base + u_ax * (length * 0.58) + u_perp * half_w
    p_tip = p_base + u_ax * length
    
    l_pts  = cubic_bezier(p_base, c1_l, c2_l, p_sl, n=40)
    tl_pts = cubic_bezier(p_sl, c1_tl, c2_tl, p_tip, n=40)
    tr_pts = cubic_bezier(p_tip, c1_tr, c2_tr, p_sr, n=40)
    r_pts  = cubic_bezier(p_sr, c1_r, c2_r, p_base, n=40)
    return np.vstack([l_pts, tl_pts, tr_pts, r_pts])
'''

_SNIPPET_GEOMETRY = '''\
class RoseGenerator:
    """
    Deterministic botanical rose geometry engine.
    Seeds produce unique, reproducible blooms.
    """
    def generate(self) -> RoseGeometry:
        # Phase 1: Core logarithmic spiral whorl
        theta = np.linspace(0.4, 5.8 * math.pi, 260)
        r_spiral = (R * 0.010) * (theta ** 1.38)
        whorl = np.stack([cx + r_spiral * np.cos(theta),
                          cy + r_spiral * np.sin(theta)*0.88], axis=1)
        
        # Golden ratio phyllotaxis distribution
        golden_angle = 2.3999632  # ~137.5 deg
        for i in range(self.cfg.n_middle):
            ang = (i * golden_angle) + rng.uniform(-0.1, 0.1)
            dist = R * rng.uniform(0.22, 0.36)
            base = [cx + dist * cos(ang), cy + dist * sin(ang)*0.86]
            paths.append(self._build_curved_petal(base, ang, ...))
        return geo
'''

_SNIPPET_LEAVES = '''\
def _build_rose_leaflet(self, base_pt, angle, length, width):
    """
    Botanical rose leaflet: ovate, acuminate tip,
    central midrib and arching lateral pinnate veins.
    """
    # Petiole attachment to stem
    p_leaf_base = attach + petiole_len * np.array([cos(pet_ang), sin(pet_ang)])
    blade_pts = cubic_bezier(p_leaf_base, ..., tip, n=120)
    
    # Secondary lateral pinnate veins
    for vi in range(1, n_veins):
        t_v = vi / n_veins
        v_start = p_leaf_base + t_v * (midrib_tip - p_leaf_base)
        cur_w = leaf_w * math.sin(t_v * math.pi) * 0.45
        v_end = v_start + cur_w * np.array([cos(v_ang), sin(v_ang)])
        yield quadratic_bezier(v_start, v_c, v_end, n=25)
'''

_SNIPPET_GLOW = '''\
def render_frame(geometry, fraction_map=None, glow_intensity=1.0, supersampling=2):
    """
    Multi-layer neon glow composite pipeline:
    1. Layer 1: Wide diffuse bloom (large Gaussian blur, rich aura)
    2. Layer 2: Medium aura (medium blur, higher saturation)
    3. Layer 3: Tight inner glow (small blur)
    4. Layer 4: Brilliant white-hot core lines (antialiased crisp art)
    """
    bloom = bloom_img.filter(ImageFilter.GaussianBlur(radius=rW * 0.016 * gi))
    aura  = aura_img.filter(ImageFilter.GaussianBlur(radius=rW * 0.007 * gi))
    inner = inner_img.filter(ImageFilter.GaussianBlur(radius=rW * 0.0025 * gi))
    
    canvas = Image.new("RGBA", (rW, rH), (0, 0, 0, 255))
    for layer in [bloom, aura, inner, core]:
        canvas = Image.alpha_composite(canvas, layer)
    return canvas.resize((W, H), Image.LANCZOS).convert("RGB")
'''

_SNIPPET_ANIMATION = '''\
def compute_fraction_map(geometry: RoseGeometry, global_t: float) -> dict:
    """
    Interpolates each curve stroke progressively along its path.
    Phases:
      1: Center core light appears
      2: Inner petals draw themselves
      3: Medium petals unfurl
      4: Outer petals bloom
      5: Stem & thorns extend downward
      6: Leaves & pinnate veins draw
      7: Sparkles fade in
      8: Neon aura reaches peak glow
    """
    fmap = {}
    for i, path in enumerate(geometry.paths):
        p0, p1 = PHASE_RANGES[path.phase]
        path_local = (global_t - p0) / (p1 - p0 + 1e-9)
        fmap[i] = ease_in_out(np.clip(path_local, 0.0, 1.0))
    return fmap
'''

CODE_SNIPPETS.update({
    "Generate petal curves":   _SNIPPET_PETALS,
    "Calculate rose geometry": _SNIPPET_GEOMETRY,
    "Generate leaves":         _SNIPPET_LEAVES,
    "Apply neon glow":         _SNIPPET_GLOW,
    "Render the animation":    _SNIPPET_ANIMATION,
})


# ---------------------------------------------------------------------------
# Composition Builders
# ---------------------------------------------------------------------------
def build_rose_image(
    geometry: RoseGeometry,
    glow_intensity: float = 1.0,
    supersampling: int = 2,
    quote: Optional[str] = None,
    quote_position: str = "bottom",
) -> Image.Image:
    """Render full high-resolution glowing rose."""
    img = render_frame(geometry, fraction_map=None,
                       glow_intensity=glow_intensity,
                       supersampling=supersampling)
    if quote and quote.strip():
        img = add_quote_overlay(img, quote, position=quote_position)
    return img


def build_split_image(
    geometry: RoseGeometry,
    code_snippet: str = "Generate petal curves",
    glow_intensity: float = 1.0,
    supersampling: int = 2,
    quote: Optional[str] = None,
) -> Image.Image:
    """
    Build side-by-side split screen:
      Left half:  Glowing Rose Art
      Right half: Dark Syntax-Highlighted Code Editor Panel
    """
    rose_img = build_rose_image(geometry, glow_intensity,
                                supersampling=supersampling, quote=quote)
    W, H = rose_img.size
    half_w = W // 2

    rose_half = _fit_on_canvas(rose_img, half_w, H)
    snippet = CODE_SNIPPETS.get(code_snippet, _SNIPPET_PETALS)
    code_panel = render_code_panel(snippet, half_w, H, font_size=max(14, H // 82))

    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    canvas.paste(rose_half, (0, 0))
    canvas.paste(code_panel, (half_w, 0))
    return canvas


def build_preview_image(
    geometry: RoseGeometry,
    max_size: int = 600,
    glow_intensity: float = 1.0,
) -> Image.Image:
    """Fast preview rendering by downscaling path coordinates."""
    W = int(geometry.canvas_w)
    H = int(geometry.canvas_h)
    scale = max_size / max(W, H)
    if scale >= 1.0:
        scale = 1.0

    preview_geo = deepcopy(geometry)
    preview_geo.canvas_w = W * scale
    preview_geo.canvas_h = H * scale
    preview_geo.center_x *= scale
    preview_geo.center_y *= scale
    preview_geo.rose_radius *= scale
    for path in preview_geo.paths:
        path.coords = path.coords * scale
        path.stroke_width *= scale

    return render_frame(preview_geo, fraction_map=None,
                        glow_intensity=glow_intensity,
                        supersampling=1)
