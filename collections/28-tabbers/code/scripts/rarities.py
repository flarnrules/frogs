import json
import os
import logging

logging.basicConfig(level=logging.INFO)

def get_trait_files(path):
    return [f for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f)) and not f.startswith('.')]

def update_rarities(layer_path, none_probability_layers=None, existing_rarities=None):
    import logging
    if none_probability_layers is None:
        none_probability_layers = {}
    if existing_rarities is None:
        existing_rarities = {}

    # Start with a copy of existing rarities
    new_rarities = existing_rarities.copy()

    # Keep track of current layers
    current_layers = set()

    # Traverse the layers directory to get the current layers and traits
    for root, _, _ in os.walk(layer_path):
        # Skip the root directory
        if root == layer_path:
            continue
        # Construct layer name relative to base path
        layer_name = os.path.relpath(root, layer_path).replace('\\', '/')
        current_layers.add(layer_name)
        # Get trait files in this directory
        trait_files = get_trait_files(root)
        if trait_files:
            logging.info(f"Processing layer: {layer_name}")
            existing_layer_rarities = existing_rarities.get(layer_name, {})
            new_rarities[layer_name] = existing_layer_rarities.copy()

            # Update existing traits and add new traits
            for trait_file in trait_files:
                if trait_file not in existing_layer_rarities:
                    # Assign default probability (will adjust later)
                    new_rarities[layer_name][trait_file] = None  # Mark for default assignment

            # Remove traits that no longer exist
            traits_to_remove = [trait for trait in existing_layer_rarities if trait != 'None' and trait not in trait_files]
            for trait in traits_to_remove:
                logging.info(f"Trait '{trait}' no longer exists in layer '{layer_name}'. Removing from rarities.")
                del new_rarities[layer_name][trait]

            # Handle 'None' probability
            if layer_name in none_probability_layers:
                none_prob = none_probability_layers[layer_name]
                if 'None' not in new_rarities[layer_name]:
                    new_rarities[layer_name]['None'] = round(100.0 * none_prob, 2)
                else:
                    # Preserve existing 'None' probability
                    pass
            else:
                # Remove 'None' if it's in existing rarities but not in none_probabilities
                if 'None' in new_rarities[layer_name]:
                    del new_rarities[layer_name]['None']

            # Assign default probabilities to new traits
            unassigned_traits = [trait for trait, prob in new_rarities[layer_name].items() if prob is None]
            total_assigned_prob = sum(float(prob) for prob in new_rarities[layer_name].values() if prob is not None)
            num_unassigned = len(unassigned_traits)
            remaining_prob = 100.0 - total_assigned_prob

            if num_unassigned > 0:
                default_prob = round(remaining_prob / num_unassigned, 2)
                for trait in unassigned_traits:
                    new_rarities[layer_name][trait] = default_prob

            # Ensure total probability sums to 100%
            total_prob = sum(float(prob) for prob in new_rarities[layer_name].values())
            difference = 100.0 - total_prob
            if abs(difference) > 0.01:
                # Adjust the last trait's probability
                last_trait = next(reversed(new_rarities[layer_name]))
                new_rarities[layer_name][last_trait] += difference
        else:
            logging.warning(f"No trait files found in layer '{layer_name}'. Skipping this layer.")

    # Remove layers that no longer exist
    existing_layers = set(existing_rarities.keys())
    layers_to_remove = existing_layers - current_layers

    if layers_to_remove:
        for layer_name in layers_to_remove:
            logging.info(f"Layer '{layer_name}' no longer exists. Removing from rarities.")
            del new_rarities[layer_name]  # Now this will not raise KeyError

    return new_rarities

if __name__ == '__main__':
    import sys
    # Load configurations from config.json
    config_path = 'config.json'
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.error(f"Config file '{config_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"Config file '{config_path}' is not valid JSON.")
        sys.exit(1)

    layer_path = config.get('layers_path', '')
    if not os.path.isdir(layer_path):
        logging.error(f"Layers path '{layer_path}' does not exist or is not a directory.")
        sys.exit(1)

    none_probability_layers = config.get('none_probabilities', {})

    # Load existing rarities if they exist
    output_path = os.path.join('code', 'data', 'rarities.json')
    if os.path.exists(output_path):
        with open(output_path, 'r') as f:
            existing_rarities = json.load(f)
    else:
        existing_rarities = {}

    new_rarities = update_rarities(layer_path, none_probability_layers, existing_rarities)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as outfile:
        json.dump(new_rarities, outfile, indent=4)
    logging.info(f"Rarities JSON has been updated and saved to {output_path}")
