import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from emojifier.config import MEDIA_TYPE, PROCESS_SCOPE
from emojifier.batch_runner import run_batch
from emojifier.emojify_gif import emojify_gif
from emojifier.config import INPUT_GIF_PATH, OUTPUT_GIF_PATH

if __name__ == "__main__":
    if MEDIA_TYPE == "gif":
        emojify_gif(INPUT_GIF_PATH, OUTPUT_GIF_PATH)
    elif MEDIA_TYPE == "image":
        run_batch()
    else:
        raise ValueError("Unsupported MEDIA_TYPE: use 'image' or 'gif'")
