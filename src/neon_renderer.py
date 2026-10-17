"""
neon_renderer.py
================
Converts a RoseGeometry object (list of DrawPaths) into a PIL Image
with a proper multi-layer neon glow effect:

  Layer 0 – Pure black background (#000000)
  Layer 1 – Wide outer bloom (large Gaussian blur, rich saturated neon aura)
  Layer 2 – Medium aura (medium blur, higher opacity)
  Layer 3 – Tight inner neon glow (small blur)
  Layer 4 – White-hot luminous core line art (sharp lines with high-value core)

Also supports:
- Text quote overlay with elegant typography
- Syntax-highlighted code editor side-panel
"""

from __future__ import annotations

import math
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .path_geometry import DrawPath, RoseGeometry, partial_path


# ---------------------------------------------------------------------------
# Colour utilities
# ---------------------------------------------------------------------------
def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def hex_to_rgba(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    r, g, b = hex_to_rgb(hex_color)
    return (r, g, b, alpha)


# ---------------------------------------------------------------------------
# Path Drawing Helper
# ---------------------------------------------------------------------------
def _draw_path_on(
    draw: ImageDraw.ImageDraw,
    path: DrawPath,
    color_override: Optional[Tuple[int, int, int, int]] = None,
    width_scale: float = 1.0,
):
    pts = path.coords
    if len(pts) < 2:
        return
    xy = [(float(p[0]), float(p[1])) for p in pts]
    col = color_override if color_override is not None else hex_to_rgba(path.color, int(255 * path.alpha))
    lw = max(1, int(round(path.stroke_width * width_scale)))
    draw.line(xy, fill=col, width=lw, joint="curve")


# ---------------------------------------------------------------------------
# Multi-Layer Neon Render Pipeline
# ---------------------------------------------------------------------------
def render_frame(
    geometry: RoseGeometry,
    fraction_map: Optional[Dict[int, float]] = None,
    glow_intensity: float = 1.0,
    supersampling: int = 2,
) -> Image.Image:
    """
    Render one frame of the rose at the geometry's canvas size.

    *fraction_map*: dict mapping path index -> [0, 1] draw fraction for progressive reveal.
    *supersampling*: 1 (fast preview), 2 (standard crisp), 3 or 4 (ultra high-res).
    """
    W = int(geometry.canvas_w)
    H = int(geometry.canvas_h)
    SS = max(1, min(int(supersampling), 4))
    rW, rH = W * SS, H * SS

    # Glow multiplier
    gi = max(0.1, float(glow_intensity))

    # Four distinct rendering passes
    bloom_img = Image.new("RGBA", (rW, rH), (0, 0, 0, 0))
    bloom_draw = ImageDraw.Draw(bloom_img)

    aura_img = Image.new("RGBA", (rW, rH), (0, 0, 0, 0))
    aura_draw = ImageDraw.Draw(aura_img)

    inner_img = Image.new("RGBA", (rW, rH), (0, 0, 0, 0))
    inner_draw = ImageDraw.Draw(inner_img)

    core_img = Image.new("RGBA", (rW, rH), (0, 0, 0, 0))
    core_draw = ImageDraw.Draw(core_img)

    for i, path in enumerate(geometry.paths):
        # Determine stroke fraction
        frac = fraction_map.get(i, 1.0) if fraction_map is not None else 1.0
        if frac <= 0.001:
            continue

        raw_pts = path.coords
        if frac < 0.999:
            pts = partial_path(raw_pts, frac)
        else:
            pts = raw_pts

        if len(pts) < 2:
            continue

        # Scale coordinates for supersampling
        scaled_pts = pts * SS
        scaled_path = DrawPath(
            coords=scaled_pts,
            color=path.color,
            stroke_width=path.stroke_width * SS,
            glow_intensity=path.glow_intensity,
            alpha=path.alpha,
        )

        r, g, b = hex_to_rgb(path.color)
        w = scaled_path.stroke_width
        path_gi = path.glow_intensity * gi

        # 1. Wide diffuse bloom
        bloom_alpha = int(min(255, 65 * path_gi * path.alpha))
        if bloom_alpha > 0:
            _draw_path_on(bloom_draw, scaled_path,
                          color_override=(r, g, b, bloom_alpha),
                          width_scale=8.0)

        # 2. Medium aura
        aura_alpha = int(min(255, 115 * path_gi * path.alpha))
        if aura_alpha > 0:
            _draw_path_on(aura_draw, scaled_path,
                          color_override=(r, g, b, aura_alpha),
                          width_scale=3.8)

        # 3. Inner saturated glow
        inner_alpha = int(min(255, 185 * path_gi * path.alpha))
        if inner_alpha > 0:
            _draw_path_on(inner_draw, scaled_path,
                          color_override=(r, g, b, inner_alpha),
                          width_scale=1.8)

        # 4. Crisp hot core (blend toward brilliant white)
        core_r = min(255, int(r * 0.35 + 255 * 0.65))
        core_g = min(255, int(g * 0.35 + 255 * 0.65))
        core_b = min(255, int(b * 0.35 + 255 * 0.65))
        core_alpha = int(min(255, 255 * path.alpha))
        _draw_path_on(core_draw, scaled_path,
                      color_override=(core_r, core_g, core_b, core_alpha),
                      width_scale=0.85)

    # Apply Gaussian blurs
    if gi > 0:
        bloom_img = bloom_img.filter(ImageFilter.GaussianBlur(radius=rW * 0.016 * min(gi, 1.5)))
        aura_img = aura_img.filter(ImageFilter.GaussianBlur(radius=rW * 0.007 * min(gi, 1.5)))
        inner_img = inner_img.filter(ImageFilter.GaussianBlur(radius=rW * 0.0025 * min(gi, 1.5)))

    # Composite onto pure cinematic black canvas
    canvas = Image.new("RGBA", (rW, rH), (0, 0, 0, 255))
    canvas = Image.alpha_composite(canvas, bloom_img)
    canvas = Image.alpha_composite(canvas, aura_img)
    canvas = Image.alpha_composite(canvas, inner_img)
    canvas = Image.alpha_composite(canvas, core_img)

    # Downscale for crisp antialiasing
    if SS > 1:
        canvas = canvas.resize((W, H), Image.LANCZOS)

    return canvas.convert("RGB")


# ---------------------------------------------------------------------------
# Quote Overlay
# ---------------------------------------------------------------------------
def add_quote_overlay(
    image: Image.Image,
    quote: str,
    position: str = "bottom",
    font_size: Optional[int] = None,
    color: Tuple[int, int, int] = (255, 235, 250),
    margin_frac: float = 0.07,
) -> Image.Image:
    """Render an elegant text quote centered at top or bottom."""
    if not quote or not quote.strip():
        return image

    img = image.convert("RGBA")
    W, H = img.size
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    if font_size is None:
        font_size = max(24, int(H * 0.024))

    font = _load_font(font_size, monospace=False)
    clean_quote = f'"{quote.strip()}"'
    lines = textwrap.wrap(clean_quote, width=32)
    line_h = font_size + 10
    total_h = line_h * len(lines)
    margin = int(H * margin_frac)

    start_y = margin if position == "top" else H - margin - total_h

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        y = start_y + i * line_h

        # Soft glowing text shadow
        for sx, sy in [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]:
            draw.text((x + sx, y + sy), line, font=font, fill=(255, 79, 216, 60))
        # Crisp text
        draw.text((x, y), line, font=font, fill=(*color, 230))

    return Image.alpha_composite(img, overlay).convert("RGB")


# ---------------------------------------------------------------------------
# Syntax-Highlighted Code Editor Panel
# ---------------------------------------------------------------------------
CODE_SNIPPETS: Dict[str, str] = {}

SYNTAX_COLORS = {
    "comment": (90, 210, 130),       # Vibrant emerald green
    "keyword": (255, 79, 216),       # Neon pink
    "string":  (255, 181, 242),      # Soft pastel pink
    "number":  (168, 85, 247),       # Electric purple
    "default": (230, 235, 245),      # Light crisp white
    "builtin": (100, 220, 255),      # Cyan
}


def _tokenize_line(line: str):
    import re
    tokens = []
    keywords = {"def", "class", "return", "import", "from", "for", "in",
                "if", "else", "elif", "while", "with", "as", "True", "False",
                "None", "and", "or", "not", "lambda", "yield", "np", "math"}
    builtins = {"range", "len", "int", "float", "str", "list", "dict",
                "print", "zip", "enumerate", "min", "max", "abs", "round"}

    stripped = line.lstrip()
    if stripped.startswith("#"):
        tokens.append(("comment", line))
        return tokens

    pattern = re.compile(
        r'(""".*?"""|\'\'\'.*?\'\'\'|".*?"|\'.*?\')'
        r'|(\b(?:' + "|".join(re.escape(k) for k in keywords) + r')\b)'
        r'|(\b(?:' + "|".join(re.escape(b) for b in builtins) + r')\b)'
        r'|(\b\d+\.?\d*\b)'
        r'|([\w_]+)'
        r'|(.)'
    )
    for m in pattern.finditer(line):
        s, kw, bi, num, ident, other = m.groups()
        if s:       tokens.append(("string",  s))
        elif kw:    tokens.append(("keyword", kw))
        elif bi:    tokens.append(("builtin", bi))
        elif num:   tokens.append(("number",  num))
        elif ident: tokens.append(("default", ident))
        elif other: tokens.append(("default", other))
    return tokens


def render_code_panel(
    code: str,
    width: int,
    height: int,
    font_size: int = 20,
    bg_color: Tuple[int, int, int] = (10, 6, 18),
) -> Image.Image:
    """Render syntax-highlighted code inside a clean dark code editor panel."""
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    font = _load_font(font_size, monospace=True)

    # Editor titlebar
    bar_h = 36
    draw.rectangle([(0, 0), (width, bar_h)], fill=(18, 12, 30))
    # Window controls (macOS / editor dots)
    for dot_x, dot_col in [(18, (255, 95, 87)), (36, (254, 188, 46)), (54, (40, 200, 64))]:
        draw.ellipse([(dot_x, 12), (dot_x + 10, 22)], fill=dot_col)

    draw.text((78, 10), "rose_generator.py", font=font, fill=(160, 140, 190))

    line_h = font_size + 6
    pad_x, pad_y = 20, bar_h + 18
    lines = code.split("\n")

    line_num_w = 42
    for i, line in enumerate(lines):
        y = pad_y + i * line_h
        if y > height - pad_y:
            break
        # Line number
        draw.text((pad_x, y), f"{i+1:2d}", font=font, fill=(75, 60, 100))
        # Syntax tokens
        x = pad_x + line_num_w
        tokens = _tokenize_line(line)
        for kind, text in tokens:
            col = SYNTAX_COLORS.get(kind, SYNTAX_COLORS["default"])
            draw.text((x, y), text, font=font, fill=col)
            bbox = draw.textbbox((0, 0), text, font=font)
            x += bbox[2] - bbox[0]

    return img


# ---------------------------------------------------------------------------
# Font Loader Helper
# ---------------------------------------------------------------------------
def _load_font(size: int, monospace: bool = False) -> ImageFont.FreeTypeFont:
    assets = Path(__file__).parent.parent / "assets" / "fonts"
    candidates = []
    if monospace:
        candidates = [
            assets / "JetBrainsMono-Regular.ttf",
            assets / "DejaVuSansMono.ttf",
            "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/cour.ttf",
        ]
    else:
        candidates = [
            assets / "Inter-Regular.ttf",
            assets / "Roboto-Regular.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]

    for path in candidates:
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            continue

    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()
