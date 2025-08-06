# emojifier/emojify_image.py

import os
import json
import numpy as np
from PIL import Image, ImageOps
from scipy.spatial import KDTree

from config.config import (
    EMOJI_FOLDER,
    EMOJI_COLOR_INDEX,
    OUTPUT_WIDTH,
    BACKGROUND_COLOR,
    TRIM_PIXELS,
    FINAL_SIZE
)

from utils.image_utils import get_resized_dimensions

def load_color_index(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        emoji_colors = json.load(f)
    color_list = np.array(list(emoji_colors.values()))
    emoji_names = list(emoji_colors.keys())
    return KDTree(color_list), emoji_names, color_list

def emojify_image(input_path, output_path, output_width=None):
    if output_width is None:
        output_width = OUTPUT_WIDTH

    verbose = True if os.environ.get("GIF_FRAME_MODE") != "1" else False
    resized_width, resized_height = get_resized_dimensions(input_path, output_width, verbose=verbose)

    img = Image.open(input_path).convert("RGB")
    img = img.resize((resized_width, resized_height))
    pixels = np.array(img)

    kd_tree, emoji_names, color_list = load_color_index(EMOJI_COLOR_INDEX)

    # Find sample emoji tile size
    sample_path = next(
        (os.path.join(EMOJI_FOLDER, f"{name}.png") for name in emoji_names if os.path.exists(os.path.join(EMOJI_FOLDER, f"{name}.png"))),
        None
    )
    if sample_path is None:
        raise FileNotFoundError("No emoji images found in folder.")

    full_tile_size = Image.open(sample_path).size[0]
    emoji_size = full_tile_size - (2 * TRIM_PIXELS)

    output_image = Image.new('RGBA', (resized_width * emoji_size, resized_height * emoji_size), BACKGROUND_COLOR)

    # 🔥 Cache for opened and cropped emoji images
    emoji_cache = {}

    for y in range(resized_height):
        for x in range(resized_width):
            pixel_color = pixels[y, x]
            _, index = kd_tree.query(pixel_color)
            emoji_name = emoji_names[index]
            emoji_path = os.path.join(EMOJI_FOLDER, f"{emoji_name}.png")

            if not os.path.exists(emoji_path):
                continue

            if emoji_name in emoji_cache:
                emoji_img = emoji_cache[emoji_name]
            else:
                emoji_img = Image.open(emoji_path).convert('RGBA')
                if TRIM_PIXELS > 0:
                    emoji_img = emoji_img.crop((TRIM_PIXELS, TRIM_PIXELS, full_tile_size - TRIM_PIXELS, full_tile_size - TRIM_PIXELS))
                emoji_cache[emoji_name] = emoji_img

            pos_x, pos_y = x * emoji_size, y * emoji_size
            output_image.paste(emoji_img, (pos_x, pos_y), emoji_img)

    if FINAL_SIZE:
        target_width = FINAL_SIZE[0]
        scale_factor = target_width / (resized_width * emoji_size)
        new_size = (
            int(resized_width * emoji_size * scale_factor),
            int(resized_height * emoji_size * scale_factor)
        )
        output_image = output_image.resize(new_size, Image.Resampling.LANCZOS)

    output_image.save(output_path)
