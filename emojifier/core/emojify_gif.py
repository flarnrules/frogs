# emojifier/emojify_gif.py
import os
import time
import tempfile
from PIL import Image, ImageSequence
from core.emojify_image import emojify_image
from config.config import OUTPUT_WIDTH

def emojify_gif(input_gif_path, output_gif_path):
    print(f"🚀 Starting emojification of GIF: {input_gif_path}")
    start_time = time.time()

    with tempfile.TemporaryDirectory() as temp_dir:
        frames = []

        with Image.open(input_gif_path) as gif:
            frame_durations = []
            total_frames = getattr(gif, "n_frames", 1)

            # ✅ Suppress verbose logging from get_resized_dimensions
            os.environ["GIF_FRAME_MODE"] = "1"

            for i, frame in enumerate(ImageSequence.Iterator(gif)):
                frame_start = time.time()
                print(f"\n🧱 Processing frame {i + 1}/{total_frames}...")

                frame_path = os.path.join(temp_dir, f"frame_{i:03}.png")
                emojified_path = os.path.join(temp_dir, f"emojified_{i:03}.png")

                frame.convert("RGB").save(frame_path)
                emojify_image(frame_path, emojified_path, output_width=OUTPUT_WIDTH)
                emojified_frame = Image.open(emojified_path).convert("RGBA")

                frames.append(emojified_frame)
                frame_durations.append(gif.info.get("duration", 100))

                frame_time = time.time() - frame_start
                remaining = total_frames - (i + 1)
                print(f"⏱️  Frame {i + 1} completed in {frame_time:.2f}s — {remaining} left")

            # ✅ Restore environment
            os.environ.pop("GIF_FRAME_MODE", None)

        frames[0].save(
            output_gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=frame_durations,
            loop=gif.info.get("loop", 0),
            disposal=2,
            optimize=True
        )

    elapsed = time.time() - start_time
    avg_time = elapsed / total_frames if total_frames > 0 else 0

    print("\n✅ Emojified GIF created:")
    print(f"📍 Output path: {output_gif_path}")
    print(f"🖼️  Total frames: {total_frames}")
    print(f"⏱️  Total time: {elapsed:.2f} sec")
    print(f"🧠 Avg time per frame: {avg_time:.2f} sec")
    print(f"🎥 Frame rate estimate: {1000 / frame_durations[0]:.2f} FPS (input)")
