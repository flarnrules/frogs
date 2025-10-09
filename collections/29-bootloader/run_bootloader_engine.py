#!/usr/bin/env python3
import argparse, importlib, json
from pathlib import Path
from engine.core import ProjectContext, merge_configs
from engine.io import ensure_dir
from engine.rle import png_to_runs
from engine.payload import pack_blob
from engine.template import BOOTLOADER_TEMPLATE
from engine.minify import minify_js

def main():
    ap = argparse.ArgumentParser(description="projects/<project>/input → out/<project>/ (bootloader snippet)")
    ap.add_argument("-p","--project", default="voxelfrog", help="project name under projects/")
    ap.add_argument("--png", help="explicit PNG path")
    ap.add_argument("--layers", help="explicit layers dir")
    ap.add_argument("--input-mode", choices=["auto","png","layers"], help="override project input mode")
    ap.add_argument("--max-colors", type=int)
    ap.add_argument("--no-trim", action="store_true")
    ap.add_argument("--bg", type=str, help="transparent → this hex (e.g. #000)")
    ap.add_argument("--out-root", type=str, default="out")
    ap.add_argument("--projects-root", type=str, default="projects")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    projects_root = (here / args.projects_root).resolve()
    out_root = (here / args.out_root).resolve()

    mod = importlib.import_module(f"projects.{args.project}.project")
    project = mod.get_project()

    proj_cfg = getattr(project, "config", lambda: {})() or {}
    cli_cfg = {}
    if args.input_mode: cli_cfg["INPUT_MODE"] = args.input_mode
    if args.max_colors is not None: cli_cfg["MAX_COLORS"] = args.max_colors
    if args.no_trim: cli_cfg["TRIM_TRANSPARENT"] = False
    if args.bg is not None: cli_cfg["BACKGROUND_HEX"] = args.bg

    cfg = merge_configs(project.default_config(), proj_cfg, cli_cfg)

    ctx = ProjectContext(
        name=args.project,
        projects_root=projects_root,
        out_root=out_root,
        explicit_png=args.png,
        explicit_layers=args.layers,
        config=cfg
    )

    img = project.resolve_input(ctx)

    model = png_to_runs(
        img,
        max_colors=cfg.get("MAX_COLORS"),
        trim=cfg.get("TRIM_TRANSPARENT", True),
        treat_transparent_as=project.parse_hex_color(cfg.get("BACKGROUND_HEX"))
    )

    out_dir = (out_root / args.project)
    ensure_dir(out_dir)
    (out_dir / "runs.json").write_text(json.dumps(model, separators=(',',':')), encoding="utf-8")

    payload = pack_blob(model)
    (out_dir / "packed.txt").write_text(payload, encoding="utf-8")

    base_pal_js = json.dumps(model["palette"], separators=(',',':'))
    probs_js = json.dumps({
        "flipx": cfg.get("FLIPX_PROB", 0.5),
        "flipy": cfg.get("FLIPY_PROB", 0.0),
        "rot90": cfg.get("ROT90_PROB", 0.0),
    }, separators=(',',':'))
    var_cfg_js = json.dumps({
        "hmin": cfg.get("HUE_SHIFT_DEG_MIN",0),
        "hmax": cfg.get("HUE_SHIFT_DEG_MAX",360),
        "smin": cfg.get("SAT_SCALE_MIN",1.0),
        "smax": cfg.get("SAT_SCALE_MAX",1.0),
        "lmin": cfg.get("LUM_SCALE_MIN",1.0),
        "lmax": cfg.get("LUM_SCALE_MAX",1.0),
    }, separators=(',',':'))
    fx_js = json.dumps(cfg.get("FX",{}), separators=(',',':'))

    # NEW: voxel-look knobs for the template
    vox_cfg_js = json.dumps({
        "thick": cfg.get("VOX_THICKNESS", 3),
        "dx": cfg.get("VOX_DX", 0.35),
        "dy": cfg.get("VOX_DY", -0.55),
        "shadeMin": cfg.get("VOX_SHADE_MIN", 0.70),
        "shadeMax": cfg.get("VOX_SHADE_MAX", 1.00),
    }, separators=(',',':'))

    js = (BOOTLOADER_TEMPLATE
        .replace("__PAYLOAD__", payload.replace("\\","\\\\").replace("'","\\'"))
        .replace("__BASE_PAL__", base_pal_js)
        .replace("__PROBS__", probs_js)
        .replace("__RENDER_MODE__", cfg.get("RENDER_MODE","rect"))
        .replace("__VAR_CFG__", var_cfg_js)
        .replace("__FX_CFG__", fx_js)
        .replace("__VOX_CFG__", vox_cfg_js)
    )
    js_min = minify_js(js)

    (out_dir / "bootloader_snippet.js").write_text(js, encoding="utf-8")
    (out_dir / "bootloader_snippet.min.js").write_text(js_min, encoding="utf-8")

    stats = {
        "project": args.project,
        "width": model["w"], "height": model["h"],
        "rows": len(model["runs"]), "palette_size": len(model["palette"]),
        "payload_bytes": len(payload.encode("utf-8")),
        "snippet_bytes": len(js.encode("utf-8")),
        "snippet_min_bytes": len(js_min.encode("utf-8")),
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    # Optional: project extras (no-op by default)
    extras = project.postbuild(ctx, model, out_dir) or {}

    print(f"[ok] {args.project}: {model['w']}×{model['h']} pal={len(model['palette'])}")
    for f in ["runs.json","packed.txt","bootloader_snippet.js","bootloader_snippet.min.js","stats.json"]:
        print("[out]", out_dir/f)
    for k, v in extras.items():
        print(f"[extra] {k}: {v}")

if __name__ == "__main__":
    main()
