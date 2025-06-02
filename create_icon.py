#!/usr/bin/env python3
"""
Create app icon for Medical Medium YouTube Comment Explorer
"""

from PIL import Image, ImageDraw
import math

def create_app_icon():
    # Create a 1024x1024 icon
    size = 1024
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # YouTube-inspired color scheme - yellow comment bubble
    bubble_color = '#FFD700'    # Golden yellow (YouTube style)
    triangle_color = '#333333'  # Dark gray for play button
    shadow_color = '#E6C200'    # Darker yellow for depth

    # Create comment bubble shape (rounded rectangle with tail)
    center_x = size // 2
    center_y = int(size * 0.4)  # Slightly higher than center
    
    # Main bubble dimensions
    bubble_width = int(size * 0.7)
    bubble_height = int(size * 0.5)
    corner_radius = int(bubble_height * 0.2)
    
    # Draw main bubble (rounded rectangle)
    bubble_left = center_x - bubble_width // 2
    bubble_top = center_y - bubble_height // 2
    bubble_right = center_x + bubble_width // 2
    bubble_bottom = center_y + bubble_height // 2
    
    # Create rounded rectangle for main bubble
    draw.rounded_rectangle(
        [bubble_left, bubble_top, bubble_right, bubble_bottom],
        radius=corner_radius,
        fill=bubble_color,
        outline=shadow_color,
        width=6
    )
    
    # Draw speech bubble tail (pointing down-left)
    tail_width = int(bubble_width * 0.15)
    tail_height = int(bubble_height * 0.4)
    tail_x = center_x - int(bubble_width * 0.25)
    tail_y = bubble_bottom
    
    tail_points = [
        (tail_x, tail_y),
        (tail_x - tail_width, tail_y + tail_height),
        (tail_x + tail_width//2, tail_y)
    ]
    draw.polygon(tail_points, fill=bubble_color, outline=shadow_color)
    
    # Draw play button triangle in center of bubble
    triangle_size = int(bubble_height * 0.3)
    triangle_center_x = center_x + triangle_size // 8  # Slightly offset right for visual balance
    triangle_center_y = center_y
    
    triangle_points = [
        (triangle_center_x - triangle_size//2, triangle_center_y - triangle_size//2),
        (triangle_center_x - triangle_size//2, triangle_center_y + triangle_size//2),
        (triangle_center_x + triangle_size//2, triangle_center_y)
    ]
    draw.polygon(triangle_points, fill=triangle_color)
    
    # Add subtle highlight to make it more dimensional
    highlight_color = '#FFEC8B'  # Lighter yellow
    highlight_thickness = 3
    
    # Top highlight on bubble
    draw.rounded_rectangle(
        [bubble_left + highlight_thickness, 
         bubble_top + highlight_thickness, 
         bubble_right - highlight_thickness, 
         bubble_top + int(bubble_height * 0.3)],
        radius=corner_radius - highlight_thickness,
        fill=None,
        outline=highlight_color,
        width=2
    )

    # Save the icon
    img.save('app_icon.png')
    print('✅ Created app_icon.png (1024x1024)')
    print('📱 Icon features:')
    print('   - YouTube-style yellow comment bubble')
    print('   - Dark play button triangle')
    print('   - Speech bubble tail for comment context')
    print('   - Clean, recognizable design')

if __name__ == '__main__':
    try:
        create_app_icon()
    except ImportError:
        print('❌ PIL (Pillow) not found. Installing...')
        import subprocess
        import sys
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'Pillow'], check=True)
        create_app_icon() 