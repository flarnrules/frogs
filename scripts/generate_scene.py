import os
from PIL import Image
import random
from generate_frogs import generate_frog, randomly_flip_frog

# Configuration
backgrounds = "../media/backgrounds"
zone_restriction = (10, 10, 86, 22) # relative to top left
scene_width = 192
scene_height = 64
start_frog_number = 1
end_frog_number = 3
num_scenes = 1
overlap_threshold = -2
max_frog_height = 5
output_folder = '../collections/3-frog_ponds/scenes'
os.makedirs(output_folder, exist_ok=True)

def does_overlap(existing_frogs, new_frog_rect, overlap_threshold):
    for rect in existing_frogs:
        # Check if new frog overlaps with existing frogs considering the overlap threshold
        if not (new_frog_rect[2] < rect[0] - overlap_threshold or
                new_frog_rect[0] > rect[2] + overlap_threshold or
                new_frog_rect[3] < rect[1] - overlap_threshold or
                new_frog_rect[1] > rect[3] + overlap_threshold):
            return True
    return False

def create_scene(scene_num, frogs_range, output_folder):
    #backgrounds = [os.path.join(backgrounds, f) for f in os.#listdir(backgrounds) if f.endswith('.png')]
    #background_image_path = random.choice(backgrounds)  # Randomly select a background
    #background = Image.open(background_image_path)
    
    scene = Image.new('RGBA', (scene_width, scene_height), (255, 255, 255, 255))
    #scene.paste(background, (0,0))

    existing_frogs = []

    total_frogs = frogs_range[1] - frogs_range[0] + 1
    # Adjust vertical step to ensure the last frog fits within the scene
    vertical_step = (scene_height - max_frog_height) / max(1, total_frogs - 1)

    for i in range(total_frogs):
        frog_image = generate_frog(i + start_frog_number)
        frog_image = randomly_flip_frog(frog_image)

        if frog_image:
            # Adjust the y position to ensure sequential placement from top, fitting within the scene
            y = min(int(i * vertical_step), scene_height - frog_image.height)

            placed = False
            attempts = 0
            while not placed and attempts < 100:
                x = random.randint(0, scene_width - frog_image.width)
                new_frog_rect = (x, y, x + frog_image.width, y + frog_image.height)

                if not does_overlap(existing_frogs, new_frog_rect,overlap_threshold):
                    scene.paste(frog_image, (x, y), frog_image)
                    existing_frogs.append(new_frog_rect)
                    placed = True
                attempts += 1

    scene_path = os.path.join(output_folder, f"scene_{scene_num}.png")
    scene.save(scene_path, "PNG")
    print(f"Scene {scene_num} saved at {scene_path}")

if __name__ == "__main__":
    for scene_num in range(1, num_scenes + 1):
        create_scene(scene_num, (start_frog_number, end_frog_number), output_folder)