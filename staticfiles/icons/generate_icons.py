from PIL import Image, ImageDraw
import os

# Create directory structure if it doesn't exist
os.makedirs(os.path.join('static', 'icons', 'splash'), exist_ok=True)

# Define colors
background_color = (0, 0, 0)  # Black background
logo_color = (255, 255, 255)  # White logo

# Function to create icon with text
def create_icon(size, text, output_path):
    # Create a new image with a black background
    img = Image.new('RGB', size, background_color)
    draw = ImageDraw.Draw(img)
    
    # Calculate text position (centered)
    text_width = int(size[0] * 0.7)  # 70% of the icon width
    text_height = int(text_width * 0.5)  # Adjust for aspect ratio
    text_left = (size[0] - text_width) // 2
    text_top = (size[1] - text_height) // 2
    
    # Draw a white rectangle for the logo
    draw.rectangle(
        [(text_left, text_top), (text_left + text_width, text_top + text_height)],
        fill=logo_color
    )
    
    # Draw "1M" text in black
    font_size = int(text_width * 0.6)
    draw.text(
        (size[0] // 2, size[1] // 2),
        "1M",
        fill=background_color,
        font=None,  # Use default font
        anchor="mm",  # Center the text
    )
    
    # Save the image
    img.save(output_path)
    print(f"Created {output_path}")

# Create main app icons
create_icon((192, 192), "1Matrix", os.path.join('static', 'icons', 'icon-192x192.png'))
create_icon((512, 512), "1Matrix", os.path.join('static', 'icons', 'icon-512x512.png'))
create_icon((180, 180), "1Matrix", os.path.join('static', 'icons', 'apple-icon-180x180.png'))

# Create splash screen images
create_icon((640, 1136), "1Matrix", os.path.join('static', 'icons', 'splash-640x1136.png'))
create_icon((750, 1334), "1Matrix", os.path.join('static', 'icons', 'splash-750x1334.png'))
create_icon((1242, 2208), "1Matrix", os.path.join('static', 'icons', 'splash-1242x2208.png'))

print("All PWA icons generated successfully!") 