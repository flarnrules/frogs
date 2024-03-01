from PIL import Image
import os

# Configuration
input_files_location = "../frog_day/421-4200/images"
output_files_location = "../frog_day/421-4200/cropped"
file_types = ('.png',)  

# Configurable number of rows/columns to remove

remove_top_rows = 4*32
remove_bottom_rows = 7*32
remove_left_columns = 1*32
remove_right_columns = 10*32

# Upscale size
upscale_size = (1024, 1024)

# Processing function
def process_image(input_path, output_path):
    original_image = Image.open(input_path)
    width, height = original_image.size

    # Calculate the crop box coordinates
    left = remove_left_columns
    top = remove_top_rows
    right = width - remove_right_columns
    bottom = height - remove_bottom_rows

    # Crop the image
    cropped_image = original_image.crop((left, top, right, bottom))

    # Upscale the cropped image
    upscaled_image = cropped_image.resize(upscale_size, Image.NEAREST)

    # Save the upscaled image
    upscaled_image.save(output_path)

# Process all files
for filename in os.listdir(input_files_location):
    if filename.endswith(file_types):
        input_path = os.path.join(input_files_location, filename)
        output_path = os.path.join(output_files_location, filename)
        process_image(input_path, output_path)
        print(f"Processed {filename} and saved to {output_files_location}")
