import json
import random
import os
from .utils import format_trait_name

def generate_metadata(image_number, traits, config):
    attributes = []
    for layer, trait in traits.items():
        if trait != 'None':
            # Extract the last part of the layer name
            trait_type = os.path.basename(layer).replace('_', ' ').capitalize()
            attributes.append({
                "trait_type": trait_type,
                "value": format_trait_name(trait)
            })

    # Optionally include a quote
    if config.get('include_quotes', False):
        try:
            with open(config['quotes_path'], 'r') as f:
                quotes = json.load(f)
            if quotes:
                quote = random.choice(quotes)
                attributes.append({"trait_type": "Quote", "value": quote})
            else:
                print("Warning: 'quotes.json' is empty.")
        except FileNotFoundError:
            print(f"Warning: 'quotes.json' not found at {config['quotes_path']}.")
        except json.JSONDecodeError:
            print("Warning: 'quotes.json' is not valid JSON.")

    metadata = {
        "name": f"NFT #{image_number}",
        "description": config['metadata'].get('description', ''),
        "attributes": attributes
    }
    return metadata