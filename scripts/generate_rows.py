import os
from PIL import Image
import random
from generate_frogs import generate_frog, randomly_flip_frog
import math

# Config
scene_width = 96
scene_height = 32
num_frogs = 15
num_rows = 3
num_scenes = 1
output_folder = '../media/scenes'
os.makedirs(output_folder, exist_ok=True)

def create_scene(scene_num, frogs_range, output_folder):
    scene = Image.new('RGBA', (scene_width, scene_height), (255, 255, 255, 255))

    total_frogs = frogs_range[1] - frogs_range[0] + 1
    frogs_per_row = math.ceil(total_frogs / num_rows)
    row_height = scene_height / num_rows

    for i in range(total_frogs):
        frog_image = generate_frog(i + frogs_range[0])
        frog_image = randomly_flip_frog(frog_image)  # Flip the frog image randomly

        if frog_image:
            row_number = i // frogs_per_row
            # Adjust the y position for the bottom row
            y_adjustment = -5 if row_number == num_rows - 1 else 0  # Raise the bottom row by 5 pixels
            
            # Calculate y position based on row number with adjustment for the bottom row
            y = int(row_height * row_number + row_height / 2 - frog_image.height / 2 + y_adjustment)
            
            # Randomize x position within the row, ensuring frogs fit within the scene width
            x = random.randint(0, max(0, scene_width - frog_image.width))
            
            scene.paste(frog_image, (x, y), frog_image)

    scene_path = os.path.join(output_folder, f"scene_{scene_num}.png")
    scene.save(scene_path, "PNG")
    print(f"Scene {scene_num} saved at {scene_path}")

if __name__ == "__main__":
    start_frog_number = 1
    end_frog_number = num_frogs
    for scene_num in range(1, num_scenes + 1):
        create_scene(scene_num, (start_frog_number, end_frog_number), output_folder)