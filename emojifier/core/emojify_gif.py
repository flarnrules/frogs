# emojifier/emojify_gif.py

import os
import time
from PIL import Image, ImageSequence
import tempfile
from core.emojify_image import emojify_image

def emojify_gif(input_gif_path, output_gif_path):
    print(f"🚀 Starting emojification of GIF: {input_gif_path}")
    start_time = time.time()

    with tempfile.TemporaryDirectory() as temp_dir:
        frames = []

        with Image.open(input_gif_path) as gif:
            frame_durations = []
            total_frames = 0

            for i, frame in enumerate(ImageSequence.Iterator(gif)):
                total_frames += 1
                frame_path = os.path.join(temp_dir, f"frame_{i:03}.png")
                emojified_path = os.path.join(temp_dir, f"emojified_{i:03}.png")

                frame.convert("RGB").save(frame_path)
                emojify_image(frame_path, emojified_path)
                emojified_frame = Image.open(emojified_path).convert("RGBA")

                frames.append(emojified_frame)
                frame_durations.append(gif.info.get("duration", 100))

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
