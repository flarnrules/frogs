import os
import random
import json
from PIL import Image

# config
path_to_layers = '../layers/'
path_to_nfts_images = '../nfts/images/'
path_to_nfts_metadata = '../nfts/metadata/'
start_nft_number = 101
end_nft_number = 420

# check if directories exist
os.makedirs(path_to_nfts_images, exist_ok=True)
os.makedirs(path_to_nfts_metadata, exist_ok=True)

# load rarities data from rarities.json file
with open('../data/rarities.json') as infile:
    rarities = json.load(infile)

# select trait weighted rarities
def select_trait(trait_rarities):
    traits, weights = zip(*trait_rarities.items())
    return random.choices(traits, weights, k=1)[0]

def generate_image_and_metadata(image_number):
    selected_traits = {}
    final_image = Image.new('RGBA', (1024, 1024))  # scales up the image
    final_image_path = os.path.join(path_to_nfts_images, f"{image_number}.png")

    # fly emojis
    flies_emoji_map = {
        "0.png": "",
        "1.png": " 🪰 ",
        "2.png": " 🪰 🪰 ",
        "3.png": " 🪰 🪰 🪰 ",
        "4.png": " 🪰 🪰 🪰 🪰  ",
        "6.png": " 🪰 🪰 🪰 🪰 🪰 🪰 ",
        "7.png": " 🪰 🪰 🪰 🪰 🪰 🪰 🪰 ",
        "8.png": " 🪰 🪰 🪰 🪰 🪰 🪰 🪰 🪰 ",
    }

    layer_order = [
        'background', 'water', 'perch', 'features', 'frog', 'headgear',
        'eyes', 'mouth', 'accessory', 'flies',
    ]

    for layer in layer_order:
        trait = select_trait(rarities.get(layer, {}))
        if trait:
            trait_path = os.path.join(path_to_layers, layer, trait)
            if os.path.exists(trait_path):
                trait_image = Image.open(trait_path).convert('RGBA')
                trait_image = trait_image.resize((1024, 1024), Image.NEAREST)
                final_image.paste(trait_image, (0, 0), trait_image)
            selected_traits[layer] = trait

    # generate attributes for metadata
    attributes = [
        {"trait_type": "type", "value": "generated"},
        {"trait_type": "frames", "value": 1}
    ]

    for key, value in selected_traits.items():
        if key == 'flies':
            # uses flies emoji map from above
            attributes.append({"trait_type": key, "value": flies_emoji_map.get(value, "")})
        else:
            attributes.append({"trait_type": key, "value": value.split('.')[0]})

    # generate and save metadata
    metadata = {
        "name": f"Frog {image_number}",
        "description": "Eclectic frogs inspired by the infamous Frogstar from the Smoker's Club.",
        "attributes": attributes
    }

    with open(os.path.join(path_to_nfts_metadata, f"{image_number}.json"), 'w') as metafile:
        json.dump(metadata, metafile, indent=4)

    final_image.save(final_image_path)

    print(f"Generated NFT #{image_number} with image {final_image_path} and metadata.")



# runs the loop
for i in range(start_nft_number, end_nft_number + 1):
    generate_image_and_metadata(i)