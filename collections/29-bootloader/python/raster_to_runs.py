#!/usr/bin/env python3
import sys, os, json, argparse
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image

# ───────────────── helpers
def to_hex(rgb: Tuple[int,int,int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def base36(n:int)->str:
    chars="0123456789abcdefghijklmnopqrstuvwxyz"
    if n==0: return "0"
    s=""; m=abs(n)
    while m>0:
        m,r = divmod(m,36)
        s = chars[r]+s
    return s if n>=0 else "-"+s

def quantize(img: Image.Image, max_colors: Optional[int]) -> Image.Image:
    if not max_colors: 
        return img.convert("RGBA")
    # mediancut conservative; preserves crisp pixel fields
    return img.convert("RGBA").quantize(colors=max_colors, method=Image.MEDIANCUT).convert("RGBA")

def trim_alpha(img: Image.Image, thresh:int=0) -> Image.Image:
    bbox = img.split()[-1].point(lambda a: 255 if a>thresh else 0).getbbox()
    return img.crop(bbox) if bbox else img

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def stack_layers(layer_paths: List[Path]) -> Image.Image:
    if not layer_paths:
        raise ValueError("No layer PNGs found.")
    base = Image.open(layer_paths[0]).convert("RGBA")
    w,h = base.size
    for p in layer_paths[1:]:
        im = Image.open(p).convert("RGBA")
        if im.size != (w,h):
            raise ValueError(f"Layer size mismatch: {p.name} is {im.size}, expected {(w,h)}")
        base.alpha_composite(im)
    return base

def png_to_runs(img: Image.Image, max_colors: Optional[int], trim: bool, treat_transparent_as: Optional[Tuple[int,int,int]]):
    im = quantize(img, max_colors)
    if trim:
        im = trim_alpha(im)
    w,h = im.size
    px = im.load()

    palette: List[Tuple[int,int,int]] = []
    pindex = {}
    runs = []

    def idx_of(rgb: Tuple[int,int,int]):
        if rgb not in pindex:
            pindex[rgb] = len(palette)
            palette.append(rgb)
        return pindex[rgb]

    for y in range(h):
        row = []
        # seed
        r,g,b,a = px[0,y]
        cur = treat_transparent_as if (a==0 and treat_transparent_as is not None) else (r,g,b)
        length = 1
        for x in range(1,w):
            r,g,b,a = px[x,y]
            c = treat_transparent_as if (a==0 and treat_transparent_as is not None) else (r,g,b)
            if c == cur:
                length += 1
            else:
                row.append([length, idx_of(cur)])
                cur, length = c, 1
        row.append([length, idx_of(cur)])
        runs.append(row)

    pal_hex = [to_hex(rgb) for rgb in palette]
    return {"w": w, "h": h, "palette": pal_hex, "runs": runs}

def pack_blob(model: dict) -> str:
    w,h = model["w"], model["h"]
    pal = model["palette"]
    rows = model["runs"]
    p = "P:" + ",".join(pal)
    rparts=[]
    for row in rows:
        rparts.append(",".join(f"{base36(L)}.{base36(i)}" for (L,i) in row))
    r = "R:" + ";".join(rparts)
    return f"{base36(w)},{base36(h)}|{p}|{r}"

def parse_hex_color(s: Optional[str]) -> Optional[Tuple[int,int,int]]:
    if not s: return None
    t = s.strip().lstrip("#")
    if len(t)==3:
        t = "".join(ch*2 for ch in t)
    if len(t)!=6:
        raise ValueError("bg color must be 3 or 6 hex digits, e.g. #000 or #aabbcc")
    r = int(t[0:2],16); g=int(t[2:4],16); b=int(t[4:6],16)
    return (r,g,b)

# ───────────────── main
def main():
    ap = argparse.ArgumentParser(description="PNG/Layers → runs.json + packed.txt + stats")
    ap.add_argument("--generator", "-g", required=True, help="generator name (folder key under out/ and projects/)")
    ap.add_argument("--png", type=str, help="path to a single PNG")
    ap.add_argument("--layers", type=str, help="path to a folder of PNG layers (stacked in filename order)")
    ap.add_argument("--max-colors", type=int, default=None, help="palette clamp (e.g. 16, 32). Omit for original colors")
    ap.add_argument("--trim", action="store_true", help="trim fully transparent border")
    ap.add_argument("--bg", type=str, default=None, help="map fully transparent pixels to this hex color (e.g. #000)")
    ap.add_argument("--projects-root", type=str, default=str(Path(__file__).resolve().parents[1] / "projects"), help="projects/ root")
    ap.add_argument("--out-root", type=str, default=str(Path(__file__).resolve().parents[1] / "out"), help="out/ root")
    args = ap.parse_args()

    gen = args.generator
    projects_root = Path(args.projects_root)
    out_root = Path(args.out_root)
    out_dir = out_root / gen
    ensure_dir(out_dir)

    # resolve inputs
    img: Optional[Image.Image] = None
    if args.png:
        img_path = Path(args.png)
        if not img_path.is_file():
            # allow shorthand projects/<gen>/input/base.png
            img_path = projects_root / gen / "input" / "base.png"
        if not img_path.is_file():
            raise FileNotFoundError(f"PNG not found: {args.png}")
        img = Image.open(img_path).convert("RGBA")
    elif args.layers:
        layers_dir = Path(args.layers)
        if not layers_dir.is_dir():
            # allow shorthand projects/<gen>/input/layers
            layers_dir = projects_root / gen / "input" / "layers"
        if not layers_dir.is_dir():
            raise FileNotFoundError(f"Layers dir not found: {args.layers}")
        layer_paths = sorted([p for p in layers_dir.iterdir() if p.suffix.lower()==".png"])
        if not layer_paths:
            raise FileNotFoundError(f"No PNGs in layers dir: {layers_dir}")
        img = stack_layers(layer_paths)
    else:
        # default preference: layers if exist, else base.png
        layers_default = projects_root / gen / "input" / "layers"
        base_default = projects_root / gen / "input" / "base.png"
        if layers_default.is_dir():
            layer_paths = sorted([p for p in layers_default.iterdir() if p.suffix.lower()==".png"])
            img = stack_layers(layer_paths)
        elif base_default.is_file():
            img = Image.open(base_default).convert("RGBA")
        else:
            raise ValueError("No input specified. Provide --png or --layers, or place files under projects/<gen>/input/")

    treat_transparent = parse_hex_color(args.bg)
    model = png_to_runs(img, max_colors=args.max_colors, trim=args.trim, treat_transparent_as=treat_transparent)

    # write artifacts
    runs_path = out_dir / "runs.json"
    packed_path = out_dir / "packed.txt"
    with open(runs_path,"w") as f: json.dump(model,f,separators=(',',':'))
    with open(packed_path,"w") as f: f.write(pack_blob(model))

    # quick stats
    payload = packed_path.read_text()
    stats = {
        "generator": gen,
        "width": model["w"],
        "height": model["h"],
        "rows": len(model["runs"]),
        "palette_size": len(model["palette"]),
        "packed_bytes": len(payload.encode("utf-8")),
        "note": "bootloader_snippet sizes are computed by pack_bootloader_js.py"
    }
    with open(out_dir / "stats.json","w") as f: json.dump(stats,f,indent=2)
    print(f"[ok] {gen} w={model['w']} h={model['h']} palette={len(model['palette'])} rows={len(model['runs'])}")
    print(f"[ok] wrote: {runs_path} | {packed_path}")
    print(f"[stat] packed bytes: {stats['packed_bytes']}")

if __name__=="__main__":
    main()
