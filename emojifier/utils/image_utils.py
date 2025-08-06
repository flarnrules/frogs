from PIL import Image

def get_resized_dimensions(image_path, final_width, verbose=True):
    with Image.open(image_path) as img:
        original_width, original_height = img.size
        aspect_ratio = original_height / original_width
        final_height = int(final_width * aspect_ratio)

        if verbose:
            print(f"[INFO] Original size: {original_width}x{original_height}")
            print(f"[INFO] Calculated aspect ratio: {aspect_ratio:.4f}")
            print(f"[INFO] Final resized dimensions: {final_width}x{final_height}")

        return final_width, final_height
