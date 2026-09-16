# pARTy Cosmos GIF Post

A deterministic, loop-safe post-processing tool for hard-edged animated art. It preserves the original runtime when adding in-between frames, uses one global output palette to prevent frame-to-frame color shimmer, and defaults to palette-safe interpolation instead of blurry crossfades.

## Quick start

Edit the paths and default preset at the top of `presets.json`:

```json
{
  "input": "../input/cosmos.gif",
  "output": "../output/cosmos_orbital_shear.gif",
  "default_preset": "orbital_shear",
  "presets": {
    "orbital_shear": {
      "interpolate": 2,
      "interpolation_mode": "palette_dither",
      "effect": "orbital_shear",
      "strength": 0.42,
      "seed": 1131
    }
  }
}
```

Then run without positional arguments:

```bash
python cosmos_post.py
```

Paths written in `presets.json` are resolved relative to `presets.json`, not relative to whichever terminal directory happens to be active.

Command-line paths still work and override the configured paths:

```bash
python cosmos_post.py input.gif output.gif --preset orbital_shear
```

For a 22-frame input, each included preset produces 44 frames at the same total runtime. The first frame remains an original frame; each inserted frame is a palette-dithered temporal midpoint.

Available presets:

- `clean_double`: interpolation only
- `orbital_shear`: looped horizontal deformation with two spatial frequencies
- `chromatic_echo`: rotating RGB separation applied only to colorful pixels
- `signal_weave`: deterministic strip displacement separated by dominant color family

Override any preset value from the command line:

```bash
python cosmos_post.py input.gif output.gif \
  --preset signal_weave \
  --strength 0.24 \
  --seed 2026 \
  --colors 192
```

You can also place `input` or `output` inside one individual preset. A per-preset path overrides the corresponding top-level path. A command-line path overrides both.

## Important input check

The tool rejects single-frame files by default—even files incorrectly named `.gif`. This prevents accidentally building a temporal treatment around a flattened upload.

To create a spatial-effect study from a still image, opt in explicitly:

```bash
python cosmos_post.py still.png study.gif --preset orbital_shear --allow-still
```

That study is useful for choosing an effect direction, but it is not a substitute for processing the original animated export.

## Design notes

- All motion uses closed sine/cosine paths, so the last generated pose leads smoothly back to the first.
- `palette_dither` selects pixels from neighboring source frames. It does not invent translucent intermediate colors.
- One palette is learned from the whole animation and reused for every output frame.
- Randomized decisions are deterministic for a given seed.
- GIF timing has a practical 10 ms resolution. If a source frame duration cannot divide evenly, the remainder is distributed across its generated subframes.
