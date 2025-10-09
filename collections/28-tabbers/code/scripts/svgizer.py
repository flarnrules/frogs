# code/scripts/svgizer.py
# Pixel/GIF -> SVG utilities for the frogs art engine
# - Row-run-length (RLE) compaction (each run = one <rect>)
# - Animated SVG with static base + frame deltas (SMIL <set> toggles)
# - Text/emoji rendering mode (each pixel -> <text> glyph)
#
# Usage (CLI examples):
#   python3 code/scripts/svgizer.py png_to_svg --input inputs/pixel.png --output outputs/pixel.svg --scale 12
#   python3 code/scripts/svgizer.py gif_to_svg --input inputs/anim.gif --output outputs/anim.svg --scale 12 --fps 6
#
# Import in your engine:
#   from code.scripts.svgizer import png_to_svg_file, gif_to_animated_svg_file, png_to_emoji_svg_file
#
# Benjamin-friendly: knobs live at the top of each function signature; no prompts; deterministic.

from __future__ import annotations
import os
import io
import math
import argparse
from dataclasses import dataclass
from typing import List, Tuple, Dict, Iterable, Optional

from PIL import Image, ImageSequence

RGBA = Tuple[int, int, int, int]

# ───────────────────────────────────────────────────────────────────────────────
# Utilities
# ───────────────────────────────────────────────────────────────────────────────

def _rgba_to_hex(rgba: RGBA) -> str:
    r, g, b, a = rgba
    return f"#{r:02x}{g:02x}{b:02x}"

def _is_opaque(c: RGBA, alpha_threshold: int) -> bool:
    return c[3] >= alpha_threshold

def _open_image(path: str) -> Image.Image:
    img = Image.open(path)
    # Convert paletted or RGB to RGBA for uniform processing
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img

def _row_rle(rgba_row: List[RGBA], alpha_threshold: int) -> List[Tuple[int, int, RGBA]]:
    """
    Run-length encode a single row of pixels (only opaque >= threshold produce runs).
    Returns list of (x_start, length, color_rgba).
    Transparent pixels are skipped (no runs emitted).
    """
    runs = []
    w = len(rgba_row)
    x = 0
    while x < w:
        if _is_opaque(rgba_row[x], alpha_threshold):
            color = rgba_row[x]
            x_start = x
            x += 1
            while x < w and rgba_row[x] == color and _is_opaque(rgba_row[x], alpha_threshold):
                x += 1
            runs.append((x_start, x - x_start, color))
        else:
            x += 1
    return runs

def _image_to_row_rles(img: Image.Image, alpha_threshold: int) -> List[List[Tuple[int, int, RGBA]]]:
    """
    Convert entire image to row-wise RLE (skipping transparent).
    """
    w, h = img.size
    px = img.load()
    rles: List[List[Tuple[int, int, RGBA]]] = []
    for y in range(h):
        row = [px[x, y] for x in range(w)]
        rles.append(_row_rle(row, alpha_threshold))
    return rles

def _frames_from_gif(gif_path: str, max_frames: Optional[int] = None) -> List[Image.Image]:
    base = Image.open(gif_path)
    frames: List[Image.Image] = []
    for idx, frame in enumerate(ImageSequence.Iterator(base)):
        if max_frames is not None and idx >= max_frames:
            break
        fr = frame.convert("RGBA")
        frames.append(fr)
    return frames

def _diff_mask(prev: Image.Image, curr: Image.Image, alpha_threshold: int) -> Image.Image:
    """
    Produce a binary mask (mode "1") where pixels differ beyond transparency threshold.
    """
    if prev.size != curr.size:
        raise ValueError("Frame size mismatch.")
    w, h = prev.size
    pprev, pcurr = prev.load(), curr.load()
    mask = Image.new("1", (w, h), 0)
    pmask = mask.load()
    for y in range(h):
        for x in range(w):
            a_ok_prev = pprev[x, y][3] >= alpha_threshold
            a_ok_curr = pcurr[x, y][3] >= alpha_threshold
            if a_ok_prev != a_ok_curr:
                pmask[x, y] = 1
            else:
                if a_ok_curr and (pprev[x, y] != pcurr[x, y]):
                    pmask[x, y] = 1
    return mask

def _majority_static(imgs: List[Image.Image], alpha_threshold: int) -> Image.Image:
    """
    For each pixel, choose the majority color across frames (considering alpha threshold).
    This becomes the static 'base' layer; non-matching pixels per frame will be emitted as deltas.
    Heuristic that works well when animations have small moving parts.
    """
    if not imgs:
        raise ValueError("No frames.")
    w, h = imgs[0].size
    for i in imgs[1:]:
        if i.size != (w, h):
            raise ValueError("All frames must be same size.")

    counts: Dict[Tuple[int, int], Dict[RGBA, int]] = {}
    for fr in imgs:
        px = fr.load()
        for y in range(h):
            for x in range(w):
                c = px[x, y]
                if _is_opaque(c, alpha_threshold):
                    counts.setdefault((x, y), {}).setdefault(c, 0)
                    counts[(x, y)][c] += 1

    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pbase = base.load()
    for y in range(h):
        for x in range(w):
            options = counts.get((x, y))
            if options:
                # pick most frequent color at this pixel
                best = max(options.items(), key=lambda kv: kv[1])[0]
                pbase[x, y] = best
            else:
                pbase[x, y] = (0, 0, 0, 0)
    return base

def _subtract(base: Image.Image, frame: Image.Image, alpha_threshold: int) -> Image.Image:
    """
    frame_delta = pixels in 'frame' that differ from 'base'
    """
    if base.size != frame.size:
        raise ValueError("Size mismatch in subtract.")
    w, h = base.size
    pbase, pfr = base.load(), frame.load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    pout = out.load()
    for y in range(h):
        for x in range(w):
            cb = pbase[x, y]; cf = pfr[x, y]
            if (_is_opaque(cf, alpha_threshold) and cf != cb) or (_is_opaque(cb, alpha_threshold) and not _is_opaque(cf, alpha_threshold)):
                pout[x, y] = cf
    return out

# ───────────────────────────────────────────────────────────────────────────────
# SVG building blocks
# ───────────────────────────────────────────────────────────────────────────────

@dataclass
class SvgBuildOpts:
    scale: int = 10                # pixel -> SVG units
    alpha_threshold: int = 1       # treat alpha >= threshold as visible
    include_bg_rect: bool = False  # emit a background rect (useful for filters)
    bg_color: str = "#000000"
    filter_id: Optional[str] = None  # apply filter to the root group if given
    title: Optional[str] = None
    desc: Optional[str] = None

def _svg_header(w: int, h: int, scale: int, title: Optional[str], desc: Optional[str]) -> str:
    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w*scale}" height="{h*scale}" viewBox="0 0 {w*scale} {h*scale}">')
    if title:
        out.append(f'  <title>{_escape_xml(title)}</title>')
    if desc:
        out.append(f'  <desc>{_escape_xml(desc)}</desc>')
    return "\n".join(out)

def _escape_xml(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&apos;"))

def _svg_defs_default_filters() -> str:
    # Sample filters: tweak as you like per-NFT
    return """  <defs>
    <!-- Grain -->
    <filter id="fx-grain" x="-10%" y="-10%" width="120%" height="120%">
      <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="1" seed="2" result="noise"/>
      <feColorMatrix in="noise" type="saturate" values="0"/>
      <feBlend in="SourceGraphic" in2="noise" mode="multiply"/>
    </filter>
    <!-- Glow -->
    <filter id="fx-glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="1" result="b1"/>
      <feMerge><feMergeNode in="b1"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>"""

def _svg_open_group(filter_id: Optional[str]) -> str:
    if filter_id:
        return f'  <g filter="url(#{filter_id})">'
    return f'  <g>'

def _svg_close_group() -> str:
    return "  </g>"

def _emit_bg_rect(w: int, h: int, scale: int, color: str) -> str:
    return f'    <rect x="0" y="0" width="{w*scale}" height="{h*scale}" fill="{color}" />'

def _emit_rle_rows(rles: List[List[Tuple[int, int, RGBA]]], y0: int, scale: int) -> str:
    """
    Emit <rect> per run. y0 allows vertical offset (for sprite strips if ever needed).
    """
    out = []
    for y, runs in enumerate(rles):
        if not runs:
            continue
        sy = (y0 + y) * scale
        for (x_start, length, rgba) in runs:
            fill = _rgba_to_hex(rgba)
            sx = x_start * scale
            out.append(f'    <rect x="{sx}" y="{sy}" width="{length*scale}" height="{1*scale}" fill="{fill}" />')
    return "\n".join(out)

# ───────────────────────────────────────────────────────────────────────────────
# Public: PNG → SVG (pixel-accurate, compact)
# ───────────────────────────────────────────────────────────────────────────────

def build_svg_from_image(
    img: Image.Image,
    opts: SvgBuildOpts = SvgBuildOpts()
) -> str:
    """
    Convert a single image to compact SVG with row-RLE rectangles.
    """
    w, h = img.size
    rles = _image_to_row_rles(img, opts.alpha_threshold)
    parts = []
    parts.append(_svg_header(w, h, opts.scale, opts.title, opts.desc))
    parts.append(_svg_defs_default_filters())
    parts.append(_svg_open_group(opts.filter_id))
    if opts.include_bg_rect:
        parts.append(_emit_bg_rect(w, h, opts.scale, opts.bg_color))
    parts.append(_emit_rle_rows(rles, 0, opts.scale))
    parts.append(_svg_close_group())
    parts.append("</svg>")
    return "\n".join(parts)

def png_to_svg_file(
    input_png: str,
    output_svg: str,
    scale: int = 10,
    alpha_threshold: int = 1,
    include_bg_rect: bool = False,
    bg_color: str = "#000000",
    filter_id: Optional[str] = None,
    title: Optional[str] = None,
    desc: Optional[str] = None,
) -> None:
    img = _open_image(input_png)
    svg = build_svg_from_image(
        img,
        SvgBuildOpts(
            scale=scale,
            alpha_threshold=alpha_threshold,
            include_bg_rect=include_bg_rect,
            bg_color=bg_color,
            filter_id=filter_id,
            title=title,
            desc=desc,
        ),
    )
    with open(output_svg, "w", encoding="utf-8") as f:
        f.write(svg)

# ───────────────────────────────────────────────────────────────────────────────
# Public: GIF → Animated SVG (static base + per-frame deltas)
# ───────────────────────────────────────────────────────────────────────────────

def build_animated_svg_from_frames(
    frames: List[Image.Image],
    fps: float = 6.0,
    opts: SvgBuildOpts = SvgBuildOpts(),
    use_static_base: bool = True
) -> str:
    """
    Animated SVG using discrete frame toggling (<set>).
    - Option use_static_base builds a majority-color static layer and emits only deltas per frame.
    - Loops indefinitely.
    """
    if not frames:
        raise ValueError("No frames provided.")
    w, h = frames[0].size
    for fr in frames[1:]:
        if fr.size != (w, h):
            raise ValueError("All frames must be the same size.")

    duration = len(frames) / fps

    # Build layers
    parts = []
    parts.append(_svg_header(w, h, opts.scale, opts.title, opts.desc))
    parts.append(_svg_defs_default_filters())
    parts.append('  <defs>')
    # master loop "clock"
    parts.append(f'    <animate id="clk" attributeName="x" from="0" to="0" dur="{duration:.6f}s" repeatCount="indefinite" />')
    parts.append('  </defs>')

    parts.append(_svg_open_group(opts.filter_id))
    if opts.include_bg_rect:
        parts.append(_emit_bg_rect(w, h, opts.scale, opts.bg_color))

    if use_static_base:
        base = _majority_static(frames, opts.alpha_threshold)
        base_rles = _image_to_row_rles(base, opts.alpha_threshold)
        parts.append('    <g id="base">')
        parts.append(_emit_rle_rows(base_rles, 0, opts.scale))
        parts.append('    </g>')

        # Frame deltas
        for i, fr in enumerate(frames):
            delta = _subtract(base, fr, opts.alpha_threshold)
            rles = _image_to_row_rles(delta, opts.alpha_threshold)
            if all((len(row) == 0) for row in rles):
                # No delta for this frame; skip emitting a group
                continue
            begin_t = (i / fps)
            end_t = ((i + 1) / fps)
            parts.append(f'    <g id="f{i}" style="display:none">')
            parts.append(_emit_rle_rows(rles, 0, opts.scale))
            # Show at frame window, then hide; both tied to the repeating clock
            parts.append(f'      <set attributeName="display" to="inline" begin="clk.begin+{begin_t:.6f}s" dur="{(1.0/fps):.6f}s" repeatCount="indefinite" />')
            parts.append('    </g>')
    else:
        # Emit full frames (heavier)
        for i, fr in enumerate(frames):
            rles = _image_to_row_rles(fr, opts.alpha_threshold)
            begin_t = (i / fps)
            parts.append(f'    <g id="f{i}" style="display:none">')
            parts.append(_emit_rle_rows(rles, 0, opts.scale))
            parts.append(f'      <set attributeName="display" to="inline" begin="clk.begin+{begin_t:.6f}s" dur="{(1.0/fps):.6f}s" repeatCount="indefinite" />')
            parts.append('    </g>')

    parts.append(_svg_close_group())
    parts.append("</svg>")
    return "\n".join(parts)

def gif_to_animated_svg_file(
    input_gif: str,
    output_svg: str,
    scale: int = 10,
    alpha_threshold: int = 1,
    fps: Optional[float] = None,
    max_frames: Optional[int] = None,
    include_bg_rect: bool = False,
    bg_color: str = "#000000",
    filter_id: Optional[str] = None,
    use_static_base: bool = True,
    title: Optional[str] = None,
    desc: Optional[str] = None,
) -> None:
    # Extract frames
    frames = _frames_from_gif(input_gif, max_frames=max_frames)
    if not frames:
        raise ValueError("GIF has no frames.")

    # If fps not provided, derive from GIF info (fallback to 6)
    if fps is None:
        delays = []
        base = Image.open(input_gif)
        for frame in ImageSequence.Iterator(base):
            delay_ms = frame.info.get("duration", 100)
            delays.append(delay_ms / 1000.0)
        avg = sum(delays) / len(delays) if delays else 0.1667
        fps = 1.0 / avg if avg > 0 else 6.0

    svg = build_animated_svg_from_frames(
        frames,
        fps=fps,
        opts=SvgBuildOpts(
            scale=scale,
            alpha_threshold=alpha_threshold,
            include_bg_rect=include_bg_rect,
            bg_color=bg_color,
            filter_id=filter_id,
            title=title,
            desc=desc,
        ),
        use_static_base=use_static_base
    )
    with open(output_svg, "w", encoding="utf-8") as f:
        f.write(svg)

# ───────────────────────────────────────────────────────────────────────────────
# Public: Text/Emoji mode (each pixel -> glyph)
# ───────────────────────────────────────────────────────────────────────────────

def build_textgrid_svg_from_image(
    img: Image.Image,
    charset: List[str],
    use_color: bool = True,
    font_family: str = "monospace",
    font_size_px: int = 12,
    opts: SvgBuildOpts = SvgBuildOpts()
) -> str:
    """
    Render each pixel as a glyph from 'charset'.
    By default, picks the SAME glyph (charset[0]) for all pixels; if you want
    brightness mapping, pass a graded charset (dark -> light) and uncomment logic below.
    """
    w, h = img.size
    px = img.load()
    parts = []
    parts.append(_svg_header(w, h, opts.scale, opts.title, opts.desc))
    parts.append(_svg_defs_default_filters())
    parts.append(_svg_open_group(opts.filter_id))
    if opts.include_bg_rect:
        parts.append(_emit_bg_rect(w, h, opts.scale, opts.bg_color))

    # Precompute positions so the glyph sits inside each pixel cell
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < opts.alpha_threshold:
                continue

            # brightness in [0, 255]
            # brightness = (0.2126*r + 0.7152*g + 0.0722*b)
            # idx = int((brightness / 255.0) * (len(charset) - 1))
            # ch = charset[idx]

            # For pixel-perfect emoji blocks, you might just use the first glyph:
            ch = charset[0] if charset else "■"

            fill = _rgba_to_hex((r, g, b, a)) if use_color else "#000000"
            # Position: anchor middle of the cell
            sx = x * opts.scale + opts.scale * 0.5
            sy = y * opts.scale + opts.scale * 0.75  # nudge baseline
            parts.append(
                f'    <text x="{sx:.2f}" y="{sy:.2f}" text-anchor="middle" '
                f'font-family="{_escape_xml(font_family)}" font-size="{font_size_px}" '
                f'fill="{fill}">{_escape_xml(ch)}</text>'
            )

    parts.append(_svg_close_group())
    parts.append("</svg>")
    return "\n".join(parts)

def png_to_emoji_svg_file(
    input_png: str,
    output_svg: str,
    charset: List[str],
    scale: int = 18,
    font_family: str = "Noto Color Emoji",
    font_size_px: int = 16,
    use_color: bool = True,
    alpha_threshold: int = 1,
    include_bg_rect: bool = False,
    bg_color: str = "#000000",
    filter_id: Optional[str] = None,
    title: Optional[str] = None,
    desc: Optional[str] = None,
) -> None:
    img = _open_image(input_png)
    svg = build_textgrid_svg_from_image(
        img,
        charset=charset,
        use_color=use_color,
        font_family=font_family,
        font_size_px=font_size_px,
        opts=SvgBuildOpts(
            scale=scale,
            alpha_threshold=alpha_threshold,
            include_bg_rect=include_bg_rect,
            bg_color=bg_color,
            filter_id=filter_id,
            title=title,
            desc=desc,
        ),
    )
    with open(output_svg, "w", encoding="utf-8") as f:
        f.write(svg)

# ───────────────────────────────────────────────────────────────────────────────
# CLI
# ───────────────────────────────────────────────────────────────────────────────

def _cli():
    parser = argparse.ArgumentParser(description="PNG/GIF → SVG converter (RLE, animation, emoji).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # png_to_svg
    p_png = sub.add_parser("png_to_svg", help="Convert a PNG to compact pixel-accurate SVG.")
    p_png.add_argument("--input", required=True)
    p_png.add_argument("--output", required=True)
    p_png.add_argument("--scale", type=int, default=10)
    p_png.add_argument("--alpha", type=int, default=1)
    p_png.add_argument("--bg", default=None, help="Background color hex (e.g., #000000). If set, include_bg_rect is true.")
    p_png.add_argument("--filter", default=None, help="Filter id (e.g., fx-grain or fx-glow).")
    p_png.add_argument("--title", default=None)
    p_png.add_argument("--desc", default=None)

    # gif_to_svg
    p_gif = sub.add_parser("gif_to_svg", help="Convert a GIF to animated SVG.")
    p_gif.add_argument("--input", required=True)
    p_gif.add_argument("--output", required=True)
    p_gif.add_argument("--scale", type=int, default=10)
    p_gif.add_argument("--alpha", type=int, default=1)
    p_gif.add_argument("--fps", type=float, default=0.0, help="If 0, derive from GIF.")
    p_gif.add_argument("--max_frames", type=int, default=0)
    p_gif.add_argument("--static_base", action="store_true", help="Use static majority base + deltas.")
    p_gif.add_argument("--bg", default=None)
    p_gif.add_argument("--filter", default=None)
    p_gif.add_argument("--title", default=None)
    p_gif.add_argument("--desc", default=None)

    # png_to_emoji_svg
    p_em = sub.add_parser("png_to_emoji_svg", help="Convert a PNG to a text/emoji SVG grid.")
    p_em.add_argument("--input", required=True)
    p_em.add_argument("--output", required=True)
    p_em.add_argument("--scale", type=int, default=18)
    p_em.add_argument("--alpha", type=int, default=1)
    p_em.add_argument("--font_family", default="Noto Color Emoji")
    p_em.add_argument("--font_size", type=int, default=16)
    p_em.add_argument("--mono_color", action="store_true", help="Ignore pixel color, use black text.")
    p_em.add_argument("--glyph", default="🟩", help="Single glyph (or paste an emoji).")

    args = parser.parse_args()

    if args.cmd == "png_to_svg":
        png_to_svg_file(
            args.input, args.output,
            scale=args.scale,
            alpha_threshold=args.alpha,
            include_bg_rect=(args.bg is not None),
            bg_color=(args.bg or "#000000"),
            filter_id=args.filter,
            title=args.title, desc=args.desc
        )
    elif args.cmd == "gif_to_svg":
        gif_to_animated_svg_file(
            args.input, args.output,
            scale=args.scale,
            alpha_threshold=args.alpha,
            fps=(None if args.fps == 0.0 else args.fps),
            max_frames=(None if args.max_frames == 0 else args.max_frames),
            include_bg_rect=(args.bg is not None),
            bg_color=(args.bg or "#000000"),
            filter_id=args.filter,
            use_static_base=args.static_base,
            title=args.title, desc=args.desc
        )
    elif args.cmd == "png_to_emoji_svg":
        charset = [args.glyph] if args.glyph else ["■"]
        png_to_emoji_svg_file(
            args.input, args.output,
            charset=charset,
            scale=args.scale,
            font_family=args.font_family,
            font_size_px=args.font_size,
            use_color=(not args.mono_color),
            alpha_threshold=args.alpha
        )

if __name__ == "__main__":
    _cli()
