# cli/cli_interface.py

import os
from core.emojify_image import emojify_image
from core.emojify_gif import emojify_gif
from core.batch_runner import run_batch

def launch_cli():
    print("🎛️ Emojifier CLI")
    print("===================")
    print("1. Emojify a single image")
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
