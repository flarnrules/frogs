# emojifier/interface.py

from core.emojify_image import emojify_image
from config import config as emojifier_config

def generate_emojified_image(input_path, output_path, output_width=128, emoji_library="OpenMoji"):
    # Set config dynamically
    emojifier_config.EMOJI_LIBRARY = emoji_library
    emojifier_config.OUTPUT_WIDTH = output_width

    # Update derived paths
    from config.config import update_paths_from_library
    update_paths_from_library(emoji_library)

    emojify_image(input_path, output_path, output_width=output_width)
