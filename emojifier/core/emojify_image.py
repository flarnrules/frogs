# emojifier/emojify_image.py

import os
import json
import numpy as np
from PIL import Image, ImageOps
from scipy.spatial import KDTree

from config import config

from utils.image_utils import get_resized_dimensions

# Toggle this to enable/disable debug output
DEBUG_UNDERLAYER = True

def load_color_index(index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        emoji_colors = json.load(f)
    color_list = np.array(list(emoji_colors.values()))
    emoji_names = list(emoji_colors.keys())
    return KDTree(color_list), emoji_names, color_list

def emojify_image(input_path, output_path, output_width=None):
    if output_width is None:
        output_width = config.OUTPUT_WIDTH

    verbose = True if os.environ.get("GIF_FRAME_MODE") != "1" else False
    resized_width, resized_height = get_resized_dimensions(input_path, output_width, verbose=verbose)

    # Load and resize with transparency preserved
    img = Image.open(input_path).convert("RGBA")
    img = img.resize((resized_width, resized_height), resample=Image.NEAREST)
    pixels = np.array(img)

    kd_tree, emoji_names, color_list = load_color_index(config.EMOJI_COLOR_INDEX)

    # Find sample emoji tile size
    sample_path = next(
        (os.path.join(config.EMOJI_FOLDER, f"{name}.png") for name in emoji_names if os.path.exists(os.path.join(config.EMOJI_FOLDER, f"{name}.png"))),
        None
    )
    if sample_path is None:
        raise FileNotFoundError("No emoji images found in folder.")

    full_tile_size = Image.open(sample_path).size[0]
    emoji_size = full_tile_size - (2 * config.TRIM_PIXELS)

    output_pixel_width = resized_width * emoji_size
    output_pixel_height = resized_height * emoji_size

    output_image = Image.new('RGBA', (output_pixel_width, output_pixel_height), config.BACKGROUND_COLOR)

    # Prepare debug and composite layers
    debug_underlayer = None
    composite_image = None
    if DEBUG_UNDERLAYER:
        debug_underlayer = Image.new('RGB', (output_pixel_width, output_pixel_height), (0, 0, 0))
        composite_image = Image.new('RGBA', (output_pixel_width, output_pixel_height), (0, 0, 0, 0))

    # 🔥 Cache for opened and cropped emoji images
    emoji_cache = {}

    for y in range(resized_height):
        for x in range(resized_width):
            r, g, b, a = pixels[y, x]

            if a == 0:
                continue  # skip fully transparent pixels

            pixel_color = (r, g, b)
            _, index = kd_tree.query(pixel_color)
            emoji_name = emoji_names[index]
            emoji_path = os.path.join(config.EMOJI_FOLDER, f"{emoji_name}.png")

            if not os.path.exists(emoji_path):
                continue

            if emoji_name in emoji_cache:
                emoji_img = emoji_cache[emoji_name]
            else:
                emoji_img = Image.open(emoji_path).convert('RGBA')
                if config.TRIM_PIXELS > 0:
                    emoji_img = emoji_img.crop((config.TRIM_PIXELS, config.TRIM_PIXELS, full_tile_size - config.TRIM_PIXELS, full_tile_size - config.TRIM_PIXELS))
                emoji_cache[emoji_name] = emoji_img

            pos_x, pos_y = x * emoji_size, y * emoji_size

            # Paste emoji into final output image
            output_image.paste(emoji_img, (pos_x, pos_y), emoji_img)

            # Paste debug color tile and build composite
            if DEBUG_UNDERLAYER:
                debug_tile = Image.new('RGB', (emoji_size, emoji_size), pixel_color)
                debug_underlayer.paste(debug_tile, (pos_x, pos_y))

                # Composite: color block underneath emoji
                base_tile = debug_tile.convert("RGBA")
                base_tile.paste(emoji_img, (0, 0), emoji_img)
                composite_image.paste(base_tile, (pos_x, pos_y))

    if config.FINAL_SIZE:
        target_width = config.FINAL_SIZE[0]
        scale_factor = target_width / (resized_width * emoji_size)
        new_size = (
            int(resized_width * emoji_size * scale_factor),
            int(resized_height * emoji_size * scale_factor)
        )
        print(f"[INFO] Final resized output size: {new_size[0]}x{new_size[1]} px")
        output_image = output_image.resize(new_size, Image.Resampling.LANCZOS)
        if DEBUG_UNDERLAYER:
            debug_underlayer = debug_underlayer.resize(new_size, Image.Resampling.NEAREST)
            composite_image = composite_image.resize(new_size, Image.Resampling.LANCZOS)
    else:
        print(f"[INFO] Output image not resized further (FINAL_SIZE is None)")

    print(f"[INFO] Using emoji tiles: {emoji_size}px each (trimmed from {full_tile_size}px)")
    output_image.save(output_path)

    if DEBUG_UNDERLAYER:
        underlayer_path = output_path.replace(".png", "_debug_underlayer.png")
        composite_path = output_path.replace(".png", "_composite.png")

        debug_underlayer.save(underlayer_path)
        print(f"[DEBUG] Saved underlayer to: {underlayer_path}")

        composite_image.save(composite_path)
        print(f"[DEBUG] Saved composite image to: {composite_path}")
