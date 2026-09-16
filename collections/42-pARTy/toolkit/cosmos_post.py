#!/usr/bin/env python3
"""Loop-safe, palette-aware post processing for animated GIF artwork."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops


BAYER_8 = np.array(
    [
        [0, 32, 8, 40, 2, 34, 10, 42],
        [48, 16, 56, 24, 50, 18, 58, 26],
        [12, 44, 4, 36, 14, 46, 6, 38],
        [60, 28, 52, 20, 62, 30, 54, 22],
        [3, 35, 11, 43, 1, 33, 9, 41],
        [51, 19, 59, 27, 49, 17, 57, 25],
        [15, 47, 7, 39, 13, 45, 5, 37],
        [63, 31, 55, 23, 61, 29, 53, 21],
    ],
    dtype=np.float32,
) / 64.0


@dataclass
class Animation:
    frames: list[Image.Image]
    durations: list[int]
    loop: int = 0


def load_animation(path: Path, allow_still: bool = False) -> Animation:
    """Load and fully composite an animation; reject mislabeled stills by default."""
    with Image.open(path) as source:
        frame_count = int(getattr(source, "n_frames", 1))
        if frame_count < 2 and not allow_still:
            actual = (source.format or "unknown").upper()
            raise ValueError(
                f"{path.name} contains one {actual} frame, not an animation. "
                "Export/upload the original animated GIF, or pass --allow-still "
                "only to make an effect study."
            )

        frames: list[Image.Image] = []
        durations: list[int] = []
        fallback_duration = int(source.info.get("duration", 100) or 100)
        for index in range(frame_count):
            source.seek(index)
            frames.append(source.convert("RGBA").copy())
            durations.append(max(10, int(source.info.get("duration", fallback_duration) or fallback_duration)))
        return Animation(frames, durations, int(source.info.get("loop", 0) or 0))


def _bayer_mask(size: tuple[int, int], threshold: float, phase: int) -> np.ndarray:
    width, height = size
    shifted = np.roll(BAYER_8, shift=(phase * 3, phase * 5), axis=(0, 1))
    tiled = np.tile(shifted, (math.ceil(height / 8), math.ceil(width / 8)))
    return tiled[:height, :width] < threshold


def palette_dither_between(a: Image.Image, b: Image.Image, t: float, phase: int) -> Image.Image:
    """Choose pixels from adjacent drawings instead of inventing blended colors."""
    aa = np.asarray(a, dtype=np.uint8)
    bb = np.asarray(b, dtype=np.uint8)
    mask = _bayer_mask(a.size, t, phase)[..., None]
    return Image.fromarray(np.where(mask, bb, aa).astype(np.uint8), "RGBA")


def crossfade_between(a: Image.Image, b: Image.Image, t: float, _phase: int) -> Image.Image:
    return Image.blend(a, b, t)


def interpolate_animation(animation: Animation, factor: int, mode: str) -> Animation:
    """Increase frame count while keeping total runtime unchanged."""
    if factor < 1:
        raise ValueError("Interpolation factor must be at least 1")
    if factor == 1 or len(animation.frames) == 1:
        return animation

    mixer = palette_dither_between if mode == "palette_dither" else crossfade_between
    frames: list[Image.Image] = []
    durations: list[int] = []
    count = len(animation.frames)
    for index, frame in enumerate(animation.frames):
        following = animation.frames[(index + 1) % count]
        total = animation.durations[index]
        base, remainder = divmod(total, factor)
        for subframe in range(factor):
            t = subframe / factor
            frames.append(mixer(frame, following, t, index * factor + subframe))
            durations.append(max(10, base + (1 if subframe < remainder else 0)))
    return Animation(frames, durations, animation.loop)


def _loop_phase(index: int, count: int) -> float:
    return 2.0 * math.pi * index / max(1, count)


def _roll_rgba(array: np.ndarray, dx: int, dy: int) -> np.ndarray:
    return np.roll(array, shift=(dy, dx), axis=(0, 1))


def orbital_shear(frame: Image.Image, phase: float, strength: float) -> Image.Image:
    """Bend horizontal ribbons along a smooth, closed orbital path."""
    src = np.asarray(frame, dtype=np.uint8)
    height, width = src.shape[:2]
    out = np.empty_like(src)
    amplitude = max(1, round(width * 0.018 * strength))
    band = max(4, height // 64)
    for y in range(height):
        slow = math.sin(phase + y / height * math.tau * 2.0)
        fine = math.sin(phase * 2.0 - (y // band) * 0.73)
        dx = round(amplitude * (0.72 * slow + 0.28 * fine))
        out[y] = np.roll(src[y], dx, axis=0)
    return Image.fromarray(out, "RGBA")


def chromatic_echo(frame: Image.Image, phase: float, strength: float) -> Image.Image:
    """Offset bright color energy while keeping black structure stable."""
    src = np.asarray(frame, dtype=np.uint8)
    rgb = src[..., :3]
    luminance = rgb.max(axis=2)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    active = ((luminance > 48) & (chroma > 42))[..., None]
    radius = max(1, round(frame.width * 0.012 * strength))
    offsets = [
        (round(math.cos(phase) * radius), round(math.sin(phase) * radius)),
        (round(math.cos(phase + 2.094) * radius), round(math.sin(phase + 2.094) * radius)),
        (round(math.cos(phase + 4.189) * radius), round(math.sin(phase + 4.189) * radius)),
    ]
    out = src.copy()
    for channel, (dx, dy) in enumerate(offsets):
        shifted = _roll_rgba(src, dx, dy)
        out[..., channel] = np.where(active[..., 0], shifted[..., channel], src[..., channel])
    out[..., 3] = src[..., 3]
    return Image.fromarray(out, "RGBA")


def signal_weave(frame: Image.Image, phase: float, strength: float, seed: int) -> Image.Image:
    """Interlace deterministic color-family strips with a controlled digital cadence."""
    src = np.asarray(frame, dtype=np.uint8)
    height, width = src.shape[:2]
    out = src.copy()
    rgb = src[..., :3]
    dominant = np.argmax(rgb, axis=2)
    saturation = rgb.max(axis=2) - rgb.min(axis=2)
    rng = np.random.default_rng(seed)
    strip_height = max(3, height // 96)
    strip_offsets = rng.integers(-1, 2, size=math.ceil(height / strip_height))
    amplitude = max(1, round(width * 0.022 * strength))
    for strip, y0 in enumerate(range(0, height, strip_height)):
        y1 = min(height, y0 + strip_height)
        wave = math.sin(phase * 2.0 + strip * 0.81)
        gate = 0.5 + 0.5 * math.sin(phase + strip * 1.618)
        if gate < 0.55:
            continue
        dx = round(amplitude * wave) + int(strip_offsets[strip])
        shifted = np.roll(src[y0:y1], dx, axis=1)
        colorful = saturation[y0:y1] > 64
        family = dominant[y0:y1] == (strip % 3)
        mask = (colorful & family)[..., None]
        out[y0:y1] = np.where(mask, shifted, out[y0:y1])
    return Image.fromarray(out, "RGBA")


def apply_effect(animation: Animation, effect: str, strength: float, seed: int) -> Animation:
    if effect == "none" or strength <= 0:
        return animation
    processors = {
        "orbital_shear": lambda f, p: orbital_shear(f, p, strength),
        "chromatic_echo": lambda f, p: chromatic_echo(f, p, strength),
        "signal_weave": lambda f, p: signal_weave(f, p, strength, seed),
    }
    if effect not in processors:
        raise ValueError(f"Unknown effect: {effect}")
    frames = [processors[effect](frame, _loop_phase(i, len(animation.frames))) for i, frame in enumerate(animation.frames)]
    return Animation(frames, animation.durations.copy(), animation.loop)


def _global_palette(frames: list[Image.Image], colors: int) -> Image.Image:
    """Build one shared palette to prevent color shimmer between GIF frames."""
    sample_width = min(256, frames[0].width)
    scale = sample_width / frames[0].width
    sample_height = max(1, round(frames[0].height * scale))
    samples = [frame.convert("RGB").resize((sample_width, sample_height), Image.Resampling.NEAREST) for frame in frames]
    sheet = Image.new("RGB", (sample_width, sample_height * len(samples)))
    for index, sample in enumerate(samples):
        sheet.paste(sample, (0, index * sample_height))
    return sheet.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)


def save_gif(animation: Animation, path: Path, colors: int = 256) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    palette = _global_palette(animation.frames, colors)
    quantized = [
        frame.convert("RGB").quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG)
        for frame in animation.frames
    ]
    quantized[0].save(
        path,
        save_all=True,
        append_images=quantized[1:],
        duration=animation.durations,
        loop=animation.loop,
        disposal=2,
        optimize=False,
    )


def load_config(
    path: Path,
    requested_preset: str | None,
) -> tuple[dict, Path | None, Path | None, str]:
    """Load paths and one preset, resolving configured paths beside the JSON file."""
    config_path = path.expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))

    # Continue accepting the original flat presets-only format.
    if "presets" in config:
        presets = config["presets"]
        preset_name = requested_preset or config.get("default_preset")
        configured_input = config.get("input")
        configured_output = config.get("output")
    else:
        presets = config
        preset_name = requested_preset or "orbital_shear"
        configured_input = None
        configured_output = None

    if not preset_name:
        raise ValueError("Choose --preset or set default_preset in presets.json")
    if preset_name not in presets:
        raise ValueError(f"Unknown preset {preset_name!r}; choose from: {', '.join(presets)}")

    settings = dict(presets[preset_name])
    configured_input = settings.pop("input", configured_input)
    configured_output = settings.pop("output", configured_output)

    def resolve_configured_path(value: str | None) -> Path | None:
        if not value:
            return None
        candidate = Path(value).expanduser()
        return candidate if candidate.is_absolute() else config_path.parent / candidate

    return (
        settings,
        resolve_configured_path(configured_input),
        resolve_configured_path(configured_output),
        preset_name,
    )


def make_still_study(animation: Animation, frame_count: int, duration: int) -> Animation:
    frame = animation.frames[0]
    return Animation([frame.copy() for _ in range(frame_count)], [duration] * frame_count, 0)


def process(
    input_path: Path,
    output_path: Path,
    interpolate: int,
    interpolation_mode: str,
    effect: str,
    strength: float,
    seed: int,
    colors: int,
    allow_still: bool,
) -> Animation:
    animation = load_animation(input_path, allow_still=allow_still)
    if len(animation.frames) == 1:
        animation = make_still_study(animation, 22, 80)
    animation = interpolate_animation(animation, interpolate, interpolation_mode)
    animation = apply_effect(animation, effect, strength, seed)
    save_gif(animation, output_path, colors)
    return animation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, nargs="?", help="Overrides the input path in presets.json")
    parser.add_argument("output", type=Path, nargs="?", help="Overrides the output path in presets.json")
    parser.add_argument("--preset", help="Overrides default_preset in presets.json")
    parser.add_argument("--presets", type=Path, default=Path(__file__).with_name("presets.json"))
    parser.add_argument("--interpolate", type=int)
    parser.add_argument("--interpolation-mode", choices=("palette_dither", "crossfade"))
    parser.add_argument("--effect", choices=("none", "orbital_shear", "chromatic_echo", "signal_weave"))
    parser.add_argument("--strength", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--colors", type=int, default=256)
    parser.add_argument("--allow-still", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings, configured_input, configured_output, preset_name = load_config(args.presets, args.preset)
    for key in ("interpolate", "interpolation_mode", "effect", "strength", "seed"):
        value = getattr(args, key)
        if value is not None:
            settings[key] = value
    input_path = args.input if args.input is not None else configured_input
    output_path = args.output if args.output is not None else configured_output
    if input_path is None or output_path is None:
        missing = "input" if input_path is None else "output"
        raise ValueError(
            f"No {missing} path supplied. Add {missing!r} to {args.presets.name} "
            f"or pass it on the command line."
        )
    result = process(
        input_path,
        output_path,
        colors=args.colors,
        allow_still=args.allow_still,
        **settings,
    )
    total_ms = sum(result.durations)
    print(
        f"Wrote {output_path}: {len(result.frames)} frames, "
        f"{total_ms / 1000:.3f}s, loop={result.loop}, preset={preset_name}"
    )


if __name__ == "__main__":
    main()
