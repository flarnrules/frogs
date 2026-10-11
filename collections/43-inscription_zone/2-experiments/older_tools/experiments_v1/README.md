# Experiments: PNG to interactive SVG (v0.2)

Export a flattened 512 × 512 PNG from Aseprite. Run the converter with Python 3.11 or newer and Pillow:

```bash
python3.11 -m pip install Pillow
python3.11 svgize.py sample/experiment1.png output/experiment1-cat.svg --box 120 280 440 470 --max-bytes 900000
```

Open the SVG file directly in a browser. It fills the available screen while keeping the square art centered and in proportion. Move the mouse over the cat, click it, or drag a finger on a touchscreen. The art bends hard, adds an animated noise squiggle and red/blue edge fringing, then springs back. To make every enclosed shape respond, omit `--box`:

```bash
python3.11 svgize.py sample/experiment1.png output/experiment1.svg
```

The box is `left top right bottom` in the 512 × 512 drawing. Only complete same-color regions within it move. Regions touching the outside canvas edge remain fixed. This lets sky, ground, and other large backgrounds stay stable without a separate art layer. If an accent crosses the box boundary it remains fixed; enlarge the box to include it.

The output is a single SVG containing paths, filter effects and its own interaction script. The original pixel boundaries are preserved at rest; the slight red/blue fringe is an intentional addition. The script reads the path geometry from the SVG and updates boundary points near the mouse or touch. A normal webpage `<img src="...svg">` displays the resting art but does not run the interaction script; open the SVG directly or embed as a document (`<object>` or `<iframe>`). Test behavior in the target inscription viewer before publishing.

## Collection rules, provisional

- Canvas: 512 × 512 pixels, one still PNG per piece.
- Palette: EDG8 exactly: `#fdfdf8`, `#d32734`, `#da7d22`, `#e6da29`, `#28c641`, `#2d93dd`, `#7b53ad`, `#1b1c33`. Subsets are fine. Any other color or transparency fails validation.
- Resting geometry: pixel-exact, with a subtle red/blue fringe on the moving shapes.
- Background regions touching the canvas edge stay fixed; fully enclosed regions can move.
- Interaction: hover pushes gently, click gives a stronger impulse, touch and drag pushes, release springs back.
- Output: single SVG, no network requests or external dependencies. Conversion reports an error if the SVG exceeds the default 900,000-byte ceiling.

## Controls

```text
--box X0 Y0 X1 Y1          Restrict moving shapes to a rectangle
--radius 105               Pointer influence radius, SVG pixels
--strength 6               Impulse magnitude
--stiffness .035           Spring pull toward the original shape
--damping .87              Momentum retained per frame (0..1)
--max-displacement 95      Maximum distance any point can bend
--squiggle 8               Noise movement while active
--chroma .38               Red/blue fringe opacity (0..1)
--stride 10                Add a spring point every 10 pixels on long edges
--min-area 2               Smaller isolated regions stay fixed
--max-bytes 900000         Fail if the SVG exceeds this many bytes
```

For a stronger effect, increase `--strength` or `--squiggle`. For a softer wobble, lower `--stiffness`. For tighter recovery, raise it slightly. Increase `--damping` for longer oscillation; lower it to settle quickly. Smaller `--stride` bends long straight edges more smoothly, but increases file size and work per frame. Set `--chroma 0` to remove the fringe.

The supplied `output/experiment1-cat.svg` animates the cat and its enclosed details. The alternate `output/experiment1.svg` also animates the clouds and sun. Both are derived from the supplied sample PNG.
