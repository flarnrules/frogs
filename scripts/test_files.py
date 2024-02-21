import shutil
import os

# Configuration
source_image_path = '../media/others/sample.png'
target_directory = '../tests/test2/images/'
number_of_images = 420

# Ensure target directory exists
os.makedirs(target_directory, exist_ok=True)

# Generate and save duplicates
for i in range(1, number_of_images + 1):
    target_image_path = os.path.join(target_directory, f"{i}.png")
    shutil.copy(source_image_path, target_image_path)
    print(f"Copied {target_image_path}")

print(f"Successfully generated {number_of_images} copies of the dummy image.")
