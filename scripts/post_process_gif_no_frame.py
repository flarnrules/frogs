from PIL import Image, ImageDraw, ImageFilter, ImageSequence
import numpy as np
import os

# config
input_files_location = "../collections/house"
output_files_location = "../collections/house/processed"
file_types = ('.gif',)

def add_noise(image, level=5):
    """
    Adds grain/noise to a single frame
    """
    np_image = np.array(image)
    noise = np.random.randint(-level, level, np_image.shape, dtype='int16')
    np_image = np.clip(np_image + noise, 0, 255).astype('uint8')
    noisy_frame = Image.fromarray(np_image)
    return noisy_frame

def fade_edges_to_color_corrected(image, fade_color=(255, 239, 213), fade_intensity=0.05):
    """
    Applies a fading effect to the edges, turning them to a specified color called 'fade_color' above
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

    mask = mask.filter(ImageFilter.GaussianBlur(radius=fade_boundary // 0.85))
    fade_overlay = Image.new("RGB", (width, height), fade_color)
    fade_overlay.putalpha(mask)
    faded_image = Image.alpha_composite(image.convert("RGBA"), fade_overlay)

    return faded_image

def process_gif(input_path, output_path):
    """
    Processes each frame of the GIF: adds noise and applies fading effect.
    """
    with Image.open(input_path) as gif:
        frames = []
        for frame in ImageSequence.Iterator(gif):
            frame = frame.convert("RGBA")
            
            # Apply noise
            frame_with_noise = add_noise(frame, level=15)
            
            # Apply fading to edges with the specified color
            frame_with_fade = fade_edges_to_color_corrected(frame_with_noise)
            
            # Convert back to P mode for GIF saving
            frame_with_fade = frame_with_fade.convert("P", palette=Image.ADAPTIVE, dither=None)
            
            frames.append(frame_with_fade)

        # Save processed frames as a new GIF
        frames[0].save(output_path, save_all=True, append_images=frames[1:], loop=0, duration=gif.info['duration'], transparency=0, dispose="background")

# Process all GIF files
for filename in os.listdir(input_files_location):
    if filename.endswith(file_types):
        input_path = os.path.join(input_files_location, filename)
        output_path = os.path.join(output_files_location, "processed_" + filename)  # To ensure unique output filename
        process_gif(input_path, output_path)
        print(f"Processed {filename} and saved to {output_files_location}")
