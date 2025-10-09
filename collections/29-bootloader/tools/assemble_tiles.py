#!/usr/bin/env python3
"""
Assemble small PNGs from a folder into:
  - a fixed grid collage (e.g., 3x3, 10x5, auto)
  - a pixel-mosaic (match each ref-image pixel to the closest tile by average color)

Run with no flags — edit CONFIG below.
Optionally override with CLI flags (all optional).

Requires: Pillow (pip install Pillow)
"""

from __future__ import annotations
import argparse, math, random
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from PIL import Image

# =======================
# CONFIG — edit these
# =======================
CONFIG = {
    # Where to read tiles (png/jpg/webp)
    "INPUT_DIR": "out/voxelfrog/exports",

    # Output file path
    "OUTPUT_PATH": "out/voxelfrog/tower_mosaic3.png",

    # "grid" or "mosaic"
    "MODE": "mosaic",

    # ---------- GRID MODE ----------
    # If both GRID_ROWS and GRID_COLS are None, we'll auto-pick a near-square layout.
    "GRID_ROWS": None,       # e.g., 3
    "GRID_COLS": None,       # e.g., 3

    # Size of each grid cell in output pixels
    "CELL_W": 64,
    "CELL_H": 64,

    # padding (pixels) between cells; background will show in gaps
    "PADDING": 0,

    # ordering of tiles: "name" | "mtime" | "random"
    "ORDER": "name",
    "SEED": 0,               # used only if ORDER == "random"

    # Background color for the canvas (RGBA tuple or hex like "#00000000")
    "BACKGROUND": (0, 0, 0, 0),

    # Resize fit mode for cell placement: "fit" | "cover"
    # - fit: letterbox inside cell, preserves full tile
    # - cover: fill entire cell, may crop
    "RESIZE_MODE": "fit",

    # ---------- MOSAIC MODE ----------
    # Reference image whose pixels we will reconstruct with tiles
    # If None, we will synthesize a near-square reference layout sized to the number of tiles.
    "REF_IMAGE": "../projects/towers/399.png",       # e.g., "projects/voxelfrog/input/base.png"

    # Target mosaic grid size (in reference pixels). If not set, uses ref image size.
    # You can force e.g. 48x48 by setting both. If only one is set, the other is scaled by aspect.
    "MOS_ROWS": 64,
    "MOS_COLS": 64,

    # Size of each mosaic cell (px) in the output
    "MOS_CELL": 49,

    # If True, we’ll allow reusing the same tile many times.
    # If False, we try to avoid repeats by simple round-robin shuffling when there are at least as many tiles as cells.
    "ALLOW_REUSE": True,

    # Limit the number of tiles used (after ordering). None = all.
    "MAX_TILES": None,
}

# =======================
# Internals
# =======================
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

def _resolve(p: str | Path) -> Path:
    p = Path(p) if not isinstance(p, Path) else p
    if p.is_absolute():
        return p
    # try cwd first
    if p.exists():
        return p
    # try relative to tools/
    p1 = SCRIPT_DIR / p
    if p1.exists() or not p.suffix:
        return p1
    # repo root
    return REPO_ROOT / p

def _to_rgba_tuple(x) -> Tuple[int,int,int,int]:
    if isinstance(x, tuple) and len(x) in (3,4):
        return (x[0], x[1], x[2], 255 if len(x)==3 else x[3])
    if isinstance(x, str) and x.startswith("#"):
        s = x.lstrip("#")
        if len(s)==3: s = "".join(ch*2 for ch in s)
        if len(s)==6: s += "ff"
        return tuple(int(s[i:i+2], 16) for i in (0,2,4,6))
    raise ValueError("BACKGROUND must be RGBA tuple or hex string")

def _list_images(input_dir: Path) -> List[Path]:
    exts = {".png",".jpg",".jpeg",".webp",".bmp"}
    files = [p for p in sorted(input_dir.iterdir()) if p.suffix.lower() in exts and p.is_file()]
    return files

def _order_files(files: List[Path], how: str, seed: int) -> List[Path]:
    if how == "name":
        return sorted(files, key=lambda p: p.name.lower())
    if how == "mtime":
        return sorted(files, key=lambda p: p.stat().st_mtime)
    if how == "random":
        rnd = random.Random(seed)
        files = list(files)
        rnd.shuffle(files)
        return files
    return files

def _avg_rgb(img: Image.Image) -> Tuple[float,float,float]:
    # quick average using resize to tiny then mean
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    small = img.resize((1,1), Image.BOX)
    r,g,b,a = small.getpixel((0,0))
    return (r,g,b)

def _resize_into_cell(tile: Image.Image, cw: int, ch: int, mode: str) -> Image.Image:
    # returns an RGBA tile sized exactly (cw,ch); letterboxed (fit) or cropped (cover)
    tile = tile.convert("RGBA")
    tw, th = tile.size
    if mode == "cover":
        scale = max(cw/tw, ch/th) if tw and th else 1.0
    else:
        scale = min(cw/tw, ch/th) if tw and th else 1.0
    nw, nh = max(1, int(round(tw*scale))), max(1, int(round(th*scale)))
    scaled = tile.resize((nw, nh), Image.NEAREST)
    # paste into canvas
    out = Image.new("RGBA", (cw, ch), (0,0,0,0))
    x0 = (cw - nw)//2
    y0 = (ch - nh)//2
    out.alpha_composite(scaled, (x0, y0))
    return out

# ------------- GRID MODE -------------
def assemble_grid(input_dir: Path, files: List[Path], out_path: Path, cfg: Dict[str, Any]):
    if cfg["MAX_TILES"]:
        files = files[: int(cfg["MAX_TILES"])]

    n = len(files)
    if n == 0:
        raise SystemExit(f"No images found in {input_dir}")

    rows = cfg["GRID_ROWS"]
    cols = cfg["GRID_COLS"]
    if rows is None and cols is None:
        # near-square grid
        cols = int(math.ceil(math.sqrt(n)))
        rows = int(math.ceil(n / cols))
    elif rows is None:
        rows = int(math.ceil(n / cols))
    elif cols is None:
        cols = int(math.ceil(n / rows))

    cw, ch = int(cfg["CELL_W"]), int(cfg["CELL_H"])
    pad = int(cfg["PADDING"])
    bg = _to_rgba_tuple(cfg["BACKGROUND"])

    W = cols*cw + (cols-1)*pad
    H = rows*ch + (rows-1)*pad
    canvas = Image.new("RGBA", (W, H), bg)

    i = 0
    for r in range(rows):
        for c in range(cols):
            if i >= n: break
            tile = Image.open(files[i])
            tile_cell = _resize_into_cell(tile, cw, ch, cfg["RESIZE_MODE"])
            x = c*(cw+pad)
            y = r*(ch+pad)
            canvas.alpha_composite(tile_cell, (x,y))
            i += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    print(f"[grid] {n} tiles → {rows}x{cols}  |  {out_path}")

# ------------- MOSAIC MODE -------------
def _compute_target_grid(n_tiles: int, mos_rows: Optional[int], mos_cols: Optional[int], ref_img: Optional[Image.Image]) -> Tuple[int,int]:
    if ref_img:
        rh, rw = ref_img.size[1], ref_img.size[0]
        if mos_rows and mos_cols:
            return mos_rows, mos_cols
        if mos_cols and not mos_rows:
            # scale rows by aspect
            return int(round(mos_cols * rh / max(1, rw))), mos_cols
        if mos_rows and not mos_cols:
            return mos_rows, int(round(mos_rows * rw / max(1, rh)))
        # no overrides — use ref size
        return rh, rw
    # no ref — try near-square using tile count
    cols = int(math.ceil(math.sqrt(n_tiles)))
    rows = int(math.ceil(n_tiles / cols))
    # allow overrides to force one dimension
    if mos_rows and not mos_cols:
        rows = mos_rows
        cols = int(math.ceil(n_tiles/rows))
    if mos_cols and not mos_rows:
        cols = mos_cols
        rows = int(math.ceil(n_tiles/cols))
    return rows, cols

def assemble_mosaic(input_dir: Path, files: List[Path], out_path: Path, cfg: Dict[str, Any]):
    if cfg["MAX_TILES"]:
        files = files[: int(cfg["MAX_TILES"])]

    if len(files) == 0:
        raise SystemExit(f"No images found in {input_dir}")

    # load reference (optional)
    ref_img = None
    if cfg["REF_IMAGE"]:
        ref_p = _resolve(cfg["REF_IMAGE"])
        ref_img = Image.open(ref_p).convert("RGBA")

    # determine mosaic grid (rows x cols)
    rows, cols = _compute_target_grid(len(files), cfg["MOS_ROWS"], cfg["MOS_COLS"], ref_img)

    # build list of tiles + their average colors
    tiles: List[Image.Image] = []
    avgs: List[Tuple[float,float,float]] = []
    for p in files:
        im = Image.open(p).convert("RGBA")
        tiles.append(im)
        avgs.append(_avg_rgb(im))

    # prepare reference pixel colors
    if ref_img:
        ref_small = ref_img.resize((cols, rows), Image.NEAREST)
        ref_pixels = [ref_small.getpixel((x,y)) for y in range(rows) for x in range(cols)]
        # convert RGBA -> RGB
        ref_colors = [(r,g,b) for (r,g,b,a) in ref_pixels]
    else:
        # no ref: just fill in order (left->right, top->bottom)
        ref_colors = None

    # output canvas
    cell = int(cfg["MOS_CELL"])
    pad = int(cfg["PADDING"])
    bg = _to_rgba_tuple(cfg["BACKGROUND"])

    W = cols*cell + (cols-1)*pad
    H = rows*cell + (rows-1)*pad
    canvas = Image.new("RGBA", (W,H), bg)

    # optional reuse-avoidance bookkeeping
    order = list(range(len(tiles)))
    if not cfg["ALLOW_REUSE"] and ref_colors is None:
        # simple: just place each tile once in reading order; extra cells reuse from start
        pass

    # build a small cache for resized tiles to (cell,cell)
    tile_cache: Dict[int, Image.Image] = {}

    # match function (nearest average)
    def nearest_tile(rgb: Tuple[int,int,int]) -> int:
        best_i, best_d = 0, 1e9
        r,g,b = rgb
        for i,(ar,ag,ab) in enumerate(avgs):
            d = (r-ar)*(r-ar) + (g-ag)*(g-ag) + (b-ab)*(b-ab)
            if d < best_d:
                best_d, best_i = d, i
        return best_i

    # assemble
    t = 0
    for r in range(rows):
        for c in range(cols):
            if ref_colors is None:
                # just pick in order (wrapping)
                idx = order[t % len(order)]
            else:
                idx = nearest_tile(ref_colors[r*cols + c])

            if idx not in tile_cache:
                tile_cache[idx] = _resize_into_cell(tiles[idx], cell, cell, "cover")
            x = c*(cell+pad)
            y = r*(cell+pad)
            canvas.alpha_composite(tile_cache[idx], (x,y))
            t += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    print(f"[mosaic] {rows}x{cols} cells  |  {out_path}")

# =======================
# main
# =======================
def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--input-dir")
    ap.add_argument("--out")
    ap.add_argument("--mode", choices=["grid","mosaic"])
    ap.add_argument("--rows", type=int)
    ap.add_argument("--cols", type=int)
    ap.add_argument("--cellw", type=int)
    ap.add_argument("--cellh", type=int)
    ap.add_argument("--pad", type=int)
    ap.add_argument("--order", choices=["name","mtime","random"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--bg")
    ap.add_argument("--resize", choices=["fit","cover"])
    ap.add_argument("--ref")
    ap.add_argument("--mos-rows", type=int)
    ap.add_argument("--mos-cols", type=int)
    ap.add_argument("--mos-cell", type=int)
    ap.add_argument("--allow-reuse", action="store_true")
    ap.add_argument("--max-tiles", type=int)
    args = ap.parse_args()

    cfg = dict(CONFIG)
    def o(k, v): 
        if v is not None: cfg[k] = v
    o("INPUT_DIR", args.input_dir)
    o("OUTPUT_PATH", args.out)
    o("MODE", args.mode)
    o("GRID_ROWS", args.rows)
    o("GRID_COLS", args.cols)
    o("CELL_W", args.cellw)
    o("CELL_H", args.cellh)
    o("PADDING", args.pad)
    o("ORDER", args.order)
    o("SEED", args.seed)
    o("BACKGROUND", args.bg)
    o("RESIZE_MODE", args.resize)
    o("REF_IMAGE", args.ref)
    o("MOS_ROWS", args.mos_rows)
    o("MOS_COLS", args.mos_cols)
    o("MOS_CELL", args.mos_cell)
    if args.allow_reuse: cfg["ALLOW_REUSE"] = True
    o("MAX_TILES", args.max_tiles)

    input_dir = _resolve(cfg["INPUT_DIR"])
    out_path = _resolve(cfg["OUTPUT_PATH"])

    if not input_dir.exists():
        raise SystemExit(f"Input dir not found: {input_dir}")

    files = _list_images(input_dir)
    files = _order_files(files, cfg["ORDER"], cfg["SEED"])
    if cfg["MAX_TILES"]:
        files = files[: int(cfg["MAX_TILES"])]

    if cfg["MODE"] == "grid":
        assemble_grid(input_dir, files, out_path, cfg)
    else:
        assemble_mosaic(input_dir, files, out_path, cfg)

if __name__ == "__main__":
    main()
