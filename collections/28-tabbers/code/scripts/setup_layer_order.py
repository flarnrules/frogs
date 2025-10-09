import os
import json

def get_available_layers(layers_path):
    return [d for d in os.listdir(layers_path)
            if os.path.isdir(os.path.join(layers_path, d)) and not d.startswith('.')]

def main():
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    layers_path = config['layers_path']

    # Get available layers
    available_layers = get_available_layers(layers_path)

    # Generate default layer order
    default_order = available_layers

    # Save to layer_order.json
    with open('code/data/layer_order.json', 'w') as f:
        json.dump(default_order, f, indent=4)

    print("Layer order has been saved to 'code/data/layer_order.json'.")
    print("Please review and adjust the order if necessary.")

if __name__ == '__main__':
    main()
