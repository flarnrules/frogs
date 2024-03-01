from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import os

# Configuration
input_files_location = "../frog_day/cropped_pngs"
output_files_location = "../frog_day/nfts/images"
frame_path = '../frog_day/picture_frames/fancy_wood.png'  # Path to the frame image
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

def place_image_behind_frame(processed_image, frame_path):
    """
    Places the processed image behind a frame.
    """
    frame = Image.open(frame_path).convert("RGBA")
    processed_image_width, processed_image_height = processed_image.size
    frame_width, frame_height = frame.size

    # Ensure the frame is larger; otherwise, resize or alert
    if processed_image_width > frame_width or processed_image_height > frame_height:
        print("Warning: Frame is smaller than the image. Image will be resized.")
        processed_image = processed_image.resize((frame_width, frame_height), Image.ANTIALIAS)

    # Calculate the position to center the processed image within the frame
    x = (frame_width - processed_image_width) // 2
    y = (frame_height - processed_image_height) // 2

    # Create a new image to composite the frame and the processed image
    composite_image = Image.new("RGBA", frame.size)
    composite_image.paste(processed_image, (x, y))
    composite_image.paste(frame, (0, 0), frame)

    return composite_image

def process_and_apply_filters(input_path, output_path, frame_path):
    """
    Processes the image by adding noise, fading the edges, and placing it behind a frame.
    """
    original_image = Image.open(input_path).convert("RGBA")
    
    # Add noise
    noisy_image = add_noise(original_image, level=15)

    # Fade edges
    faded_image = fade_edges_to_color_corrected(noisy_image)

    # Place behind frame
    final_image = place_image_behind_frame(faded_image, frame_path)

    final_image.save(output_path, "PNG")

# Process all files
for filename in os.listdir(input_files_location):
    if filename.endswith(file_types):
        input_path = os.path.join(input_files_location, filename)
        output_path = os.path.join(output_files_location, filename)
        process_and_apply_filters(input_path, output_path, frame_path)
        print(f"Processed {filename} with noise and faded edges, placed behind frame, saved to {output_files_location}")
