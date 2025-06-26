# emojifier/batch_runner.py

import os
from config.config import (
    PROCESS_SCOPE,
    INPUT_IMAGE_PATH,
    INPUT_IMAGE_FOLDER,
    OUTPUT_IMAGE_FOLDER
)
from core.emojify_image import emojify_image

def run_batch():
    os.makedirs(OUTPUT_IMAGE_FOLDER, exist_ok=True)

    if PROCESS_SCOPE == "single":
        filename = os.path.basename(INPUT_IMAGE_PATH)
        output_path = os.path.join(OUTPUT_IMAGE_FOLDER, filename)
        emojify_image(INPUT_IMAGE_PATH, output_path)

    elif PROCESS_SCOPE == "folder":
        for fname in os.listdir(INPUT_IMAGE_FOLDER):
            if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                input_path = os.path.join(INPUT_IMAGE_FOLDER, fname)
                output_path = os.path.join(OUTPUT_IMAGE_FOLDER, fname)
                emojify_image(input_path, output_path)
    else:
        raise ValueError("PROCESS_SCOPE must be 'single' or 'folder'")
