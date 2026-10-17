"""
video_exporter.py
=================
Exports a list of PIL Images (animation frames) to MP4 using moviepy,
with robust fallbacks to OpenCV and FFmpeg.
Handles Instagram Reels (1080x1920), 4K vertical (2160x3840),
Square (1080x1080), and Portrait (1080x1350) presets.
Also handles high-resolution static PNG exports.
"""

from __future__ import annotations

import gc
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Export presets
# ---------------------------------------------------------------------------
PRESETS = {
    "instagram_reel": {
        "width": 1080, "height": 1920, "fps": 30, "label": "Instagram Reel (1080×1920)",
    },
    "4k_vertical": {
        "width": 2160, "height": 3840, "fps": 30, "label": "High-Res 4K (2160×3840)",
    },
    "square_1080": {
        "width": 1080, "height": 1080, "fps": 30, "label": "Square (1080×1080)",
    },
    "portrait_1350": {
        "width": 1080, "height": 1350, "fps": 30, "label": "Portrait (1080×1350)",
    },
}


# ---------------------------------------------------------------------------
# PNG Export
# ---------------------------------------------------------------------------
def export_png(
    image: Image.Image,
    output_path: Path,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None,
) -> Path:
    """Save *image* as high-resolution PNG on pure black canvas."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if target_width and target_height:
        img = _fit_on_canvas(image, target_width, target_height)
    else:
        img = image

    img.convert("RGB").save(str(output_path), format="PNG", compress_level=4)
    return output_path


# ---------------------------------------------------------------------------
# MP4 Export
# ---------------------------------------------------------------------------
def export_mp4(
    frames: List[Image.Image],
    output_path: Path,
    fps: int = 30,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    quality: int = 8,
) -> Path:
    """
    Export sequence of PIL Images to an H.264 MP4 file.
    Tries MoviePy first; falls back to OpenCV; falls back to FFmpeg subprocess.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not frames:
        raise ValueError("Cannot export empty frame list to MP4")

    if target_width and target_height:
        frames = [_fit_on_canvas(f, target_width, target_height) for f in frames]

    W, H = frames[0].size

    # 1. MoviePy backend
    try:
        return _export_with_moviepy(frames, output_path, fps, progress_callback, quality)
    except Exception as e:
        print(f"[video_exporter] moviepy backend failed: {e}. Trying OpenCV backend...")

    # 2. OpenCV backend
    try:
        return _export_with_opencv(frames, output_path, fps, W, H, progress_callback)
    except Exception as e:
        print(f"[video_exporter] OpenCV backend failed: {e}. Trying FFmpeg backend...")

    # 3. FFmpeg subprocess backend
    return _export_with_ffmpeg(frames, output_path, fps, progress_callback)


# ---------------------------------------------------------------------------
# MoviePy Implementation
# ---------------------------------------------------------------------------
def _export_with_moviepy(frames, output_path, fps, progress_cb, quality):
    # Support MoviePy 2.x, 1.x, and legacy layouts
    try:
        from moviepy import ImageSequenceClip
    except ImportError:
        try:
            from moviepy.editor import ImageSequenceClip
        except ImportError:
            from moviepy.video.io.ImageSequenceClip import ImageSequenceClip

    np_frames = []
    n_frames = len(frames)
    for i, f in enumerate(frames):
        np_frames.append(np.array(f.convert("RGB")))
        if progress_cb and i % 5 == 0:
            progress_cb(0.3 * (i / n_frames))

    clip = ImageSequenceClip(np_frames, fps=fps)

    # crf: lower = higher quality (18-23 is visually lossless)
    crf_val = str(max(14, 28 - quality * 2))

    clip.write_videofile(
        str(output_path),
        codec="libx264",
        ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", crf_val],
        logger=None,
    )

    if progress_cb:
        progress_cb(1.0)

    del np_frames, clip
    gc.collect()
    return output_path


# ---------------------------------------------------------------------------
# OpenCV Implementation
# ---------------------------------------------------------------------------
def _export_with_opencv(frames, output_path, fps, W, H, progress_cb):
    import cv2

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (W, H))
    if not writer.isOpened():
        raise RuntimeError("OpenCV VideoWriter failed to open file for writing")

    n_frames = len(frames)
    for i, frame in enumerate(frames):
        arr = np.array(frame.convert("RGB"))
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        writer.write(bgr)
        if progress_cb and i % 5 == 0:
            progress_cb(i / n_frames)

    writer.release()
    if progress_cb:
        progress_cb(1.0)
    return output_path


# ---------------------------------------------------------------------------
# FFmpeg Subprocess Implementation
# ---------------------------------------------------------------------------
def _export_with_ffmpeg(frames, output_path, fps, progress_cb):
    tmp_dir = Path(tempfile.mkdtemp())
    n_frames = len(frames)

    for i, frame in enumerate(frames):
        frame_path = tmp_dir / f"frame_{i:06d}.png"
        frame.convert("RGB").save(str(frame_path), format="PNG")
        if progress_cb and i % 5 == 0:
            progress_cb(0.5 * (i / n_frames))

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(tmp_dir / "frame_%06d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "19",
        str(output_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)

    for p in tmp_dir.glob("*.png"):
        p.unlink(missing_ok=True)
    tmp_dir.rmdir()

    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg command failed: {res.stderr}")

    if progress_cb:
        progress_cb(1.0)
    return output_path


# ---------------------------------------------------------------------------
# Canvas Framing Utility
# ---------------------------------------------------------------------------
def _fit_on_canvas(image: Image.Image, W: int, H: int) -> Image.Image:
    """Scale *image* proportionally to fit inside canvas (W x H) with black letterboxing."""
    if image.size == (W, H):
        return image

    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    img_w, img_h = image.size
    scale = min(W / img_w, H / img_h)
    new_w, new_h = max(1, int(img_w * scale)), max(1, int(img_h * scale))
    resized = image.resize((new_w, new_h), Image.LANCZOS)
    x = (W - new_w) // 2
    y = (H - new_h) // 2
    canvas.paste(resized, (x, y))
    return canvas
