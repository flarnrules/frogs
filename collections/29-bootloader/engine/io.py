from pathlib import Path
from PIL import Image

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def load_image_rgba(path: Path) -> Image.Image:
    img = Image.open(path)
    if getattr(img, "is_animated", False):
        img.seek(0)
    return img.convert("RGBA")

def stack_layers(layer_paths: list[Path]) -> Image.Image:
    if not layer_paths: raise ValueError("No layer PNGs found.")
    base = load_image_rgba(layer_paths[0]); w,h = base.size
    for p in layer_paths[1:]:
        im = load_image_rgba(p)
        if im.size!=(w,h): raise ValueError(f"Layer size mismatch: {p.name} is {im.size}, expected {(w,h)}")
        base.alpha_composite(im)
    return base
