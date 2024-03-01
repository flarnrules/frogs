from PIL import Image, ImageSequence
import os

# Configuration
input_files_location = "../frog_pfps/full_size_gifs"
output_files_location = "../frog_pfps/cropped_gifs"
file_types = ('.gif',)  # Focus on GIF for this example

def process_gif(input_path, output_path):
    # Open the source GIF
    with Image.open(input_path) as src:
        frames = []  # To hold processed frames
        
        original_grid_size = 32
        final_grid_size = 16
        cell_size = src.size[0] // original_grid_size  # Assuming src.size[0] == src.size[1] == 1024
        
        # Calculate new dimensions after cropping
        cropped_width_cells = original_grid_size - 3 - 13  # Remove columns
        cropped_height_cells = original_grid_size - 5 - 11  # Remove rows
        
        # Calculate pixel dimensions for cropping
        crop_left = 3 * cell_size
        crop_top = 5 * cell_size
        crop_right = crop_left + cropped_width_cells * cell_size
        crop_bottom = crop_top + cropped_height_cells * cell_size
        
        # Process each frame
        for frame in ImageSequence.Iterator(src):
            # Crop
            cropped_frame = frame.crop((crop_left, crop_top, crop_right, crop_bottom))
            # Resize to 16x16 grid
            resized_frame = cropped_frame.resize((final_grid_size * cell_size, final_grid_size * cell_size), Image.NEAREST)
            # Then resize back to 1024x1024
            final_frame = resized_frame.resize((1024, 1024), Image.NEAREST)
            frames.append(final_frame)
        
        # Save processed frames as a new GIF
        frames[0].save(output_path, save_all=True, append_images=frames[1:], loop=0, duration=src.info['duration'], disposal=2)

# Process all GIF files
for filename in os.listdir(input_files_location):
    if filename.endswith(file_types):
        input_path = os.path.join(input_files_location, filename)
        output_path = os.path.join(output_files_location, filename)
        process_gif(input_path, output_path)
        print(f"Processed {filename} and saved to {output_files_location}")
