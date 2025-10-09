from pathlib import Path
from typing import Dict
from PIL import Image
from engine.core import Project, ProjectContext
from engine.io import load_image_rgba, stack_layers

class Voxelfrog(Project):
    def default_config(self) -> Dict:
        return {
            "GENERATOR": "voxelfrog",
            "INPUT_MODE": "auto",
            "MAX_COLORS": 32,
            "TRIM_TRANSPARENT": True,
            "BACKGROUND_HEX": None,

            # voxel-look mode (pure SVG illusion)
            "RENDER_MODE": "voxel",
            "VOX_THICKNESS": 3,
            "VOX_DX": 0.35,
            "VOX_DY": -0.55,
            "VOX_SHADE_MIN": 0.70,
            "VOX_SHADE_MAX": 1.00,

            # keep flips/rot minimal for clarity
            "FLIPX_PROB": 0.0, "FLIPY_PROB": 0.0, "ROT90_PROB": 0.0,

            # palette shift knobs
            "HUE_SHIFT_DEG_MIN": 0, "HUE_SHIFT_DEG_MAX": 360,
            "SAT_SCALE_MIN": 0.25, "SAT_SCALE_MAX": 2.05,
            "LUM_SCALE_MIN": 0.97, "LUM_SCALE_MAX": 1.03,

            # effects off by default (clean read)
            "FX": {
                "hue_anim": {"prob": 0.0, "period_min": 1, "period_max": 14},
                "glitch_turb": {"prob": 0.0, "amp_min": 0.1, "amp_max": 5.5, "period_min": 1, "period_max": 12},
                "glitch_aberr": {"prob": 0.0, "dx_min": 0.0, "dx_max": 1.6, "dy_min": -1.25, "dy_max": 1.25},
                "glitch_noise": {"prob": 0.0, "amount_min": 0.02, "amount_max": 0.82},
                "glitch_fray": {"prob": 0.0, "dir": "random", "shift_min": 0.3, "shift_max": 2.6, "density_min": 0.25, "density_max": 1.75},
                "recursion": {"prob": 0.00, "mode_weights": {"one": 0.35, "some": 0.45, "all": 0.20}, "some_frac_min": 0.2, "some_frac_max": 0.6, "max_pixels": 20000}
            }
        }

    def config(self) -> Dict:
        return {}

    def resolve_input(self, ctx: ProjectContext) -> Image.Image:
        if ctx.explicit_png:
            p = Path(ctx.explicit_png)
            if not p.is_file(): raise FileNotFoundError(f"PNG not found: {p}")
            return load_image_rgba(p)
        if ctx.explicit_layers:
            d = Path(ctx.explicit_layers)
            if not d.is_dir(): raise FileNotFoundError(f"Layers dir not found: {d}")
            layers = sorted([p for p in d.iterdir() if p.suffix.lower()==".png"])
            if not layers: raise FileNotFoundError(f"No PNGs in {d}")
            return stack_layers(layers)

        base_png = ctx.projects_root / ctx.name / "input" / "base.png"
        layers_dir = ctx.projects_root / ctx.name / "input" / "layers"
        mode = ctx.config.get("INPUT_MODE","auto")

        if mode == "png":
            if not base_png.is_file(): raise FileNotFoundError(f"Expected PNG at {base_png}")
            return load_image_rgba(base_png)
        if mode == "layers":
            if not layers_dir.is_dir(): raise FileNotFoundError(f"Expected layers at {layers_dir}")
            layers = sorted([p for p in layers_dir.iterdir() if p.suffix.lower()==".png"])
            if not layers: raise FileNotFoundError(f"No PNGs in {layers_dir}")
            return stack_layers(layers)

        if layers_dir.is_dir():
            layers = sorted([p for p in layers_dir.iterdir() if p.suffix.lower()==".png"])
            if layers: return stack_layers(layers)
        if base_png.is_file():
            return load_image_rgba(base_png)
        raise FileNotFoundError(f"No input found under {ctx.projects_root/ctx.name/'input'}")

def get_project() -> Project:
    return Voxelfrog()
