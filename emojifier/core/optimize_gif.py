from PIL import Image, ImageSequence
import os

# === CONFIGURATION ===
INPUT_GIF = "outputs/red_yellow64.gif"
OUTPUT_GIF = "outputs/red_yellow64_optimized.gif"
FINAL_SIZE = (1000, 1000)  # Set to None to keep original size
DITHER = Image.FLOYDSTEINBERG  # or Image.NONE

# === MAIN FUNCTION ===
def optimize_gif(input_path, output_path, final_size=None):
    print(f"📥 Optimizing: {input_path}")

    with Image.open(input_path) as gif:
        frame_durations = []
        frames = []

        for i, frame in enumerate(ImageSequence.Iterator(gif)):
            frame = frame.convert("RGBA")
            if final_size:
                frame = frame.resize(final_size, Image.Resampling.LANCZOS)

            # Quantize to adaptive palette with dithering
            quantized = frame.convert("P", palette=Image.ADAPTIVE, dither=DITHER)
            frames.append(quantized)
            frame_durations.append(gif.info.get("duration", 100))

        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=frame_durations,
            loop=gif.info.get("loop", 0),
            disposal=2,
            optimize=True
        )

    original_size = os.path.getsize(input_path) / 1024
    optimized_size = os.path.getsize(output_path) / 1024

    print(f"✅ Saved optimized GIF to: {output_path}")
    print(f"📦 Original size:  {original_size:.1f} KB")
    print(f"📦 Optimized size: {optimized_size:.1f} KB")

# === ENTRY POINT ===
if __name__ == "__main__":
    optimize_gif(INPUT_GIF, OUTPUT_GIF, FINAL_SIZE)
