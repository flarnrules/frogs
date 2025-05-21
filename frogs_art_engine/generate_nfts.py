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
    layers_order = config.get('layers_order', None)
    if layers_order:
        return layers_order

    available_layers = get_available_layers(layers_path)
    if not available_layers:
        print("No layers found in the specified layers path.")
        sys.exit(1)

    print("Available layers:")
    for idx, layer in enumerate(available_layers):
        print(f"{idx + 1}: {layer}")

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
    config = load_config('config.json')

    start_nft_number = config['nft_start_number']
    end_nft_number = config['nft_end_number']
    output_images_path = config['output_images_path']
    output_metadata_path = config['output_metadata_path']
    layers_path = config['layers_path']

    os.makedirs(output_images_path, exist_ok=True)
    os.makedirs(output_metadata_path, exist_ok=True)

    # Run rarities script
    rarities_script_path = os.path.join('code', 'scripts', 'rarities.py')
    subprocess.run(['python', rarities_script_path], check=True)

    # Load rarities
    with open(os.path.join('code', 'data', 'rarities.json'), 'r') as f:
        rarities = json.load(f)

    # Load trait rules
    rules_path = os.path.join('code', 'data', 'trait_rules.json')
    if os.path.exists(rules_path):
        with open(rules_path, 'r') as f:
            trait_rules = json.load(f)
    else:
        trait_rules = {}

    # Get layer order
    layers_order = setup_layer_order(layers_path, config)

    # Validate layer paths
    layers_order = [
        layer for layer in layers_order
        if os.path.isdir(os.path.join(layers_path, layer))
    ]
    if not layers_order:
        print("No valid layers to process. Exiting.")
        sys.exit(1)

    # Dynamically determine which layers define rules
    rule_layers = [
        layer for layer in sorted(set(os.path.dirname(k) for k in trait_rules.keys()))
        if layer in layers_order
    ]
    print(f"\n🔧 Dynamic rule-layers detected for prepass: {rule_layers}")

    for image_number in range(start_nft_number, end_nft_number + 1):
        traits = {}
        disallowed_by_layer = {}

        # --- PREPASS: select all rule-triggering layers first ---
        for rule_layer in rule_layers:
            disallowed = disallowed_by_layer.get(rule_layer, [])
            trait = select_trait(rarities.get(rule_layer, {}), disallowed_traits=disallowed)
            if not trait:
                print(f"No valid trait for rule-layer '{rule_layer}'. Skipping NFT.")
                continue

            traits[rule_layer] = trait

            full_path = os.path.join(layers_path, rule_layer, trait)
            layer_trait_key = os.path.relpath(full_path, start='media/layers').replace('\\', '/')

            print(f"\n[Rules Prepass] {rule_layer}/{trait} → {layer_trait_key}")
            rule = trait_rules.get(layer_trait_key)
            if rule and "disallow" in rule:
                for target_layer, disallowed_traits in rule["disallow"].items():
                    print(f"  🚫 Pre-disallowing in {target_layer}: {disallowed_traits}")
                    disallowed_by_layer.setdefault(target_layer, []).extend(disallowed_traits)

        # --- MAIN PASS: loop through the rest of the layers ---
        for layer in layers_order:
            if layer in traits:
                continue  # Already handled in prepass

            disallowed = disallowed_by_layer.get(layer, [])
            trait = select_trait(rarities.get(layer, {}), disallowed_traits=disallowed)
            if not trait:
                print(f"No valid trait for layer '{layer}' after applying disallowed list.")
                continue

            if trait in disallowed:
                print(f"  ❌ Selected disallowed trait '{trait}' in layer '{layer}' — logic error!")
            traits[layer] = trait

            full_path = os.path.join(layers_path, layer, trait)
            layer_trait_key = os.path.relpath(full_path, start='media/layers').replace('\\', '/')

            print(f"\nChecking for trait rule:")
            print(f"  Trait: {trait}")
            print(f"  Layer: {layer}")
            print(f"  Full path: {full_path}")
            print(f"  Rel key for rules: {layer_trait_key}")

            rule = trait_rules.get(layer_trait_key)
            if rule:
                print(f"  🔎 Rule found: {rule}")
                if "disallow" in rule:
                    for target_layer, disallowed_traits in rule["disallow"].items():
                        print(f"  🚫 Disallowing in layer '{target_layer}': {disallowed_traits}")
                        disallowed_by_layer.setdefault(target_layer, []).extend(disallowed_traits)
            else:
                print(f"  ⚠️ No rule matched for: {layer_trait_key}")

            # Trait-specific layers
            trait_name = os.path.splitext(trait)[0].replace(' ', '_')
            trait_specific_layer_path = os.path.join(layers_path, layer, f"{trait_name}_layers")
            if os.path.isdir(trait_specific_layer_path):
                sub_layers = [
                    d for d in os.listdir(trait_specific_layer_path)
                    if os.path.isdir(os.path.join(trait_specific_layer_path, d))
                ]
                for sub_layer in sub_layers:
                    sub_layer_key = os.path.join(layer, f"{trait_name}_layers", sub_layer)
                    sub_rarity = rarities.get(sub_layer_key, {})
                    if not sub_rarity:
                        print(f"No rarities found for sub-layer '{sub_layer_key}'. Skipping.")
                        continue
                    sub_trait = select_trait(sub_rarity)
                    if sub_trait:
                        traits[sub_layer_key] = sub_trait
                    else:
                        print(f"No trait selected for sub-layer '{sub_layer_key}'.")

        if not traits:
            print(f"No traits selected for NFT #{image_number}. Skipping.")
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

        print(f"✅ Generated NFT #{image_number} with image {final_image_path} and metadata.")

if __name__ == '__main__':
    main()
