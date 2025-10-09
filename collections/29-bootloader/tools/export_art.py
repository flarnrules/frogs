#!/usr/bin/env python3
"""
Export assets from bootloader runs.json — with zero CLI required.
- PNG batches (rect or voxel-look)
- SVG batches (rect or voxel-look)
- Animated GIF (frames via hue rotation)

Run from anywhere (recommended from repo root), but works fine from the tools/ dir.
Defaults are set in CONFIG below; CLI args are *optional* overrides.

Examples (optional):
  python3 tools/export_art.py --format png --count 12
  python3 tools/export_art.py --format gif --gif-frames 32 --gif-dur 60
"""

from __future__ import annotations
import json, math, random, argparse
from pathlib import Path
from typing import List, Tuple, Dict, Any

# =======================
# CONFIG — edit these
# =======================
CONFIG = {
    # Path to out/<project>/runs.json
    "INPUT": "out/voxelfrog/runs.json",

    # Output directory (folder will be created)
    "OUTDIR": "out/voxelfrog/exports",

    # one of: "png" | "svg" | "gif"
    "FORMAT": "png",

    # one of: "rect" | "voxel"
    "MODE": "voxel",

    # batch count (for png/svg)
    "COUNT": 4096,

    # RNG seed (0 = fixed; change for variety)
    "SEED": 0,

    # flips / rotation (mirrors bootloader behavior)
    "FLIPX": False,
    "FLIPY": False,
    "ROT90": False,

    # palette transform knobs (match your bootloader defaults)
    "HUE_MIN": 0.0,
    "HUE_MAX": 360.0,
    "SAT_MIN": 0.25,
    "SAT_MAX": 2.05,
    "LUM_MIN": 0.97,
    "LUM_MAX": 1.03,

    # voxel-look params (SVG/PNG voxel mode)
    "VOX_THICK": 3,
    "VOX_DX": 0.35,
    "VOX_DY": -0.55,
    "VOX_SHADE_MIN": 0.70,
    "VOX_SHADE_MAX": 1.00,

    # GIF controls
    "GIF_FRAMES": 24,
    "GIF_DUR_MS": 80,
}

# =======================
# internals
# =======================
try:
    from PIL import Image, ImageDraw
except ImportError as e:
    raise SystemExit("This tool requires Pillow: pip install Pillow") from e

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent  # parent of tools/ → repo root


def _resolve_path(p: str | Path) -> Path:
    """Resolve a path with smart fallbacks: absolute, given as-is, tools/, repo_root/."""
    p = Path(p)
    if p.is_absolute():
        return p
    # try as given relative to CWD
    if p.exists():
        return p
    # try relative to tools/
    p1 = SCRIPT_DIR / p
    if p1.exists() or not p.suffix:  # for out dirs we may create later
        return p1
    # try relative to repo root
    p2 = REPO_ROOT / p
    return p2


# ---------- helpers (color + math) ----------
def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

def hex_to_rgb(hx: str) -> Tuple[int,int,int]:
    hx = hx.strip().lstrip("#")
    if len(hx) == 3:
        hx = "".join(ch*2 for ch in hx)
    return int(hx[0:2],16), int(hx[2:4],16), int(hx[4:6],16)

def rgb_to_hex(rgb: Tuple[int,int,int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def rot_hex(hx: str, deg: float, s_scale: float, l_scale: float) -> str:
    # HSL rotate + scale (matches bootloader)
    r,g,b = [v/255.0 for v in hex_to_rgb(hx)]
    mx, mn = max(r,g,b), min(r,g,b)
    l = (mx+mn)/2.0
    if mx == mn:
        h = 0.0; s = 0.0
    else:
        d = mx - mn
        s = d / (2.0 - mx - mn) if l > 0.5 else d / (mx + mn)
        if   mx == r: h = (g-b)/d + (6.0 if g < b else 0.0)
        elif mx == g: h = (b-r)/d + 2.0
        else:         h = (r-g)/d + 4.0
        h /= 6.0
    h = (h + (deg/360.0)) % 1.0
    s = clamp01(s * s_scale)
    l = clamp01(l * l_scale)
    def hue2rgb(p, q, t):
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q-p)*6*t
        if t < 1/2: return q
        if t < 2/3: return p + (q-p)*(2/3 - t)*6
        return p
    q = l*(1+s) if l < 0.5 else l + s - l*s
    p = 2*l - q
    r2 = int(round(hue2rgb(p,q,h+1/3)*255))
    g2 = int(round(hue2rgb(p,q,h    )*255))
    b2 = int(round(hue2rgb(p,q,h-1/3)*255))
    return rgb_to_hex((r2,g2,b2))

def build_palette(base: List[str], deg: float, smin: float, smax: float, lmin: float, lmax: float, rnd: random.Random) -> List[str]:
    ss = smin + (smax - smin) * rnd.random()
    ll = lmin + (lmax - lmin) * rnd.random()
    return [rot_hex(h, deg, ss, ll) for h in base]

# ---------- load model ----------
def load_runs(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

# ---------- transforms (flip/rot) ----------
def iter_pixels(model: Dict[str, Any], flipx: bool, flipy: bool, rot90: bool):
    """Yield (x,y,index,is_horizontal,run_len) for each RLE segment respecting flips/rot."""
    W, H = model["w"], model["h"]
    rows = model["runs"]
    if not rot90:
        for y, row in enumerate(rows):
            x = 0
            yy = (H-1-y) if flipy else y
            for L, idx in row:
                x0 = (W - (x+L)) if flipx else x
                yield x0, yy, idx, True, L
                x += L
    else:
        for y, row in enumerate(rows):
            x = 0
            for L, idx in row:
                nx = (H-1-y)
                ny = x
                if flipx: nx = (H-1) - nx
                if flipy: ny = (W - L) - ny
                yield nx, ny, idx, False, L
                x += L

# ---------- SVG writers ----------
def svg_header(w: int, h: int) -> List[str]:
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid meet">' % (w, h),
        '<style>*{shape-rendering:crispEdges}</style>'
    ]

def svg_footer() -> List[str]:
    return ['</svg>']

def write_svg_rect(model: Dict[str, Any], palette: List[str], flipx: bool, flipy: bool, rot90: bool) -> str:
    vw = model["h"] if rot90 else model["w"]
    vh = model["w"] if rot90 else model["h"]
    out = svg_header(vw, vh)
    groups: Dict[int, List[str]] = {}
    for x, y, idx, horiz, L in iter_pixels(model, flipx, flipy, rot90):
        rect = f'<rect x="{x}" y="{y}" width="{L if horiz else 1}" height="{1 if horiz else L}"/>'
        groups.setdefault(idx, []).append(rect)
    for idx, rects in groups.items():
        out.append(f'<g fill="{palette[idx]}">')
        out.extend(rects)
        out.append('</g>')
    out.extend(svg_footer())
    return "".join(out)

def write_svg_voxel(model: Dict[str, Any], palette: List[str], flipx: bool, flipy: bool, rot90: bool,
                    thick: int, dx: float, dy: float, shade_min: float, shade_max: float) -> str:
    vw = model["h"] if rot90 else model["w"]
    vh = model["w"] if rot90 else model["h"]
    out = svg_header(vw, vh)
    # precompute shades (near -> far)
    shades = [shade_min + (shade_max - shade_min) * (1 - (z/(thick-1) if thick>1 else 0)) for z in range(thick)]
    # build layers: translate + per-color groups
    layer_buckets: List[Dict[int, List[str]]] = [{ } for _ in range(thick)]
    for x, y, idx, horiz, L in iter_pixels(model, flipx, flipy, rot90):
        for z in range(thick):
            rect = f'<rect x="{x}" y="{y}" width="{L if horiz else 1}" height="{1 if horiz else L}"/>'
            layer_buckets[z].setdefault(idx, []).append(rect)
    for z in range(thick):
        out.append(f'<g transform="translate({dx*z},{dy*z})">')
        t = shades[z]
        for idx, rects in layer_buckets[z].items():
            r,g,b = hex_to_rgb(palette[idx])
            r2 = max(0, min(255, int(round(r*t))))
            g2 = max(0, min(255, int(round(g*t))))
            b2 = max(0, min(255, int(round(b*t))))
            out.append(f'<g fill="#{r2:02x}{g2:02x}{b2:02x}">')
            out.extend(rects)
            out.append('</g>')
        out.append('</g>')
    out.extend(svg_footer())
    return "".join(out)

# ---------- PNG renderers ----------
from PIL import Image, ImageDraw
def render_png_rect(model: Dict[str, Any], palette: List[str], flipx: bool, flipy: bool, rot90: bool) -> Image.Image:
    W = model["h"] if rot90 else model["w"]
    H = model["w"] if rot90 else model["h"]
    im = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(im)
    pal = [hex_to_rgb(h) + (255,) for h in palette]
    for x, y, idx, horiz, L in iter_pixels(model, flipx, flipy, rot90):
        if horiz: draw.rectangle([x, y, x+L-1, y], fill=pal[idx])
        else:     draw.rectangle([x, y, x, y+L-1], fill=pal[idx])
    return im

def render_png_voxel(model, palette, flipx, flipy, rot90,
                     thick, dx, dy, shade_min, shade_max):
    W = model["h"] if rot90 else model["w"]
    H = model["w"] if rot90 else model["h"]
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    base_rgba = [hex_to_rgb(h) + (255,) for h in palette]
    # near → far
    shades = [
        shade_min + (shade_max - shade_min) * (1 - (z/(thick-1) if thick > 1 else 0))
        for z in range(thick)
    ]

    for x, y, idx, horiz, L in iter_pixels(model, flipx, flipy, rot90):
        r, g, b, a = base_rgba[idx]
        for z, t in enumerate(shades):
            # translate and snap to integer pixel grid
            rx = int(round(x + dx * z))
            ry = int(round(y + dy * z))
            col = (int(r * t), int(g * t), int(b * t), a)

            if horiz:
                x0, y0 = rx, ry
                x1, y1 = rx + (L - 1), ry
            else:
                x0, y0 = rx, ry
                x1, y1 = rx, ry + (L - 1)

            # optional: clip to image bounds to avoid any out-of-bounds
            if x1 < 0 or y1 < 0 or x0 >= W or y0 >= H:
                continue
            x0 = max(0, min(W - 1, x0)); x1 = max(0, min(W - 1, x1))
            y0 = max(0, min(H - 1, y0)); y1 = max(0, min(H - 1, y1))

            draw.rectangle([x0, y0, x1, y1], fill=col)

    return im


# =======================
# main
# =======================
def main():
    # Optional CLI overrides (all fields optional)
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--input")
    ap.add_argument("--outdir")
    ap.add_argument("--format", choices=["png","svg","gif"])
    ap.add_argument("--mode", choices=["rect","voxel"])
    ap.add_argument("--count", type=int)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--flipx", action="store_true")
    ap.add_argument("--flipy", action="store_true")
    ap.add_argument("--rot90", action="store_true")
    ap.add_argument("--hue-min", type=float)
    ap.add_argument("--hue-max", type=float)
    ap.add_argument("--sat-min", type=float)
    ap.add_argument("--sat-max", type=float)
    ap.add_argument("--lum-min", type=float)
    ap.add_argument("--lum-max", type=float)
    ap.add_argument("--vox-thick", type=int)
    ap.add_argument("--vox-dx", type=float)
    ap.add_argument("--vox-dy", type=float)
    ap.add_argument("--vox-shade-min", type=float)
    ap.add_argument("--vox-shade-max", type=float)
    ap.add_argument("--gif-frames", type=int)
    ap.add_argument("--gif-dur", type=int)
    args = ap.parse_args()

    # Merge overrides into a local cfg
    cfg = dict(CONFIG)
    def o(key, argval): 
        if argval is not None: cfg[key] = argval
    o("INPUT", args.input)
    o("OUTDIR", args.outdir)
    o("FORMAT", args.format)
    o("MODE", args.mode)
    o("COUNT", args.count)
    o("SEED", args.seed)
    if args.flipx: cfg["FLIPX"] = True
    if args.flipy: cfg["FLIPY"] = True
    if args.rot90: cfg["ROT90"] = True
    o("HUE_MIN", args.hue_min); o("HUE_MAX", args.hue_max)
    o("SAT_MIN", args.sat_min); o("SAT_MAX", args.sat_max)
    o("LUM_MIN", args.lum_min); o("LUM_MAX", args.lum_max)
    o("VOX_THICK", args.vox_thick); o("VOX_DX", args.vox_dx); o("VOX_DY", args.vox_dy)
    o("VOX_SHADE_MIN", args.vox_shade_min); o("VOX_SHADE_MAX", args.vox_shade_max)
    o("GIF_FRAMES", args.gif_frames); o("GIF_DUR_MS", args.gif_dur)

    in_path  = _resolve_path(cfg["INPUT"])
    out_dir  = _resolve_path(cfg["OUTDIR"])
    out_dir.mkdir(parents=True, exist_ok=True)

    model = load_runs(in_path)

    rnd = random.Random(cfg["SEED"])
    base_palette = model["palette"]

    def build_pal_with_random_hsl():
        hue = rnd.uniform(cfg["HUE_MIN"], cfg["HUE_MAX"])
        return build_palette(base_palette, hue, cfg["SAT_MIN"], cfg["SAT_MAX"], cfg["LUM_MIN"], cfg["LUM_MAX"], rnd)

    if cfg["FORMAT"] == "gif":
        from PIL import Image
        frames: List[Image.Image] = []
        for fi in range(int(cfg["GIF_FRAMES"])):
            # evenly sweep hue range across frames
            if cfg["GIF_FRAMES"] > 1:
                t = fi / (cfg["GIF_FRAMES"] - 1)
                hue = cfg["HUE_MIN"] + (cfg["HUE_MAX"] - cfg["HUE_MIN"]) * t
            else:
                hue = cfg["HUE_MIN"]
            pal = build_palette(base_palette, hue, cfg["SAT_MIN"], cfg["SAT_MAX"], cfg["LUM_MIN"], cfg["LUM_MAX"], rnd)
            if cfg["MODE"] == "voxel":
                frame = render_png_voxel(model, pal, cfg["FLIPX"], cfg["FLIPY"], cfg["ROT90"],
                                         cfg["VOX_THICK"], cfg["VOX_DX"], cfg["VOX_DY"], cfg["VOX_SHADE_MIN"], cfg["VOX_SHADE_MAX"])
            else:
                frame = render_png_rect(model, pal, cfg["FLIPX"], cfg["FLIPY"], cfg["ROT90"])
            frames.append(frame.convert("P", palette=Image.ADAPTIVE, colors=256))
        gif_path = out_dir / "anim.gif"
        frames[0].save(gif_path, save_all=True, append_images=frames[1:], duration=int(cfg["GIF_DUR_MS"]), loop=0, optimize=True)
        print("[out]", gif_path)
        return

    # PNG or SVG batches
    for i in range(1, int(cfg["COUNT"]) + 1):
        pal = build_pal_with_random_hsl()

        if cfg["FORMAT"] == "png":
            if cfg["MODE"] == "voxel":
                im = render_png_voxel(model, pal, cfg["FLIPX"], cfg["FLIPY"], cfg["ROT90"],
                                      cfg["VOX_THICK"], cfg["VOX_DX"], cfg["VOX_DY"], cfg["VOX_SHADE_MIN"], cfg["VOX_SHADE_MAX"])
            else:
                im = render_png_rect(model, pal, cfg["FLIPX"], cfg["FLIPY"], cfg["ROT90"])
            path = out_dir / f"img_{i:03d}.png"
            im.save(path, optimize=True)
            print("[out]", path)

        elif cfg["FORMAT"] == "svg":
            if cfg["MODE"] == "voxel":
                svg = write_svg_voxel(model, pal, cfg["FLIPX"], cfg["FLIPY"], cfg["ROT90"],
                                      cfg["VOX_THICK"], cfg["VOX_DX"], cfg["VOX_DY"], cfg["VOX_SHADE_MIN"], cfg["VOX_SHADE_MAX"])
            else:
                svg = write_svg_rect(model, pal, cfg["FLIPX"], cfg["FLIPY"], cfg["ROT90"])
            path = out_dir / f"img_{i:03d}.svg"
            path.write_text(svg, encoding="utf-8")
            print("[out]", path)

if __name__ == "__main__":
    main()
