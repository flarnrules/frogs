from PIL import Image, ImageDraw
import math

def find_edge_points(frame, center, angles):
    width, height = frame.size
    pixels = frame.load()
    edge_points = []
    
    for angle in angles:
        for r in range(max(width, height)):
            x = int(center[0] + r * math.cos(math.radians(angle)))
            y = int(center[1] + r * math.sin(math.radians(angle)))
            if x < 0 or x >= width or y < 0 or y >= height or pixels[x, y][3] != 0:
                edge_points.append((x, y))
                break
                
    return edge_points

def approximate_interior_mask(frame, edge_points):
    mask = Image.new('L', frame.size, 0)
    draw = ImageDraw.Draw(mask)
    
    # Assuming the shape is elliptical, we can use the bounding box of the edge points
    min_x = min([point[0] for point in edge_points])
    max_x = max([point[0] for point in edge_points])
    min_y = min([point[1] for point in edge_points])
    max_y = max([point[1] for point in edge_points])
    
    # Draw an ellipse based on the bounding box
    draw.ellipse([min_x, min_y, max_x, max_y], fill=255)
    
    return mask

def color_exterior(frame_path, exterior_color=(0, 0, 255)):
    frame = Image.open(frame_path).convert("RGBA")
    center = (frame.width // 2, frame.height // 2)
    
    angles = [0, 45, 90, 135, 180, 225, 270, 315]
    edge_points = find_edge_points(frame, center, angles)
    
    mask = approximate_interior_mask(frame, edge_points)
    
    # Create an image for the exterior color
    exterior = Image.new("RGBA", frame.size, exterior_color + (255,))
    interior = Image.composite(frame, exterior, mask)
    
    return interior

# Example usage
#frame_path = '../frog_day/picture_frames/crystal_frame_circle.png'
#colored_frame = color_exterior(frame_path)
#colored_frame.show()
