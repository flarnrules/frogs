import os
from PIL import Image
from .utils import format_trait_name

def generate_image(traits, config):
    image_size = tuple(config.get('image_size', [1024, 1024]))
    layers_path = config['layers_path']
    final_image = Image.new('RGBA', image_size)

    # Use the order of layers as keys to ensure correct stacking order
    layers_order = list(traits.keys())

    for layer_name in layers_order:
        trait_filename = traits[layer_name]
        if trait_filename == 'None':
            continue
        trait_path = os.path.join(layers_path, layer_name, trait_filename)
        if os.path.exists(trait_path):
            trait_image = Image.open(trait_path).convert('RGBA')
            trait_image = trait_image.resize(image_size, Image.NEAREST)
            final_image.paste(trait_image, (0, 0), trait_image)
        else:
            print(f"Trait image not found: {trait_path}")
    return final_image

