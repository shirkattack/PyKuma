"""Extract GIF frames to PNG files."""

from PIL import Image
import os

gifs = {
    'jump_up.gif': 18320,       # Start at sprite 18320
    'jump_forward.gif': 18354,  # Start at sprite 18354
    'jump_backward.gif': 18391, # Start at sprite 18391
    'crouching.gif': 18429      # Start at sprite 18429
}

output_dir = '14_Akuma'

for gif_file, start_sprite in gifs.items():
    print(f"\nProcessing {gif_file}...")

    img = Image.open(gif_file)
    frame_count = 0

    try:
        while True:
            # Save current frame
            sprite_number = start_sprite + frame_count
            output_path = os.path.join(output_dir, f"{sprite_number}.png")

            # Convert to RGBA if needed
            frame = img.convert('RGBA')
            frame.save(output_path, 'PNG')

            print(f"  Saved frame {frame_count} as {sprite_number}.png")

            # Move to next frame
            frame_count += 1
            img.seek(frame_count)

    except EOFError:
        print(f"  Extracted {frame_count} frames from {gif_file}")

print("\nDone!")
