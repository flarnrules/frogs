import os
import math
import random
import numpy as np
from PIL import Image, ImageSequence

def add_noise(img, intensity=10):
    img = img.convert("RGB")
    arr = np.array(img, dtype=np.int16)
    noise = np.random.randint(-intensity, intensity + 1, arr.shape, dtype=np.int16)
    noisy_arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy_arr)

def chromatic_aberration(img, shift_r=(25, 0), shift_g=(0, 25), shift_b=(-25, 0),
                          jitter=False, aberration_strength=5):
    img = img.convert("RGB")
    arr = np.array(img)

    def shift_channel(channel, shift):
        return np.roll(np.roll(channel, shift[0], axis=0), shift[1], axis=1)

    if jitter:
        shift_r = (random.randint(-aberration_strength, aberration_strength),
                   random.randint(-aberration_strength, aberration_strength))
        shift_g = (random.randint(-aberration_strength, aberration_strength),
                   random.randint(-aberration_strength, aberration_strength))
        shift_b = (random.randint(-aberration_strength, aberration_strength),
                   random.randint(-aberration_strength, aberration_strength))

    r = shift_channel(arr[:, :, 0], shift_r)
    g = shift_channel(arr[:, :, 1], shift_g)
    b = shift_channel(arr[:, :, 2], shift_b)
    aberrated = np.stack((r, g, b), axis=2)
    return Image.fromarray(aberrated)

def resize_to_width(img, output_width):
    if output_width is None:
        return img
    w_percent = output_width / float(img.width)
    h_size = int((float(img.height) * w_percent))
    return img.resize((output_width, h_size), Image.LANCZOS)

def process_gif(input_path, output_path,
                shift_r=(1, 0), shift_g=(0, 1), shift_b=(-1, 0),
                jitter=False, aberration_strength=5,
                output_width=None, noise_intensity=0,
                dynamic_aberration=False):
    with Image.open(input_path) as im:
        frames = []
        durations = []
        total_frames = im.n_frames

        for idx, frame in enumerate(ImageSequence.Iterator(im)):
            frame = frame.copy().convert("RGB")

            if noise_intensity > 0:
                frame = add_noise(frame, noise_intensity)

            if dynamic_aberration:
                progress = idx / (total_frames - 1)
                # .3 - fast come up, slow ride down
                # .5 - symmetrical
                # .85 - gradual build, sharp fall
                # .95 - slow build, abrupt collapse
                rise_ratio = .5
                
                if progress < rise_ratio:
                    factor = (progress / rise_ratio) ** 2
                else:
                    fall_progress = (progress - rise_ratio) / (1 - rise_ratio)
                    factor = 1 - fall_progress
                factor = max(factor, 0)
                strength = int(aberration_strength * factor)
            else:
                strength = aberration_strength

            ab_img = chromatic_aberration(frame,
                                          shift_r=shift_r,
                                          shift_g=shift_g,
                                          shift_b=shift_b,
                                          jitter=jitter,
                                          aberration_strength=strength)

            ab_img = resize_to_width(ab_img, output_width)

            ab_img = ab_img.convert("RGBA").convert("P", palette=Image.ADAPTIVE)
            frames.append(ab_img)
            durations.append(frame.info.get("duration", 72))

        print(f"Writing {len(frames)} frames to {output_path}")
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            disposal=2,
            optimize=True
        )
        print("✅ Done.")

# INPUTS
input_gif = "all_is_waves_emoji.gif"
output_gif = "all_is_waves_emoji_glitch.gif"

process_gif(
    input_path=input_gif,
    output_path=output_gif,
    shift_r=(15, 0),
    shift_g=(0, 15),
    shift_b=(-15, 0),
    jitter=True,
    aberration_strength=25,
    output_width=1024,
    noise_intensity=55,
    dynamic_aberration=False
)
