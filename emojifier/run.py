# emojifier/run.py

import argparse
from cli.cli_interface import launch_cli
from cli.cli_interface import launch_cli, run_single_image

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", action="store_true", help="Run single image mode")
    parser.add_argument("input", nargs="?", help="Path to input image")
    parser.add_argument("output", nargs="?", help="Path to output image")
    parser.add_argument("--emoji_set", help="Emoji set to use")
    parser.add_argument("--width", type=int, help="Output width")

    args = parser.parse_args()

    if args.single and args.input and args.output:
        run_single_image(
            input_path=args.input,
            output_path=args.output,
            emoji_set=args.emoji_set,
            output_width=args.width
        )
    else:
        launch_cli()