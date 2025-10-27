"""Flip the extracted jump/crouch sprites to match the LEFT-facing default."""

from PIL import Image
import os

# Sprite ranges to flip
sprite_ranges = [
    (18320, 18353),  # Jump up
    (18354, 18390),  # Jump forward
    (18391, 18428),  # Jump backward
    (18429, 18439),  # Crouching
]

output_dir = '14_Akuma'

total_flipped = 0

for start, end in sprite_ranges:
    print(f"\nFlipping sprites {start}-{end}...")

    for sprite_num in range(start, end + 1):
        sprite_path = os.path.join(output_dir, f"{sprite_num}.png")

        if os.path.exists(sprite_path):
            # Load image
            img = Image.open(sprite_path)

            # Flip horizontally
            flipped = img.transpose(Image.FLIP_LEFT_RIGHT)

            # Save back
            flipped.save(sprite_path, 'PNG')
            total_flipped += 1

            if sprite_num % 10 == 0:
                print(f"  Flipped {sprite_num}.png")
        else:
            print(f"  Warning: {sprite_path} not found")

print(f"\nTotal sprites flipped: {total_flipped}")
