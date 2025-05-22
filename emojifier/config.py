import os

# === Process Type Settings ===
MEDIA_TYPE = "gif"           # "image", "gif", "video"
PROCESS_SCOPE = "single"       # "single", "folder"

# === Input / Output Paths ===
INPUT_IMAGE_PATH = "inputs/frog.png"
INPUT_IMAGE_FOLDER = "inputs/images"
INPUT_GIF_PATH = "inputs/red_yellow2.gif"
OUTPUT_IMAGE_FOLDER = "outputs/images"
OUTPUT_GIF_PATH = "outputs/red_yellow18-2.gif"

# === Emoji Library Settings ===
EMOJI_LIBRARY = "Noto Emoji"
EMOJI_SIZE = "72"

# === Appearance Settings ===
OUTPUT_WIDTH_RANGE = (18, 19)
ROWS_TO_COLUMNS = 1
BACKGROUND_COLOR = (0, 0, 0, 255)
TRIM_PIXELS = 0
FINAL_SIZE = (1000, 1000)

# === Derived Paths ===
BASE_DIR = os.path.dirname(__file__)
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
