# emojifier/emojify_image.py

import os
import json
import numpy as np
from PIL import Image, ImageOps
from scipy.spatial import KDTree

from emojifier.config import (
    EMOJI_FOLDER,
    EMOJI_COLOR_INDEX,
    OUTPUT_WIDTH_RANGE,
    ROWS_TO_COLUMNS,
    BACKGROUND_COLOR,
    TRIM_PIXELS,
    FINAL_SIZE
)

def load_color_index(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        emoji_colors = json.load(f)
    color_list = np.array(list(emoji_colors.values()))
    emoji_names = list(emoji_colors.keys())
    return KDTree(color_list), emoji_names, color_list

def emojify_image(input_path, output_path, output_width=None):
    img = Image.open(input_path).convert("RGB")

    if output_width is None:
        output_width = np.random.randint(*OUTPUT_WIDTH_RANGE)

    width, height = img.size
    aspect_ratio = height / width
    adjusted_height = int(aspect_ratio * output_width * ROWS_TO_COLUMNS)
    img = img.resize((output_width, adjusted_height))
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

    output_image = Image.new('RGBA', (output_width * emoji_size, adjusted_height * emoji_size), BACKGROUND_COLOR)

    for y in range(adjusted_height):
        for x in range(output_width):
            pixel_color = pixels[y, x]
            _, index = kd_tree.query(pixel_color)
            emoji_name = emoji_names[index]
            emoji_path = os.path.join(EMOJI_FOLDER, f"{emoji_name}.png")

            if not os.path.exists(emoji_path):
                continue

            emoji_img = Image.open(emoji_path).convert('RGBA')
            if TRIM_PIXELS > 0:
                emoji_img = emoji_img.crop((TRIM_PIXELS, TRIM_PIXELS, full_tile_size - TRIM_PIXELS, full_tile_size - TRIM_PIXELS))

            pos_x, pos_y = x * emoji_size, y * emoji_size
            output_image.paste(emoji_img, (pos_x, pos_y), emoji_img)

    output_image = ImageOps.fit(output_image, (output_width * emoji_size, adjusted_height * emoji_size), method=Image.Resampling.LANCZOS)
    output_image = output_image.resize(FINAL_SIZE, Image.Resampling.LANCZOS)
    output_image.save(output_path)
