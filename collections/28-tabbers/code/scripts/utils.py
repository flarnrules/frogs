import os
import random
import json

def load_config(config_path='config.json'):
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

def get_trait_files(path):
    return [f for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f)) and not f.startswith('.')]

def select_trait(rarity_dict, disallowed_traits=None):
    disallowed_traits = disallowed_traits or []
    available = {k: v for k, v in rarity_dict.items() if k not in disallowed_traits}
    if not available:
        return None
    traits = list(available.keys())
    weights = list(available.values())
    return random.choices(traits, weights=weights, k=1)[0]

def format_trait_name(file_name):
    name_without_extension = os.path.splitext(file_name)[0]
    formatted_name = name_without_extension.replace('_', ' ').replace('-', ' ')
    return ' '.join(word.capitalize() for word in formatted_name.split())
