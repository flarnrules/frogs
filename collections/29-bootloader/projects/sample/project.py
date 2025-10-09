from pathlib import Path
from typing import Dict
from PIL import Image
from engine.core import Project, ProjectContext
from engine.io import load_image_rgba, stack_layers

class SampleProject(Project):
    # defaults sensible for your earlier script
    def default_config(self) -> Dict:
        return {
            "GENERATOR": "sample",
            "INPUT_MODE": "auto",   # "auto" | "png" | "layers"
            "MAX_COLORS": 32,
            "TRIM_TRANSPARENT": True,
            "BACKGROUND_HEX": None,
            "RENDER_MODE": "gradient",
            "FLIPX_PROB": 0.50,
            "FLIPY_PROB": 0.00,
            "ROT90_PROB": 0.00,
            "HUE_SHIFT_DEG_MIN": 0,
            "HUE_SHIFT_DEG_MAX": 360,
            "SAT_SCALE_MIN": 0.25, "SAT_SCALE_MAX": 2.05,
            "LUM_SCALE_MIN": 0.97, "LUM_SCALE_MAX": 1.03,
            "FX": {
                "hue_anim": {"prob": 0.4, "period_min": 1, "period_max": 14},
                "glitch_turb": {"prob": 0.4, "amp_min": 0.1, "amp_max": 5.5, "period_min": 1, "period_max": 12},
                "glitch_aberr": {"prob": 0.4, "dx_min": 0.0, "dx_max": 1.6, "dy_min": -1.25, "dy_max": 1.25},
                "glitch_noise": {"prob": 0.7, "amount_min": 0.02, "amount_max": 0.82},
                "glitch_fray": {"prob": 0.4, "dir": "random", "shift_min": 0.3, "shift_max": 2.6, "density_min": 0.25, "density_max": 1.75},
                "recursion": {"prob": 0.20, "mode_weights": {"one": 0.35, "some": 0.45, "all": 0.20}, "some_frac_min": 0.2, "some_frac_max": 0.6, "max_pixels": 20000}
            }
        }

    def config(self) -> Dict:
        # per-project overrides go here; keep empty if not needed
        return {}

    def resolve_input(self, ctx: ProjectContext) -> Image.Image:
        # explicit CLI paths take precedence
        if ctx.explicit_png:
            p = Path(ctx.explicit_png)
            if not p.is_file(): raise FileNotFoundError(f"PNG not found: {p}")
            return load_image_rgba(p)
        if ctx.explicit_layers:
            d = Path(ctx.explicit_layers)
            if not d.is_dir(): raise FileNotFoundError(f"Layers dir not found: {d}")
            layer_paths = sorted([p for p in d.iterdir() if p.suffix.lower()==".png"])
            if not layer_paths: raise FileNotFoundError(f"No PNGs in {d}")
            return stack_layers(layer_paths)

        # project-local defaults
        base_png = ctx.projects_root / ctx.name / "input" / "base.png"
        layers_dir = ctx.projects_root / ctx.name / "input" / "layers"
        mode = ctx.config.get("INPUT_MODE","auto")

        if mode == "png":
            if not base_png.is_file(): raise FileNotFoundError(f"Expected PNG at {base_png}")
            return load_image_rgba(base_png)
        if mode == "layers":
            if not layers_dir.is_dir(): raise FileNotFoundError(f"Expected layers at {layers_dir}")
            layer_paths = sorted([p for p in layers_dir.iterdir() if p.suffix.lower()==".png"])
            if not layer_paths: raise FileNotFoundError(f"No PNGs in {layers_dir}")
            return stack_layers(layer_paths)

        # auto: prefer layers if present
        if layers_dir.is_dir():
            layer_paths = sorted([p for p in layers_dir.iterdir() if p.suffix.lower()==".png"])
            if layer_paths: return stack_layers(layer_paths)
        if base_png.is_file():
            return load_image_rgba(base_png)

        raise FileNotFoundError(f"No input found under {ctx.projects_root/ctx.name/'input'} (need base.png or layers/*.png)")

def get_project() -> Project:
    return SampleProject()
