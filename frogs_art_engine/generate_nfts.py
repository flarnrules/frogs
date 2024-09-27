import os
import json
import random
import sys
import subprocess

from code.scripts.utils import load_config, select_trait, format_trait_name
from code.scripts.generate_image import generate_image
from code.scripts.generate_metadata import generate_metadata

def get_available_layers(layers_path):
    available_layers = []
    for root, dirs, files in os.walk(layers_path):
        if root == layers_path:
            continue
        if any(file.endswith(('.png', '.jpg', '.jpeg')) for file in files):
            layer_name = os.path.relpath(root, layers_path).replace('\\', '/')
            available_layers.append(layer_name)
    return available_layers

def setup_layer_order(layers_path, config):
    # Check if layers_order is specified in config.json
    layers_order = config.get('layers_order', None)
    if layers_order:
        return layers_order

    # If not specified, retrieve available layers
    available_layers = get_available_layers(layers_path)

    if not available_layers:
        print("No layers found in the specified layers path.")
        sys.exit(1)

    print("Available layers:")
    for idx, layer in enumerate(available_layers):
        print(f"{idx + 1}: {layer}")

    # Prompt the user to specify the layer order
    print("\nSpecify the layer order by entering the numbers separated by commas.")
    print("For example, to use the order 'background', 'character', 'object', enter: 1,2,3")
    print("Press Enter to use the default order.")
    
    user_input = input("Layer order: ").strip()
    if user_input:
        try:
            indices = [int(x.strip()) - 1 for x in user_input.split(',')]
            layers_order = [available_layers[i] for i in indices]
        except (ValueError, IndexError):
            print("Invalid input. Using default order.")
            layers_order = available_layers
    else:
        layers_order = available_layers

    print(f"Using layer order: {layers_order}")
    return layers_order

def main():
    # Load configurations
    config = load_config('config.json')

    start_nft_number = config['nft_start_number']
    end_nft_number = config['nft_end_number']
    output_images_path = config['output_images_path']
    output_metadata_path = config['output_metadata_path']
    layers_path = config['layers_path']

    # Ensure output directories exist
    os.makedirs(output_images_path, exist_ok=True)
    os.makedirs(output_metadata_path, exist_ok=True)

    # Automatically run rarities.py
    rarities_script_path = os.path.join('code', 'scripts', 'rarities.py')
    subprocess.run(['python', rarities_script_path], check=True)

    # Load rarities data
    rarities_path = os.path.join('code', 'data', 'rarities.json')
    if not os.path.exists(rarities_path):
        print(f"rarities.json not found at {rarities_path}. Please check for errors.")
        sys.exit(1)
    with open(rarities_path, 'r') as f:
        rarities = json.load(f)

    # Get or set up layers order
    layers_order = setup_layer_order(layers_path, config)

    # Validate layers in layers_order
    valid_layers_order = []
    for layer in layers_order:
        layer_path = os.path.join(layers_path, layer)
        if not os.path.isdir(layer_path):
            print(f"Layer '{layer}' does not exist in '{layers_path}'. Removing from layers_order.")
        else:
            valid_layers_order.append(layer)
    layers_order = valid_layers_order

    if not layers_order:
        print("No valid layers to process. Exiting.")
        sys.exit(1)

    for image_number in range(start_nft_number, end_nft_number + 1):
        traits = {}

        for layer in layers_order:
            layer_rarity = rarities.get(layer, {})
            if not layer_rarity:
                print(f"No rarities found for layer '{layer}'. Skipping this layer.")
                continue
            trait = select_trait(layer_rarity)
            if trait is None:
                print(f"No trait selected for layer '{layer}'. Skipping this layer.")
                continue
            traits[layer] = trait

            # Handle trait-specific layers
            trait_name = os.path.splitext(trait)[0].replace(' ', '_')
            trait_specific_layer_path = os.path.join(layers_path, layer, f"{trait_name}_layers")
            if os.path.isdir(trait_specific_layer_path):
                # Get sub-layers
                sub_layers = [d for d in os.listdir(trait_specific_layer_path)
                              if os.path.isdir(os.path.join(trait_specific_layer_path, d))]
                for sub_layer in sub_layers:
                    sub_layer_full_name = os.path.join(layer, f"{trait_name}_layers", sub_layer)
                    sub_layer_rarity = rarities.get(sub_layer_full_name, {})
                    if not sub_layer_rarity:
                        print(f"No rarities found for sub-layer '{sub_layer_full_name}'. Skipping.")
                        continue
                    sub_trait = select_trait(sub_layer_rarity)
                    if sub_trait is None:
                        print(f"No trait selected for sub-layer '{sub_layer_full_name}'. Skipping.")
                        continue
                    traits[sub_layer_full_name] = sub_trait

        if not traits:
            print(f"No traits selected for NFT #{image_number}. Skipping generation.")
            continue

        # Generate image
        final_image = generate_image(traits, config)
        final_image_path = os.path.join(output_images_path, f"{image_number}.png")
        final_image.save(final_image_path)

        # Generate metadata
        metadata = generate_metadata(image_number, traits, config)
        metadata_path = os.path.join(output_metadata_path, f"{image_number}.json")
        with open(metadata_path, 'w') as metafile:
            json.dump(metadata, metafile, indent=4)

        print(f"Generated NFT #{image_number} with image {final_image_path} and metadata.")

if __name__ == '__main__':
    main()
