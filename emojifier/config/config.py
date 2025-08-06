import os

# === Process Type Settings ===
MEDIA_TYPE = "image"           # "image", "gif", "video"
PROCESS_SCOPE = "single"       # "single", "folder"

# === Input / Output Paths ===
INPUT_IMAGE_PATH = "inputs/the_frog_and_the_lizard2.png"
INPUT_IMAGE_FOLDER = "inputs/images"
INPUT_GIF_PATH = "inputs/red_yellow2.gif"
OUTPUT_IMAGE_FOLDER = "outputs/images"
OUTPUT_GIF_PATH = "outputs/gifs/red_yellow3k.gif"

# === Emoji Library Settings ===
EMOJI_LIBRARY = "Noto Emoji" #"Noto Emoji" , "OpenMoji"
EMOJI_SIZE = "72"

# === Appearance Settings ===
OUTPUT_WIDTH = 128
BACKGROUND_COLOR = (0, 0, 0, 255)
TRIM_PIXELS = 0
FINAL_SIZE = (3000, 3000)

# === Derived Paths ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EMOJI_DATA_DIR = os.path.join(BASE_DIR, "emoji_data")
EMOJI_IMAGES_DIR = os.path.join(EMOJI_DATA_DIR, "emoji_images")
EMOJI_COLOR_DIR = os.path.join(EMOJI_DATA_DIR, "emoji_color_data")

if EMOJI_LIBRARY == "Noto Emoji":
    EMOJI_FOLDER = os.path.join(EMOJI_IMAGES_DIR, "noto-emoji", EMOJI_SIZE)
    EMOJI_COLOR_INDEX = os.path.join(EMOJI_COLOR_DIR, "emoji_color_index_noto_emoji.json")
elif EMOJI_LIBRARY == "OpenMoji":
    EMOJI_FOLDER = os.path.join(EMOJI_IMAGES_DIR, "openmoji", "72")
    EMOJI_COLOR_INDEX = os.path.join(EMOJI_COLOR_DIR, "emoji_color_index_openmoji.json")
else:
    raise ValueError(f"Unsupported EMOJI_LIBRARY: {EMOJI_LIBRARY}")
