import os
from PIL import Image
from .utils import format_trait_name

def generate_image(traits, config):
    image_size = tuple(config.get('image_size', [1024, 1024]))
    layers_path = config['layers_path']
    final_image = Image.new('RGBA', image_size, (0, 0, 0, 0))  # Transparent base

    # Use explicit order if defined, otherwise fallback to whatever trait keys exist
    layer_order = config.get('layers_order', list(traits.keys()))

    # Step 1: main layers in defined/fallback order
    for layer_name in layer_order:
        trait_filename = traits.get(layer_name)
        if not trait_filename or trait_filename == 'None':
            continue
        trait_path = os.path.join(layers_path, layer_name, trait_filename)
        if os.path.exists(trait_path):
            trait_image = Image.open(trait_path).convert('RGBA')
            trait_image = trait_image.resize(image_size, Image.NEAREST)
            final_image.paste(trait_image, (0, 0), trait_image)
        else:
            print(f"⚠️ Missing layer image: {trait_path}")

    # Step 2: additional sublayers (e.g. trait-specific folders)
    for layer_name, trait_filename in traits.items():
        if layer_name in layer_order:
            continue  # already pasted
        if not trait_filename or trait_filename == 'None':
            continue
        trait_path = os.path.join(layers_path, layer_name, trait_filename)
        if os.path.exists(trait_path):
            trait_image = Image.open(trait_path).convert('RGBA')
            trait_image = trait_image.resize(image_size, Image.NEAREST)
            final_image.paste(trait_image, (0, 0), trait_image)
        else:
            print(f"⚠️ Missing sublayer image: {trait_path}")

    return final_image
