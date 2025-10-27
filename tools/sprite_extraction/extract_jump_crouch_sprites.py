"""Extract sprite frames from jump and crouch GIFs."""

import requests
from PIL import Image
import io

# URLs for the animations
urls = {
    'jump_up': 'https://www.justnopoint.com/zweifuss/colorswap.php?pcolorstring=AkumaPalette.bin&pcolornum=7&pname=akuma/akuma-jump.gif',
    'jump_forward': 'https://www.justnopoint.com/zweifuss/colorswap.php?pcolorstring=AkumaPalette.bin&pcolornum=7&pname=akuma/akuma-jumpf.gif',
    'jump_backward': 'https://www.justnopoint.com/zweifuss/colorswap.php?pcolorstring=AkumaPalette.bin&pcolornum=7&pname=akuma/akuma-jumpb.gif',
    'crouching': 'https://www.justnopoint.com/zweifuss/colorswap.php?pcolorstring=AkumaPalette.bin&pcolornum=7&pname=akuma/akuma-crouching.gif'
}

# Starting sprite numbers (continuing from existing sprite sheet)
# We'll need to find what comes after the walk animations
# Walk backward ended at 18310, so let's start at 18320
sprite_mappings = {}
current_sprite = 18320

for anim_name, url in urls.items():
    print(f"\nDownloading {anim_name}...")
    response = requests.get(url)

    if response.status_code == 200:
        img = Image.open(io.BytesIO(response.content))

        # Get number of frames
        frame_count = 0
        try:
            while True:
                img.seek(frame_count)
                frame_count += 1
        except EOFError:
            pass

        print(f"  Found {frame_count} frames")

        # Store sprite range
        start_sprite = current_sprite
        sprite_mappings[anim_name] = {
            'start': start_sprite,
            'end': start_sprite + frame_count - 1,
            'count': frame_count,
            'frames': list(range(start_sprite, start_sprite + frame_count))
        }

        current_sprite += frame_count

    else:
        print(f"  Failed to download: {response.status_code}")

# Print the mapping
print("\n" + "="*60)
print("SPRITE MAPPINGS:")
print("="*60)
for anim_name, mapping in sprite_mappings.items():
    print(f"\n{anim_name.upper()}:")
    print(f"  Sprite range: {mapping['start']}-{mapping['end']}")
    print(f"  Frame count: {mapping['count']}")
    print(f"  Frame list: {mapping['frames']}")
