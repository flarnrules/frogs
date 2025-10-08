# create_mp4.py
from typing import Optional, Tuple
from moviepy.editor import VideoFileClip, CompositeVideoClip, ColorClip

def gif_to_mp4(
    input_path: str,
    output_path: str,
    crf: int = 20,
    fps: Optional[int] = None,
    preset: str = "medium",
    bg_color: Optional[Tuple[int, int, int]] = (0, 0, 0),  # used for transparency & padding
    even_strategy: str = "pad",  # "pad" (add 1px) or "shrink" (remove 1px)
):
    """
    Convert a GIF to MP4 (H.264) without changing aspect ratio.
      - Flattens transparency over bg_color if the GIF has a mask.
      - Ensures even dimensions required by x264/yuv420p via pad (default) or shrink.
      - Strips any alpha channel from frames for safety.
    """
    clip = VideoFileClip(input_path)

    # If GIF has transparency, composite over a solid background.
    if clip.mask is not None:
        color = bg_color if bg_color is not None else (0, 0, 0)
        bg = ColorClip(size=(clip.w, clip.h), color=color).set_duration(clip.duration)
        clip = CompositeVideoClip([bg, clip])

    # Ensure frames are 3-channel RGB (drop alpha if present).
    # This is cheap and safe; if frames are already RGB it’s a no-op.
    clip = clip.fl_image(lambda f: f[..., :3])

    # Make dimensions even (required by yuv420p), preserving aspect ratio.
    need_w = clip.w % 2
    need_h = clip.h % 2
    if need_w or need_h:
        if even_strategy == "pad":
            new_w = clip.w + need_w
            new_h = clip.h + need_h
            color = bg_color if bg_color is not None else (0, 0, 0)
            clip = clip.on_color(size=(new_w, new_h), color=color, pos=("center", "center"))
        else:
            new_w = clip.w - need_w
            new_h = clip.h - need_h
            clip = clip.resize(newsize=(new_w, new_h))

    # FPS: preserve if known; otherwise default to 30 unless specified.
    fps_out = fps if fps is not None else getattr(clip, "fps", 30)

    ffmpeg_params = [
        "-movflags", "+faststart",
        "-pix_fmt", "yuv420p",
        "-crf", str(crf),
    ]

    clip.write_videofile(
        output_path,
        codec="libx264",
        audio=False,
        preset=preset,
        fps=fps_out,
        ffmpeg_params=ffmpeg_params,
    )
    clip.close()


if __name__ == "__main__":
    gif_to_mp4(
        input_path="outputs/all_is_waves_emoji_collage_fullsize.gif",
        output_path="outputs/all_is_waves.mp4",
        crf=20,
        fps=None,            # keep source timing if available
        preset="medium",
        bg_color=(0, 0, 0),  # use (255,255,255) for white; None -> black default
        even_strategy="pad", # add 1px where needed (no scaling)
    )
