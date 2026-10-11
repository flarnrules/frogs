# Experiments SVG converter — v3

This converter takes a flattened 512 × 512 EDG8 PNG and makes a single interactive SVG. It keeps a painted environment underneath the moving art. When the cat bends or breaks apart, sky, grass, and shadow show through its former position.

## Try the sample

From this folder with Python 3.11 or newer:

```bash
python3.11 -m pip install Pillow
python3.11 svgize.py sample/experiment1.png output/experiment1.svg
```

Open `output/experiment1.svg` directly in a browser. Moving near the artwork gradually wakes it; a stationary pointer lets it settle. Click the cat for a stronger spring burst, the clouds for a soft breakup and reconnection, and the sun for radial rays and distortion of the sky, grass, and shadow. Repeated clicks build intensity, which slowly fades. Touch and drag work too.

## Make real layers in Aseprite

The converter can infer the underpainting by extending the colors of the edge-connected scenery under enclosed objects. The sample inferred result is `sample/experiment1-underpainting.png`. You can edit that file in Aseprite to decide exactly what exists behind the cat.

For your own art, export two 512 × 512 PNGs:

1. A complete, flattened artwork, including the cat and other foreground objects.
2. A flattened background with the sky, grass, shadow, and anything that should be exposed when foreground objects move.

Then run:

```bash
python3.11 svgize.py art.png output/art.svg --background background.png
```

To get an editable starting background from a flattened drawing:

```bash
python3.11 svgize.py art.png output/art.svg --export-background background-draft.png
```

The output layers are the outer dark color, the painted background, the sun rays, fixed objects, and the moving colored shapes. The sample cloud shapes are divided into small pieces for their puff effect. `--box left top right bottom` restricts the moving objects and the active pointer region to that rectangle; leave it off to use the clouds and sun as well as the cat.

## Tune `effects.json`

Every EDG8 color has an `effect`, `force`, `noise`, `chroma`, and `include_edge` setting. The modes are `still`, `push`, `swirl`, `ripple`, `jitter`, `puff`, and `supernova`. A `puff` color also has `fragment_size`, the cell size in source pixels. The sample assigns `puff` to white clouds, `supernova` to yellow sun, `push` to the navy cat, and other motion to accents. All pixels of one palette color share that rule. If you need two white objects to behave differently, give them separate colors or supply a future effect mask.

The main controls are:

| Setting | What it changes |
| --- | --- |
| `outer_background` | Color of the space outside the 512 × 512 image; use `#111111` for near black. |
| `behavior.activation_margin` | How far outside the moving art the subtle approach effect starts. |
| `behavior.activation_ease` | How gradually motion rises toward its target. Smaller means a slower start. |
| `behavior.motion_decay` | How quickly a still pointer lets the art settle. |
| `behavior.hover_force` | Pointer push while moving. `0` leaves only smooth noise motion. |
| `behavior.strength`, `radius`, `squiggle` | Overall reach, force, and noisy deformation. |
| `behavior.click_gain`, `trip_cap`, `trip_decay` | How repeated clicks compound and fade. |
| `cloud.max_blur`, `click_gain`, `decay`, `cap` | Cloud softness and duration after a cloud click. |
| `supernova.ray_count`, `ray_opacity` | Number and visibility of sun rays. Set either to `0` to remove rays. |
| `supernova.background_warp` | Strength of the ambient distortion on a sun click. Set to `0` to disable it. |
| `supernova.click_gain`, `cap`, `decay`, `rotation_speed` | Sun burst buildup, limit, lifetime, and ray spin. |
| `max_bytes` | SVG limit, 900,000 bytes by default. |

The output is self-contained. It rejects unexpected colors, transparency, and invalid sizes. If an SVG exceeds the size limit, the converter reports an error and leaves the file available for inspection. A larger `--stride` or larger cloud `fragment_size` can reduce size and processing work.

A webpage `<img>` displays the still SVG without running its script. Open it as its own document or embed it with `<object>` or `<iframe>`. Verify behavior in the intended inscription viewer before publishing, since viewers differ in SVG script support.
