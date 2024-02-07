import json
import os

# Define the base path for layers
path_to_layers = '../layers/'

# Function to retrieve all file names in a given directory
def get_trait_files(path):
    return [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

# Function to calculate rarities
def calculate_rarities(layer_path):
    rarities = {}
    for layer in os.listdir(layer_path):
        trait_path = os.path.join(layer_path, layer)
        if os.path.isdir(trait_path):
            trait_files = get_trait_files(trait_path)
            trait_count = len(trait_files)
            rarities[layer] = {trait_file: round(100.0 / trait_count, 2) for trait_file in trait_files}
    return rarities

# Calculate rarities for layers
layer_rarities = calculate_rarities(path_to_layers)

# Save the rarities to a JSON file in the data folder
path_to_data = '../data/rarities.json'  # Adjust the path as needed
with open(path_to_data, 'w') as outfile:
    json.dump(layer_rarities, outfile, indent=4)

print("Rarities JSON has been generated and saved to", path_to_data)
