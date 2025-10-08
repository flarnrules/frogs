import os

# === Process Type Settings ===
MEDIA_TYPE = "image"           # "image", "gif", "video"
PROCESS_SCOPE = "single"       # "single", "folder"

# === Input / Output Paths ===
INPUT_IMAGE_PATH = "inputs/big_money/1201.png" #1201 1312 1713 1798 1985 2011
INPUT_IMAGE_FOLDER = "inputs/big_money"
INPUT_GIF_PATH = "inputs/red_yellow2.gif"
OUTPUT_IMAGE_FOLDER = "outputs/big_money"
OUTPUT_GIF_PATH = "outputs/gifs/red_yellow3k.gif"

# === Emoji Library Settings ===
EMOJI_LIBRARY = "OpenMoji" #"Noto Emoji" , "OpenMoji"
EMOJI_SIZE = "72"

# === Appearance Settings ===
OUTPUT_WIDTH = 100
BACKGROUND_COLOR = (124, 124, 124, 255)
TRIM_PIXELS = 0
FINAL_SIZE = (2000, 2000)

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

def update_emoji_paths():
    global EMOJI_FOLDER, EMOJI_COLOR_INDEX
    if EMOJI_LIBRARY == "Noto Emoji":
        EMOJI_FOLDER = os.path.join(EMOJI_IMAGES_DIR, "noto-emoji", EMOJI_SIZE)
        EMOJI_COLOR_INDEX = os.path.join(EMOJI_COLOR_DIR, "emoji_color_index_noto_emoji.json")
    elif EMOJI_LIBRARY == "OpenMoji":
        EMOJI_FOLDER = os.path.join(EMOJI_IMAGES_DIR, "openmoji", EMOJI_SIZE)
        EMOJI_COLOR_INDEX = os.path.join(EMOJI_COLOR_DIR, "emoji_color_index_openmoji.json")
    else:
        raise ValueError(f"Unsupported EMOJI_LIBRARY: {EMOJI_LIBRARY}")
    
update_emoji_paths()

def update_paths_from_library(emoji_library):
    global EMOJI_FOLDER, EMOJI_COLOR_INDEX, EMOJI_LIBRARY
    EMOJI_LIBRARY = emoji_library

    if emoji_library == "Noto Emoji":
        EMOJI_FOLDER = os.path.join(EMOJI_IMAGES_DIR, "noto-emoji", EMOJI_SIZE)
        EMOJI_COLOR_INDEX = os.path.join(EMOJI_COLOR_DIR, "emoji_color_index_noto_emoji.json")
    elif emoji_library == "OpenMoji":
        EMOJI_FOLDER = os.path.join(EMOJI_IMAGES_DIR, "openmoji", "72")
        EMOJI_COLOR_INDEX = os.path.join(EMOJI_COLOR_DIR, "emoji_color_index_openmoji.json")
    else:
        raise ValueError(f"Unsupported EMOJI_LIBRARY: {emoji_library}")
    
def get_emoji_folder():
    if EMOJI_LIBRARY == "Noto Emoji":
        return os.path.join(EMOJI_IMAGES_DIR, "noto-emoji", EMOJI_SIZE)
    elif EMOJI_LIBRARY == "OpenMoji":
        return os.path.join(EMOJI_IMAGES_DIR, "openmoji", EMOJI_SIZE)
    else:
        raise ValueError(f"Unsupported EMOJI_LIBRARY: {EMOJI_LIBRARY}")

def get_emoji_color_index():
    if EMOJI_LIBRARY == "Noto Emoji":
        return os.path.join(EMOJI_COLOR_DIR, "emoji_color_index_noto_emoji.json")
    elif EMOJI_LIBRARY == "OpenMoji":
        return os.path.join(EMOJI_COLOR_DIR, "emoji_color_index_openmoji.json")
    else:
        raise ValueError(f"Unsupported EMOJI_LIBRARY: {EMOJI_LIBRARY}")