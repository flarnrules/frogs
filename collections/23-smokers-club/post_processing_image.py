import os
import math
import random
import numpy as np
from PIL import Image

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

def create_gif_from_image(input_path, output_path,
                          shift_r=(1, 0), shift_g=(0, 1), shift_b=(-1, 0),
                          jitter=False, aberration_strength=5,
                          output_width=None, noise_intensity=0,
                          dynamic_aberration=False,
                          frame_count=30, duration=40):
    original = Image.open(input_path).convert("RGB")
    frames = []

    for idx in range(frame_count):
        frame = original.copy()

        if noise_intensity > 0:
            frame = add_noise(frame, noise_intensity)

        if dynamic_aberration:
            progress = idx / (frame_count - 1)
            rise_ratio = 0.5
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

    print(f"Writing {len(frames)} frames to {output_path}")
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        disposal=2,
        optimize=False
    )
    print("✅ Done.")

# INPUTS
input_image = "hatcoin-test.png"
output_gif = "hattab.gif"

create_gif_from_image(
    input_path=input_image,
    output_path=output_gif,
    shift_r=(10, 0),
    shift_g=(0, 10),
    shift_b=(-10, 0),
    jitter=True,
    aberration_strength=50,
    output_width=512,
    noise_intensity=0,
    dynamic_aberration=False,
    frame_count=24,
    duration=75
)
