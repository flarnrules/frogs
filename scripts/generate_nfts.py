import os
import random
import json
from PIL import Image

# Configuration
path_to_layers = '../layers/'
path_to_nfts_images = '../nfts/images/'
path_to_nfts_metadata = '../nfts/metadata/'
number_of_images = 300

# Ensure output directories exist
os.makedirs(path_to_nfts_images, exist_ok=True)
os.makedirs(path_to_nfts_metadata, exist_ok=True)

# Load rarities data
with open('../data/rarities.json') as infile:
    rarities = json.load(infile)

# Select a trait based on rarity
def select_trait(trait_rarities):
    traits, weights = zip(*trait_rarities.items())
    return random.choices(traits, weights, k=1)[0]

# Simplified function to generate the image and metadata
def generate_image_and_metadata(image_number):
    selected_traits = {}
    final_image = Image.new('RGBA', (1024, 1024))  # Final image size set to 1024x1024
    
    # Predefined layer order
    layer_order = [
        'background', 
        'water', 
        'perch', 
        'features', 
        'frog', 
        'headgear',
        'eyes', 
        'mouth',
        'accessory', 
        'flies', 
    ]
    
    # Iterate over layers and compose the final image
    for layer in layer_order:
        trait = select_trait(rarities.get(layer, {}))
        if trait:  # Only proceed if a trait was selected
            trait_path = os.path.join(path_to_layers, layer, trait)
            if os.path.exists(trait_path):
                trait_image = Image.open(trait_path).convert('RGBA')
                trait_image = trait_image.resize((1024, 1024), Image.NEAREST)  # Resize using nearest neighbor algorithm
                final_image.paste(trait_image, (0, 0), trait_image)
            selected_traits[layer] = trait

    # Save the final image
    final_image_path = os.path.join(path_to_nfts_images, f"{image_number}.png")
    final_image.save(final_image_path)
    
    # Generate and save metadata
    metadata = {
        "name": f"Frog {image_number}",
        "description": "Frogs inspired by the infamous Frogstar from the Smoker's Club.",
        "attributes": [{ "trait_type": key, "value": value.split('.')[0] } for key, value in selected_traits.items()]
    }
    with open(os.path.join(path_to_nfts_metadata, f"{image_number}.json"), 'w') as metafile:
        json.dump(metadata, metafile, indent=4)
    
    print(f"Generated NFT #{image_number} with image {final_image_path} and metadata.")

# Main loop to generate the specified number of images and metadata
for i in range(1, number_of_images + 1):
    generate_image_and_metadata(i)
