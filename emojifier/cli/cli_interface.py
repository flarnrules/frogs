# cli/cli_interface.py

import os
from core.emojify_image import emojify_image
from core.emojify_gif import emojify_gif
from core.batch_runner import run_batch
from config import config

def choose_emoji_library():
    available_sets = {
        "Noto Emoji": "noto-emoji",
        "OpenMoji": "openmoji"
    }

    default_set = config.EMOJI_LIBRARY
    print(f"\n🌈 Available emoji sets:")
    for i, name in enumerate(available_sets, 1):
        mark = " (default)" if name == default_set else ""
        print(f"  {i}. {name}{mark}")

    choice = input(f"Choose an emoji set [Enter for default = '{default_set}']: ").strip()

    selected = default_set
    if choice.isdigit() and 1 <= int(choice) <= len(available_sets):
        selected = list(available_sets.keys())[int(choice) - 1]
    elif choice != "":
        print("⚠️ Invalid choice, using default.")

    config.EMOJI_LIBRARY = selected
    config.update_emoji_paths()

    print(f"[INFO] Using emoji set: {selected}")
    print(f"[INFO] Emoji images from: {config.EMOJI_FOLDER}")
    print(f"[INFO] Color index file: {config.EMOJI_COLOR_INDEX}")

def launch_cli():
    print("🎛️ Emojifier CLI")
    print("===================")
    choose_emoji_library()

    print("\n1. Emojify a single image")
    print("2. Emojify a GIF")
    print("3. Run batch mode")
    choice = input("Choose an option (1, 2, or 3): ")

    if choice == "1":
        input_path = input("Enter path to input image: ").strip()
        output_path = input("Enter path to save output: ").strip()
        emojify_image(input_path, output_path)

    elif choice == "2":
        input_path = input("Enter path to input GIF: ").strip()
        output_path = input("Enter path to save output GIF: ").strip()
        emojify_gif(input_path, output_path)

    elif choice == "3":
        run_batch()

    else:
        print("❌ Invalid choice.")
        
def run_single_image(input_path, output_path, emoji_set=None, output_width=None):
    # Override config for emoji set
    if emoji_set:
        config.EMOJI_LIBRARY = emoji_set
        config.EMOJI_FOLDER = config.get_emoji_folder()
        config.EMOJI_COLOR_INDEX = config.get_emoji_color_index()

    emojify_image(input_path, output_path, output_width=output_width)