# emojifier/batch_runner.py

import os
from config import config  # ✅ dynamic config access
from core.emojify_image import emojify_image

def run_batch():
    os.makedirs(config.OUTPUT_IMAGE_FOLDER, exist_ok=True)

    if config.PROCESS_SCOPE == "single":
        filename = os.path.basename(config.INPUT_IMAGE_PATH)
        output_path = os.path.join(config.OUTPUT_IMAGE_FOLDER, filename)
        emojify_image(config.INPUT_IMAGE_PATH, output_path)

    elif config.PROCESS_SCOPE == "folder":
        for fname in os.listdir(config.INPUT_IMAGE_FOLDER):
            if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                input_path = os.path.join(config.INPUT_IMAGE_FOLDER, fname)
                output_path = os.path.join(config.OUTPUT_IMAGE_FOLDER, fname)
                emojify_image(input_path, output_path)

    else:
        raise ValueError("PROCESS_SCOPE must be 'single' or 'folder'")
