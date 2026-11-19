"""
app.py — NEON ROSE
Pure cinematic neon rose generative art.
Draws the rose immediately upon opening with zero clutter or options.
"""

from __future__ import annotations

import json
from pathlib import Path
import streamlit as st
from src.rose_generator import RoseConfig, RoseGenerator

# --------------------------------------------------------------------------
# Page Configuration: Centered, clean, no sidebar
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Neon Rose",
    page_icon="🌹",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------------------------------------------------------------------
# Clean Pure Black Cinematic Styling: Hide all Streamlit UI clutter
# --------------------------------------------------------------------------
st.markdown("""
<style>
  /* Remove all default Streamlit margins, headers, menus, and sidebars */
  #MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {
    visibility: hidden !important;
    display: none !important;
  }
  
  [data-testid="stSidebar"] {
    display: none !important;
  }
  
  [data-testid="stHeader"] {
    background: transparent !important;
    display: none !important;
  }

  /* Full screen pure black */
  html, body, .stApp {
    background-color: #000000 !important;
    color: #ffffff !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    width: 100vw !important;
    height: 100vh !important;
  }

  .block-container {
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100vw !important;
    height: 100vh !important;
  }
  
  iframe {
    border: none !important;
    width: 100vw !important;
    height: 100vh !important;
    overflow: hidden !important;
    display: block !important;
  }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Generate Rose Paths
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def get_rose_paths_json(seed=42):
    cfg = RoseConfig(
        seed=seed,
        canvas_w=1080,
        canvas_h=1920,
        n_inner=6,
        n_middle=9,
        n_outer=13,
        stem_curvature=0.35,
        n_leaves=3,
        line_thickness=1.5,
        detail_level=3,
        primary_color="#FF4FD8",
        secondary_color="#FFB5F2",
        accent_color="#A855F7",
        glow_intensity=1.2,
        show_particles=True,
    )
    geo = RoseGenerator(cfg).generate()

    serializable = []
    for p in geo.paths:
        serializable.append({
            "coords": [[round(float(pt[0]), 2), round(float(pt[1]), 2)] for pt in p.coords],
            "color": p.color,
            "width": round(float(p.stroke_width), 2),
            "glow": round(float(p.glow_intensity), 2),
            "phase": int(p.phase),
            "phase_start": round(float(p.phase_start), 3),
        })
    return json.dumps(serializable)


paths_json = get_rose_paths_json(seed=42)

# --------------------------------------------------------------------------
# HTML5 Canvas Animation: Draws stroke-by-stroke in 60 FPS neon light
# --------------------------------------------------------------------------
canvas_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    user-select: none;
    -webkit-user-select: none;
  }}
  html, body {{
    width: 100%;
    height: 100%;
    background-color: #000000;
    overflow: hidden;
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
  }}
  canvas {{
    display: block;
    max-width: 100vw;
    max-height: 100vh;
    aspect-ratio: 9 / 16;
    background-color: #000000;
  }}

  /* Romantic title placed above the rose */
  .dedication {{
    position: fixed;
    z-index: 2;
    top: 5.5%;
    left: 5%;
    width: 90%;
    text-align: center;
    pointer-events: none;
    animation: appear 2s ease both;
  }}

  .dedication h1 {{
    color: #FFEAF8;
    font-family: Georgia, 'Times New Roman', serif;
    font-size: clamp(30px, 7vw, 58px);
    font-weight: 400;
    letter-spacing: 1.5px;
    line-height: 1.15;
    text-shadow: 0 0 8px #FF4FD8, 0 0 22px #D946EF, 0 0 42px #A855F7;
    margin: 0 0 12px 0;
  }}

  .dedication p {{
    color: #EBCDE5;
    font-family: Georgia, 'Times New Roman', serif;
    font-size: clamp(13px, 3.2vw, 19px);
    font-weight: 400;
    letter-spacing: 0.35px;
    line-height: 1.5;
    text-shadow: 0 0 10px rgba(255, 79, 216, 0.65);
    margin: 0 auto;
    max-width: 440px;
  }}

  .dedication .ornament {{
    width: 54px;
    height: 1px;
    margin: 18px auto 0;
    background: linear-gradient(90deg, transparent, #FF8BE3, transparent);
    box-shadow: 0 0 9px #FF4FD8;
  }}

  @keyframes appear {{
    from {{ opacity: 0; transform: translateY(-12px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}

  @media (max-height: 650px) {{
    .dedication {{ top: 3%; }}
    .dedication h1 {{ font-size: clamp(25px, 5vw, 40px); margin-bottom: 6px; }}
    .dedication p {{ font-size: 12px; }}
    .dedication .ornament {{ margin-top: 8px; }}
  }}
</style>
</head>
<body>
<div class="dedication">
  <h1>Un fiore per Camilla</h1>
  <p>Perché ci sono cose belle che meritano di brillare.</p>
  <div class="ornament"></div>
</div>
<canvas id="roseCanvas"></canvas>

<script>
  const paths = {paths_json};
  const canvas = document.getElementById('roseCanvas');
  const ctx = canvas.getContext('2d');

  const VIRTUAL_W = 1080;
  const VIRTUAL_H = 1920;

  function resize() {{
    const dpr = window.devicePixelRatio || 1;
    const winW = window.innerWidth;
    const winH = window.innerHeight;
    
    // Fit 9:16 within viewport
    let displayW = winW;
    let displayH = winW * (16 / 9);
    if (displayH > winH) {{
      displayH = winH;
      displayW = winH * (9 / 16);
    }}
    
    canvas.style.width = displayW + 'px';
    canvas.style.height = displayH + 'px';
    canvas.width = displayW * dpr;
    canvas.height = displayH * dpr;
    
    scale = (displayW * dpr) / VIRTUAL_W;
  }}

  let scale = 1;
  window.addEventListener('resize', resize);
  resize();

  // Phase timing (normalized 0 to 1)
  const PHASE_RANGES = {{
    1: [0.00, 0.05],  // Center core light
    2: [0.05, 0.28],  // Bud whorl & inner petals
    3: [0.28, 0.52],  // Middle cupped petals
    4: [0.52, 0.76],  // Outer blooming petals
    5: [0.76, 0.84],  // Calyx & stem extension
    6: [0.84, 0.94],  // Leaves & veins
    7: [0.94, 0.98],  // Sparkles
    8: [0.98, 1.00]   // Outer aura glow
  }};

  function easeInOut(t) {{
    t = Math.max(0, Math.min(1, t));
    return t * t * (3 - 2 * t);
  }}

  let startTime = null;
  const DRAW_DURATION = 9000; // 9 seconds drawing animation
  let animationFrameId;

  function startAnimation() {{
    startTime = performance.now();
    requestAnimationFrame(render);
  }}

  function render(now) {{
    const elapsed = now - startTime;
    const globalT = Math.min(1.0, elapsed / DRAW_DURATION);

    ctx.save();
    ctx.scale(scale, scale);

    // Pure black clear
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, VIRTUAL_W, VIRTUAL_H);

    // Subtle gentle breathing pulse after drawing completes
    let pulse = 1.0;
    if (globalT >= 1.0) {{
      const holdTime = (elapsed - DRAW_DURATION) / 1000;
      pulse = 1.0 + 0.08 * Math.sin(holdTime * 2.0);
    }}

    // Draw all paths up to current progress
    for (let i = 0; i < paths.length; i++) {{
      const p = paths[i];
      const range = PHASE_RANGES[p.phase] || [0, 1];
      const pStart = range[0] + (p.phase_start || 0) * (range[1] - range[0]);
      const pEnd = range[1];

      if (globalT < pStart) continue;

      let frac = (globalT - pStart) / Math.max(0.001, (pEnd - pStart));
      frac = easeInOut(Math.min(1.0, Math.max(0.0, frac)));

      const pts = p.coords;
      const count = Math.max(2, Math.floor(pts.length * frac));
      if (count < 2) continue;

      const pathColor = p.color;
      const baseW = p.width * pulse;
      const glowMul = p.glow * pulse;

      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      for (let j = 1; j < count; j++) {{
        ctx.lineTo(pts[j][0], pts[j][1]);
      }}

      // Layer 1: Wide outer neon aura bloom
      ctx.save();
      ctx.shadowColor = pathColor;
      ctx.shadowBlur = 24 * glowMul;
      ctx.strokeStyle = pathColor;
      ctx.lineWidth = baseW * 3.6;
      ctx.globalAlpha = 0.45;
      ctx.stroke();
      ctx.restore();

      // Layer 2: Medium vibrant glow
      ctx.save();
      ctx.shadowColor = pathColor;
      ctx.shadowBlur = 10 * glowMul;
      ctx.strokeStyle = pathColor;
      ctx.lineWidth = baseW * 1.6;
      ctx.globalAlpha = 0.85;
      ctx.stroke();
      ctx.restore();

      // Layer 3: Brilliant white-hot core line
      ctx.save();
      ctx.shadowColor = '#FFFFFF';
      ctx.shadowBlur = 4;
      ctx.strokeStyle = '#FFF5FB';
      ctx.lineWidth = Math.max(1, baseW * 0.7);
      ctx.globalAlpha = 1.0;
      ctx.stroke();
      ctx.restore();

      // Glowing pen tip leading the stroke while drawing
      if (frac > 0.01 && frac < 0.99) {{
        const tip = pts[count - 1];
        ctx.save();
        ctx.shadowColor = '#FFFFFF';
        ctx.shadowBlur = 16;
        ctx.fillStyle = '#FFFFFF';
        ctx.beginPath();
        ctx.arc(tip[0], tip[1], baseW * 1.8, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }}
    }}

    ctx.restore();
    animationFrameId = requestAnimationFrame(render);
  }}

  // Click anywhere to redraw
  document.body.addEventListener('click', () => {{
    startAnimation();
  }});

  // Keyboard shortcut Space / R to replay
  window.addEventListener('keydown', (e) => {{
    if (e.code === 'Space' || e.key === 'r' || e.key === 'R') {{
      startAnimation();
    }}
  }});

  startAnimation();
</script>
</body>
</html>
"""

st.components.v1.html(canvas_html, height=1000, scrolling=False)
