import os
from PIL import Image
import random
from generate_frogs import generate_frog, randomly_flip_frog

def create_scene(scene_num, frogs_range, output_folder, backgrounds_folder, zone_restriction):
    # Load background images
    backgrounds = [os.path.join(backgrounds_folder, f) for f in os.listdir(backgrounds_folder) if f.endswith('.png')]
    background_image_path = random.choice(backgrounds)  # Randomly select a background
    background = Image.open(background_image_path)

    scene = Image.new('RGBA', (scene_width, scene_height), (255, 255, 255, 255))
    scene.paste(background, (0, 0))  # Paste the background onto the scene

    existing_frogs = []
    total_frogs = frogs_range[1] - frogs_range[0] + 1
    vertical_step = (zone_restriction[3] - zone_restriction[1]) / total_frogs

    for i in range(total_frogs):
        frog_image = generate_frog(i + start_frog_number)
        frog_image = randomly_flip_frog(frog_image)

        if frog_image:
            y = int(zone_restriction[1] + i * vertical_step)
            attempts = 0
            placed = False
            while not placed and attempts < 100:
                x = random.randint(zone_restriction[0], zone_restriction[2] - frog_image.width)
                new_frog_rect = (x, y, x + frog_image.width, y + frog_image.height)

                if not does_overlap(existing_frogs, new_frog_rect):
                    scene.paste(frog_image, (x, y), frog_image)
                    existing_frogs.append(new_frog_rect)
                    placed = True
                attempts += 1

    scene_path = os.path.join(output_folder, f"scene_{scene_num}.png")
    scene.save(scene_path, "PNG")
    print(f"Scene saved at {scene_path}")

if __name__ == "__main__":
    for scene_num in range(1, num_scenes + 1):
        create_scene(scene_num, (start_frog_number, end_frog_number), output_folder, backgrounds_folder, zone_restriction)
