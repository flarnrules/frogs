from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageOps
import numpy as np
import os
import json
import math
import random
from interior_mask import find_edge_points, approximate_interior_mask


# Configuration
input_files_location = "../frog_day/421-4200/cropped"
output_files_location = "../frog_day/nfts/images"
frame_directory = '../frog_day/picture_frames'
metadata_input_location = "../nfts/metadata"
metadata_output_location = "../frog_day/nfts/metadata"
file_types = ('.png',)  # Focus on PNG for this example

# Frame rarity mapping (example, adjust based on your actual frames and rarities)
frame_info = {
    "fancy wood.png":  {"rarity": 0.5, "inner_diameter": 990}, 
    "super_fancy.png":  {"rarity": 0.3, "inner_diameter": 900},
    "black_n_green.png": {"rarity": 3, "inner_diameter": 1017},
    "crystal_frame_circle.png": {"rarity": 0.1, "inner_diameter": 787},
    "fancy_circle.png": {"rarity": 0.2, "inner_diameter": 785},
    "flower_frame.png": {"rarity": 0.3, "inner_diameter": 646},
    "antique_circle.png": {"rarity": 1, "inner_diameter": 802},
    "gold.png": {"rarity": 0.1, "inner_diameter": 862},
    "green_n_red_stars.png": {"rarity": 2, "inner_diameter": 877},
    "kinda_gross.png": {"rarity": 2, "inner_diameter": 925},
    "simple_dark_circle.png": {"rarity": 1.5, "inner_diameter": 916},
    "trash.png": {"rarity": 2.5, "inner_diameter": 810},
    "wooden_circle.png": {"rarity": 0.52, "inner_diameter": 952},
    "gold_leaf_circle.png": {"rarity": 0.12, "inner_diameter": 1005},
    "cheap_frog_frame.png": {"rarity": 2.5, "inner_diameter": 750},
    "expensive_frog_frame_ai.png": {"rarity": 1.1, "inner_diameter": 610},
    "rustic_frog_frame_ai.png": {"rarity": 1, "inner_diameter": 660},
    "frogs_frame_ai.png": {"rarity": 1.1, "inner_diameter": 784},
    "boroque_frame_circle.png": {"rarity": 1.1, "inner_diameter": 693},
    "colorful_frogs_ai.png":{"rarity": 0.1, "inner_diameter": 766},
    "patinated_gold_leaf.png":{"rarity":2.3,"inner_diameter":810},
    "distressed_metal.png":{"rarity":3.3,"inner_diameter":1000},
    "beaded_ball_circle.png":{"rarity":1.3,"inner_diameter": 919},
    "moody_frame_ai.png":{"rarity":1.6,"inner_diameter":650}
}

# Adjusted select_frame Function to Use frame_info
def select_frame(nft_number):
    frames = list(frame_info.keys())
    rarities = [frame_info[frame]['rarity'] for frame in frames]
    total_rarity = sum(rarities)
    probabilities = [rarity / total_rarity for rarity in rarities]
    selected_frame = random.choices(frames, weights=probabilities, k=1)[0]
    return selected_frame

def fit_image_to_frame(processed_image, frame_path, inner_diameter):
    frame = Image.open(frame_path).convert("RGBA")
    frame_width, frame_height = frame.size

    # Calculate the scaling factor needed for the image to fit within the frame's inner diameter
    image_width, image_height = processed_image.size
    scale_factor = min(inner_diameter / image_width, inner_diameter / image_height)

    # If scaling factor is less than 1, resize the image to fit within the inner diameter
    if scale_factor < 1:
        new_image_size = (int(image_width * scale_factor), int(image_height * scale_factor))
        processed_image = processed_image.resize(new_image_size, Image.Resampling.LANCZOS)

    # Create a composite image with the same size as the frame
    composite_image = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))

    # Calculate position to center the processed image within the frame
    x = (frame_width - processed_image.width) // 2
    y = (frame_height - processed_image.height) // 2

    # Paste the processed image onto the composite image
    # This step ensures that the image does not extend outside the frame
    composite_image.paste(processed_image, (x, y), processed_image)

    # Overlay the frame onto the composite image
    composite_image.paste(frame, (0, 0), frame)

    # The composite_image now contains the processed image within the frame,
    # ensuring no part of the image extends outside the frame's boundaries.
    return composite_image


def add_noise(image, level=8):
    """
    Adds grain/noise to the image.
    """
    np_image = np.array(image)
    noise = np.random.randint(-level, level, np_image.shape, dtype='int16')
    np_image = np.clip(np_image + noise, 0, 255).astype('uint8')
    noisy_image = Image.fromarray(np_image)
    return noisy_image

def fade_edges_to_color_corrected(image, fade_color=(255, 239, 213), fade_intensity=0.05):
    """
    applies a fading effect to the edges, turning them to a specified color.
    """
    width, height = image.size
    mask = Image.new("L", (width, height), 0)  # Black mask = fully transparent
    draw = ImageDraw.Draw(mask)

    fade_boundary = int(min(width, height) * fade_intensity)
    for x in range(width):
        for y in range(height):
            distance_to_edge = min(x, y, width-x-1, height-y-1)
            if distance_to_edge < fade_boundary:
                opacity = 255 - int((distance_to_edge / fade_boundary) * 255)
                mask.putpixel((x, y), opacity)

    mask = mask.filter(ImageFilter.GaussianBlur(radius=fade_boundary // .85))
    fade_overlay = Image.new("RGB", (width, height), fade_color)
    fade_overlay.putalpha(mask)
    faded_image = Image.alpha_composite(image.convert("RGBA"), fade_overlay)

    return faded_image

def calculate_interior_mask(frame_path):
    frame = Image.open(frame_path).convert("RGBA")
    center = (frame.width // 2, frame.height // 2)
    angles = range(0, 360, 10)

    edge_points = find_edge_points(frame, center, angles) #from interior_mask.py
    mask = approximate_interior_mask(frame, edge_points) #from interior_mask.py

    return mask #used in delete_pixels function

def delete_pixels(processed_image, frame_path):
    frame = Image.open(frame_path).convert("RGBA")
    interior_mask = calculate_interior_mask(frame_path)  # Calculate the interior mask
    interior_mask_pixels = interior_mask.load()

    frame_pixels = frame.load()
    processed_pixels = processed_image.load()
    width, height = processed_image.size

    for x in range(width):
        for y in range(height):
            # if the pixel is outside the interior mask (mask pixel is 0) and the frame pixel is transparent
            if interior_mask_pixels[x, y] == 0 and frame_pixels[x, y][3] == 0:
                # Delete the pixel in the processed image by setting it to fully transparent
                processed_pixels[x, y] = (0, 0, 0, 0)

    return processed_image

def add_blue_exterior(image, mask):
    pixels = image.load()
    width, height = image.size

    # Iterate through each pixel and set to blue if it's outside the mask
    for x in range(width):
        for y in range(height):
            if mask.getpixel((x, y)) == 0:
                pixels[x, y] = (0, 0, 255, 255)  # Set pixel to blue

    return image

def update_metadata_with_frame(nft_number, frame_name):
    """
    Loads existing metadata from a JSON file, adds the frame trait, and saves the updated metadata.
    """
    metadata_input_path = os.path.join(metadata_input_location, f"{nft_number}.json")
    metadata_output_path = os.path.join(metadata_output_location, f"{nft_number}.json")
    
    with open(metadata_input_path, 'r') as f:
        metadata = json.load(f)

    # Check if the "Frame" trait already exists and update it; otherwise, add it
    frame_trait_exists = False
    for attribute in metadata.get("attributes", []):
        if attribute["trait_type"] == "Frame":
            attribute["value"] = frame_name
            frame_trait_exists = True
            break
    
    if not frame_trait_exists:
        metadata.setdefault("attributes", []).append({"trait_type": "Frame", "value": frame_name})
    
    # Save the updated metadata to the output location
    with open(metadata_output_path, 'w') as f:
        json.dump(metadata, f, indent=4)




def process_image_and_metadata(input_path, output_path, nft_number):
    original_image = Image.open(input_path).convert("RGBA")
    noisy_image = add_noise(original_image, level=18)
    faded_image = fade_edges_to_color_corrected(noisy_image)
    
    selected_frame = select_frame(nft_number)  # Select the frame filename
    frame_path = os.path.join(frame_directory, selected_frame)
    inner_diameter = frame_info[selected_frame]["inner_diameter"]
    
    # Check if the selected frame is circular
    if selected_frame.endswith("_circle.png"):
        # Fit image to frame
        processed_image = fit_image_to_frame(faded_image, frame_path, inner_diameter)
        
        # Delete pixels outside the frame's interior, preserving the interior
        processed_image = delete_pixels(processed_image, frame_path)
    else:
        # For non-circular frames, proceed without masking
        processed_image = fit_image_to_frame(faded_image, frame_path, inner_diameter)
    
    # Additional processing steps can be added here
    
    # Save the final image with the frame and deleted pixels
    processed_image.save(output_path, "PNG")
    
    frame_name = os.path.basename(frame_path).split('.')[0]
    update_metadata_with_frame(nft_number, frame_name)

# Processing Images and Updating Metadata
for filename in sorted(os.listdir(input_files_location)):
    if filename.endswith(tuple(file_types)):
        nft_number = int(filename.split('.')[0])  # Assuming filename format "<number>.png"
        input_path = os.path.join(input_files_location, filename)
        output_path = os.path.join(output_files_location, filename)
        
        process_image_and_metadata(input_path, output_path, nft_number)
        print(f"Processed {filename} and saved with frame and deleted pixels if circular.")