#!/usr/bin/env python3
"""Generate ganttpilot.ico — a simple Gantt chart icon."""
from PIL import Image, ImageDraw

def generate():
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background: rounded rectangle (dark blue)
    bg_color = (52, 73, 94)  # #34495E
    draw.rounded_rectangle([8, 8, 248, 248], radius=32, fill=bg_color)

    # Gantt bars
    bars = [
        (40, 50, 160, 78, "#7BC67E"),   # green
        (80, 90, 200, 118, "#F5A623"),   # orange
        (50, 130, 180, 158, "#E74C8B"),  # pink
        (100, 170, 220, 198, "#4A90D9"), # blue
    ]
    for x1, y1, x2, y2, color in bars:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=6, fill=color)

    # Small diamond milestone marker (red)
    cx, cy, s = 190, 64, 10
    draw.polygon([(cx, cy-s), (cx+s, cy), (cx, cy+s), (cx-s, cy)], fill="#E74C3C")

    # Save as ICO with multiple sizes
    img.save("ganttpilot.ico", format="ICO",
             sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("ganttpilot.ico generated")

if __name__ == "__main__":
    generate()
