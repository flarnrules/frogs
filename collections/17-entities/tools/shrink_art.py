#!/usr/bin/env python3
# tools/shrink_art.py
# Minimal, extendable master compressor for PNG/GIF/WEBP/MP4 → optimized + variants.
# Inputs live up here.

INPUT_PATH = "./media"          # file or folder
OUTPUT_ROOT = "./out"           # where outputs go
MAKE_VARIANTS = True            # fanout variants
TARGET_MAX_BYTES = None         # e.g., 120_000 for strict on-chain caps
DITHER_MODE = "fs"              # "fs" (Floyd), "atkinson", "ordered", or None
PALETTE_COLORS = 64             # 256/128/64/32 — tighten to shrink
GIF_LOSSY = 50                  # 0 = lossless (if gifsicle present). 30–80 saves tons.
APNG_ENABLE = True
WEBP_QUALITY = 60               # 30–80 for stills/anim webp
AVIF_QUALITY = 45               # lower = smaller
SVG_TRACE_ENABLE = True         # try vectorization routes for posterized pieces

# --- no edits needed below --------------------------------------------
import os, sys, json, math, shutil, subprocess
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageOps

def has(cmd):
    return shutil.which(cmd) is not None

def run(cmd):
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception:
        return False

def ensure_dir(p): Path(p).mkdir(parents=True, exist_ok=True)

def quantize_img(im: Image.Image, colors=PALETTE_COLORS, dither=DITHER_MODE):
    mode = Image.FLOYDSTEINBERG if dither == "fs" else Image.NONE
    if dither == "atkinson":
        # crude Atkinson via ordered then small blur—cheap stand-in
        im = im.convert("RGB")
        im = im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.FLOYDSTEINBERG)
        return im
    if dither == "ordered":
        im = im.convert("RGB")
        return ImageOps.posterize(im, 8 - int(math.log2(colors)) if colors > 2 else 1)
    return im.convert("RGB").quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=mode)

def strip_metadata(im: Image.Image):
    data = list(im.getdata())
    out = Image.new(im.mode, im.size)
    out.putdata(data)
    return out

def save_png8(im, path):
    q = quantize_img(im)
    q.save(path, optimize=True)

def save_png24_oxipng(path):
    # oxipng → zopfli levels
    if has("oxipng"):
        run(["oxipng", "-o", "4", "--strip", "all", path])
    elif has("pngquant"):
        # fall back: palette’d + speed tradeoff
        run(["pngquant", "--force", "--output", path, "--strip", str(PALETTE_COLORS), path])

def optimize_gif(in_path, out_path):
    if has("gifsicle"):
        cmd = ["gifsicle", "-O3", "--no-comments", "--color", str(PALETTE_COLORS)]
        if GIF_LOSSY > 0:
            cmd += [f"--lossy={GIF_LOSSY}"]
        cmd += [in_path, "-o", out_path]
        run(cmd)
    else:
        # naive Pillow save (bigger than gifsicle)
        im = Image.open(in_path)
        im.save(out_path, save_all=True, optimize=True)

def make_apng(in_gif, out_png):
    if not APNG_ENABLE: return
    # ffmpeg path: GIF → APNG
    if has("ffmpeg"):
        run(["ffmpeg", "-y", "-i", in_gif, "-plays", "0", out_png])

def make_webp(in_path, out_path, q=WEBP_QUALITY):
    if has("ffmpeg"):
        run(["ffmpeg", "-y", "-i", in_path, "-c:v", "libwebp", "-quality", str(q),
             "-loop", "0", "-preset", "picture", out_path])
    else:
        im = Image.open(in_path)
        if getattr(im, "is_animated", False):
            im.save(out_path, save_all=True, quality=q)
        else:
            im.convert("RGBA").save(out_path, quality=q, method=6)

def make_avif(in_path, out_path, q=AVIF_QUALITY):
    if has("ffmpeg"):
        run(["ffmpeg", "-y", "-i", in_path, "-c:v", "libaom-av1", "-crf", str(q), "-still-picture", "1", out_path])

def size_bytes(p): 
    try: return Path(p).stat().st_size
    except: return None

def try_svg_trace(raster_path, svg_path):
    # Best with flat-color/palette inputs. Pref: "potrace" (via ppm) or "autotrace"; last resort: svgo clean on provided SVG.
    if not SVG_TRACE_ENABLE: return
    tmp_ppm = svg_path.with_suffix(".ppm")
    try:
        if has("magick"):
            run(["magick", raster_path, "-colors", str(PALETTE_COLORS), str(tmp_ppm)])
        elif has("convert"):
            run(["convert", raster_path, "-colors", str(PALETTE_COLORS), str(tmp_ppm)])
        else:
            return
        if has("potrace"):
            run(["potrace", str(tmp_ppm), "-s", "-o", str(svg_path), "--flat", "--turdsize", "10"])
            if has("svgo"):
                run(["svgo", "--config=--multipass", str(svg_path)])
    finally:
        if tmp_ppm.exists():
            tmp_ppm.unlink(missing_ok=True)

def compress_still(path, outdir):
    im = Image.open(path)
    im = strip_metadata(im)
    stem = Path(path).stem

    # PNG-8
    p_png8 = Path(outdir, f"{stem}.png")
    save_png8(im, p_png8)
    save_png24_oxipng(p_png8)

    # WebP & AVIF
    p_webp = Path(outdir, f"{stem}.webp")
    make_webp(path, p_webp)
    p_avif = Path(outdir, f"{stem}.avif")
    make_avif(path, p_avif)

    # Attempt SVG trace
    p_svg = Path(outdir, f"{stem}.svg")
    try_svg_trace(str(p_png8), p_svg)

    return [p for p in [p_png8, p_webp, p_avif, p_svg] if p.exists()]

def compress_gif(path, outdir):
    stem = Path(path).stem
    p_gif = Path(outdir, f"{stem}.gif")
    # Start from source as baseline output
    shutil.copy2(path, p_gif)
    optimize_gif(path, p_gif)

    # Fanout
    p_apng = Path(outdir, f"{stem}.png") if APNG_ENABLE else None
    if p_apng: make_apng(str(p_gif), str(p_apng))

    p_webp = Path(outdir, f"{stem}.webp")
    make_webp(path, p_webp)

    return [p for p in [p_gif, p_apng, p_webp] if p and p.exists()]

def maybe_enforce_budget(paths):
    if TARGET_MAX_BYTES is None:
        return
    for p in sorted(paths, key=lambda x: size_bytes(x) or 10**12, reverse=True):
        # If too big, try harsher quantization reruns—placeholder hook for future
        pass

def process_one(src):
    relname = Path(src).name
    outdir = Path(OUTPUT_ROOT, Path(src).stem)
    ensure_dir(outdir)

    suffix = Path(src).suffix.lower()
    made = []
    if suffix in [".png", ".jpg", ".jpeg"]:
        made += compress_still(src, outdir)
    elif suffix in [".gif"]:
        made += compress_gif(src, outdir)
    elif suffix in [".webp"]:
        # treat like still or anim via ffmpeg transcodes
        made += compress_still(src, outdir)
    else:
        # Best effort: try convert → PNG then proceed
        tmp_png = Path(outdir, Path(src).stem + "_conv.png")
        if has("ffmpeg"):
            run(["ffmpeg", "-y", "-i", src, str(tmp_png)])
            if tmp_png.exists():
                made += compress_still(tmp_png, outdir)

    if MAKE_VARIANTS:
        maybe_enforce_budget(made)

    report = { "source": src, "outputs": [] }
    for p in made:
        report["outputs"].append({"path": str(p), "bytes": size_bytes(p)})
    print(json.dumps(report, indent=2))

def discover_inputs(root):
    p = Path(root)
    if p.is_file(): return [str(p)]
    exts = {".png",".jpg",".jpeg",".gif",".webp",".bmp",".tiff"}
    return [str(f) for f in p.rglob("*") if f.suffix.lower() in exts]

def main():
    ensure_dir(OUTPUT_ROOT)
    for src in discover_inputs(INPUT_PATH):
        process_one(src)
    print("done")

if __name__ == "__main__":
    main()
