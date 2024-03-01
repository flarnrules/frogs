import json
import os

# Configuration
input_directory = "../frog_day/nfts/metadata_old"  # Adjust this path to your JSON files location
output_directory = "../frog_day/nfts/metadata_new"  # Adjust this path to where you want to save updated JSON files

# Ensure output directory exists
os.makedirs(output_directory, exist_ok=True)

# New description text
new_description = "Frog profile pictures inspired by the nft collection Picture Day and launched on leap day ~February 29, 2024~. First 420 airdropped to holders of frogs, the nft collection of 420 digital frogs on Stargaze."

# Iterate over all files in the input directory
for filename in os.listdir(input_directory):
    if filename.endswith('.json'):
        # Extract the file number from the filename
        file_number = filename.split('.')[0]
        
        # Construct file paths
        input_file_path = os.path.join(input_directory, filename)
        output_file_path = os.path.join(output_directory, filename)
        
        # Open and read the JSON file
        with open(input_file_path, 'r') as file:
            data = json.load(file)
            
            # Update the name and description
            data['name'] = file_number
            data['description'] = new_description
            
            # Add the final trait for picture frame
            data['attributes'].append({
                "trait_type": "picture frame",
                "value": "fancy wood"
            })
            
            # Write the updated JSON data to a new file
            with open(output_file_path, 'w') as outfile:
                json.dump(data, outfile, indent=4)

print("Updated JSON files have been saved to:", output_directory)
