from PIL import Image, ImageSequence
import os

# === CONFIGURATION ===
INPUT_GIF = "../outputs/gifs/nectar_collectar4.gif"
OUTPUT_GIF = "../outputs/gifs/nectar_collectar4_optimized.gif"
FINAL_WIDTH = 1000  # Set to None to keep original size
DITHER = Image.FLOYDSTEINBERG  # or Image.NONE
USE_SHARED_PALETTE = False  # Set to True for global palette

def resize_keep_aspect(frame, target_width):
    original_width, original_height = frame.size
    aspect_ratio = original_height / original_width
    target_height = int(target_width * aspect_ratio)
    return frame.resize((target_width, target_height), Image.Resampling.LANCZOS)

def optimize_gif(input_path, output_path, final_width=None):
    print(f"📥 Optimizing: {input_path}")
    
    with Image.open(input_path) as gif:
        frame_durations = []
        raw_frames = []
        frames = []

        for i, frame in enumerate(ImageSequence.Iterator(gif)):
            frame = frame.convert("RGBA")
            if final_width:
                frame = resize_keep_aspect(frame, final_width)

            raw_frames.append(frame)
            frame_durations.append(gif.info.get("duration", 100))

        if USE_SHARED_PALETTE:
            print("🎨 Generating shared palette from first frame...")
            global_palette = raw_frames[0].convert("P", palette=Image.ADAPTIVE).getpalette()

        for i, frame in enumerate(raw_frames):
            if USE_SHARED_PALETTE:
                quantized = frame.convert("P")
                quantized.putpalette(global_palette)
            else:
                quantized = frame.convert("P", palette=Image.ADAPTIVE, dither=DITHER)

            frames.append(quantized)

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

    print(f"\n✅ Saved optimized GIF to: {output_path}")
    print(f"📦 Original size:  {original_size:.1f} KB")
    print(f"📦 Optimized size: {optimized_size:.1f} KB")
    print(f"📉 Compression ratio: {original_size / optimized_size:.2f}x smaller" if optimized_size else "🛑 No size reduction")

if __name__ == "__main__":
    optimize_gif(INPUT_GIF, OUTPUT_GIF, FINAL_WIDTH)
