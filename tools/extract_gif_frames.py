#!/usr/bin/env python3
"""Extract individual frames from Akuma animation GIFs and map them to sprite numbers."""

import sys
from PIL import Image, ImageChops
import os
import urllib.request
import json

def download_gif(animation_name, output_path):
    """Download a GIF from justnopoint.com."""
    url = f"https://www.justnopoint.com/zweifuss/colorswap.php?pcolorstring=AkumaPalette.bin&pcolornum=7&pname=akuma/{animation_name}.gif"
    print(f"Downloading {animation_name}...")

    # Use subprocess.run with curl instead of urllib (server rejects Python user agent)
    import subprocess
    result = subprocess.run(['curl', '-s', '-o', output_path, url], capture_output=True)
    if result.returncode != 0:
        raise Exception(f"Failed to download: {result.stderr.decode()}")

    print(f"  Saved to {output_path}")

def extract_frames(gif_path, output_dir):
    """Extract all frames from a GIF file."""
    img = Image.open(gif_path)
    frames = []

    try:
        frame_num = 0
        while True:
            # Save current frame
            frame_path = os.path.join(output_dir, f"frame_{frame_num:03d}.png")
            img.save(frame_path, 'PNG')
            frames.append(frame_path)

            frame_num += 1
            img.seek(img.tell() + 1)
    except EOFError:
        pass  # End of frames

    print(f"  Extracted {len(frames)} frames")
    return frames

def find_matching_sprite(frame_path, sprite_dir):
    """Find which sprite number matches this frame (if any)."""
    frame = Image.open(frame_path).convert('RGBA')

    # Try to find exact match in sprite directory
    for sprite_file in sorted(os.listdir(sprite_dir)):
        if not sprite_file.endswith('.png'):
            continue

        sprite_path = os.path.join(sprite_dir, sprite_file)
        sprite = Image.open(sprite_path).convert('RGBA')

        # Resize to same dimensions for comparison
        if frame.size != sprite.size:
            # Try both: resize frame to sprite, and sprite to frame
            if frame.size[0] <= sprite.size[0] and frame.size[1] <= sprite.size[1]:
                # Frame is smaller, compare with cropped sprite
                diff = ImageChops.difference(frame, sprite.crop((0, 0, frame.size[0], frame.size[1])))
            else:
                continue  # Sizes incompatible
        else:
            diff = ImageChops.difference(frame, sprite)

        # Check if images are identical (all pixels have diff of 0)
        if diff.getbbox() is None:
            sprite_num = sprite_file.replace('.png', '')
            return sprite_num

    return None

def analyze_animation(animation_name, sprite_dir="./14_Akuma"):
    """Download GIF, extract frames, and map to sprite numbers."""
    # Create temp directory for this animation
    temp_dir = f"/tmp/akuma_frames/{animation_name}"
    os.makedirs(temp_dir, exist_ok=True)

    # Download GIF
    gif_path = os.path.join(temp_dir, f"{animation_name}.gif")
    download_gif(animation_name, gif_path)

    # Extract frames
    frames = extract_frames(gif_path, temp_dir)

    # Try to match each frame to a sprite
    print(f"  Matching frames to sprites...")
    sprite_sequence = []
    for i, frame_path in enumerate(frames):
        sprite_num = find_matching_sprite(frame_path, sprite_dir)
        if sprite_num:
            sprite_sequence.append(sprite_num)
            print(f"    Frame {i}: {sprite_num}.png")
        else:
            print(f"    Frame {i}: No exact match found")
            sprite_sequence.append(None)

    return {
        "animation_name": animation_name,
        "total_frames": len(frames),
        "sprite_sequence": sprite_sequence
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_gif_frames.py <animation-name>")
        print("Example: python extract_gif_frames.py akuma-stance")
        print("\nOr: python extract_gif_frames.py --all")
        sys.exit(1)

    animation_name = sys.argv[1]

    if animation_name == "--all":
        # Process all animations from list
        with open("/tmp/akuma_animations.txt") as f:
            animations = [line.strip() for line in f if line.strip()]

        results = {}
        for anim in animations:
            try:
                result = analyze_animation(anim)
                results[anim] = result
            except Exception as e:
                print(f"  ERROR: {e}")
                results[anim] = {"error": str(e)}

        # Save results
        output_file = "./akuma_animation_mapping.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved all results to {output_file}")
    else:
        # Process single animation
        result = analyze_animation(animation_name)
        print(f"\nResult:")
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
