import os
import random
import json
from PIL import Image

# config
path_to_layers = '../layers/'
path_to_frogs = '../collections/3-frog_ponds/frogs'
start_nft_number = 1
end_nft_number = 100

# check if directories exist
os.makedirs(path_to_frogs, exist_ok=True)

# load rarities data from rarities.json file
with open('../data/rarities.json') as infile:
    rarities = json.load(infile)

# select trait weighted rarities
def select_trait(trait_rarities):
    traits, weights = zip(*trait_rarities.items())
    return random.choices(traits, weights, k=1)[0]


def generate_frog(image_number):
    selected_traits = {}
    base_image = None  # Placeholder for the initial image layer

    layer_order = [
       'perch' ,'frog', 'accessory', 'headgear',
        'eyes', 'mouth',
    ]

    for layer in layer_order:
        trait = select_trait(rarities.get(layer, {}))
        if trait:
            # Ensure trait path is correct, and include the debugging print statement if the file doesn't exist
            trait_path = os.path.join(path_to_layers, layer, trait)
            if os.path.exists(trait_path):
                trait_image = Image.open(trait_path).convert('RGBA')
                if base_image:
                    base_image = Image.alpha_composite(base_image, trait_image)
                else:
                    base_image = trait_image  # Initialize base image if not already set
            else:
                # Print a message if the trait image file cannot be found
                print(f"Could not find trait image for {layer}: {trait_path}")
            selected_traits[layer] = trait

    if base_image:
        # Specify your crop area (left, top, right, bottom)
        crop_area = (1, 2, 22, 26)  # Adjust as needed
        cropped_image = base_image.crop(crop_area)

        return cropped_image

    else:
        print(f"Skipping frog #{image_number} due to missing layers.")
        return None

def randomly_flip_frog(frog_image):
    if random.choice([True, False]):  # 50/50 chance
        return frog_image.transpose(Image.FLIP_LEFT_RIGHT)
    else:
        return frog_image

# Generate frogs in a loop
for i in range(start_nft_number, end_nft_number + 1):
    generate_frog(i)