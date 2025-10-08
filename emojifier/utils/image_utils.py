from PIL import Image

def get_resized_dimensions(image_path, final_width, verbose=True):
    with Image.open(image_path) as img:
        original_width, original_height = img.size
        aspect_ratio = original_height / original_width
        final_height = int(final_width * aspect_ratio)

        if verbose:
            print(f"[INFO] Input image size: {original_width}x{original_height} px")
            print(f"[INFO] Emoji grid dimensions: {final_width}x{final_height} (W x H)")
            print(f"[INFO] Aspect ratio: {aspect_ratio:.4f}")

        return final_width, final_height
