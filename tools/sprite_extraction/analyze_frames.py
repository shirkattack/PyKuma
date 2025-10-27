"""Analyze GIF frames to get sprite counts."""

from PIL import Image

gifs = {
    'jump_up': 'jump_up.gif',
    'jump_forward': 'jump_forward.gif',
    'jump_backward': 'jump_backward.gif',
    'crouching': 'crouching.gif'
}

# Starting sprite numbers (continuing from existing sprite sheet)
# Walk backward ended at 18310, so let's start at 18320
sprite_mappings = {}
current_sprite = 18320

for anim_name, filename in gifs.items():
    print(f"\nAnalyzing {anim_name} ({filename})...")

    img = Image.open(filename)

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

# Print the mapping
print("\n" + "="*60)
print("SPRITE MAPPINGS FOR AKUMA.PY:")
print("="*60)
for anim_name, mapping in sprite_mappings.items():
    print(f"\n# {anim_name.replace('_', ' ').title()} ({mapping['count']} frames)")
    print(f"# Sprites {mapping['start']}-{mapping['end']}")
    print(f"{anim_name}_anim = create_simple_animation(")
    print(f"    {mapping['frames']},")
    print(f"    frame_duration=2,  # Adjust as needed")
    print(f"    loop=False  # Set to True if looping")
    print(f")")
    print(f"self.animation_controller.add_animation(\"{anim_name}\", {anim_name}_anim)")
