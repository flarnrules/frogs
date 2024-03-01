from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import os

# Configuration
input_files_location = "../frog_pfps/preprocess"
output_files_location = "../frog_pfps/postprocess2"
file_types = ('.png',)  # Focus on PNG for this example

def add_noise(image, level=5):
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
    Correctly applies a fading effect to the edges, turning them to a specified color.
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

def process_and_apply_filters(input_path, output_path):
    """
    Processes the image by adding noise and fading the edges.
    """
    original_image = Image.open(input_path).convert("RGBA")
    
    # Add noise
    noisy_image = add_noise(original_image, level=15)

    # Fade edges
    final_image = fade_edges_to_color_corrected(noisy_image)

    final_image.save(output_path, "PNG")

# Process all files
for filename in os.listdir(input_files_location):
    if filename.endswith(file_types):
        input_path = os.path.join(input_files_location, filename)
        output_path = os.path.join(output_files_location, filename)
        process_and_apply_filters(input_path, output_path)
        print(f"Processed {filename} with noise and faded edges, saved to {output_files_location}")
