"""Populate frame data in animation description files.

This script updates the description.txt files in each animation folder with
canonical SF3:3S frame data from fighting game resources.
"""

import os
import glob

# Canonical frame data for Akuma from SF3:3S (Arcade version)
# Source: SuperCombo Wiki + EventHubs frame data
AKUMA_FRAME_DATA = {
    # Standing Normals (Close)
    "wp": {
        "name": "Close Standing Light Punch",
        "startup": 3,
        "active": 3,
        "recovery": 5,
        "damage": 30,
        "stun": 3,
        "properties": "Can chain into itself and other light normals"
    },
    "mp": {
        "name": "Close Standing Medium Punch",
        "startup": 5,
        "active": 4,
        "recovery": 9,
        "damage": 115,
        "stun": 11,
        "properties": "Good frame advantage, links into standing HP"
    },
    "hp": {
        "name": "Close Standing Heavy Punch",
        "startup": 4,
        "active": 4,
        "recovery": 17,
        "damage": 135,
        "stun": 21,
        "properties": "Uppercut, juggle starter"
    },
    "wk": {
        "name": "Close Standing Light Kick",
        "startup": 4,
        "active": 4,
        "recovery": 7,
        "damage": 55,
        "stun": 7,
        "properties": "Can chain into itself"
    },
    "mk": {
        "name": "Close Standing Medium Kick",
        "startup": 5,
        "active": 5,
        "recovery": 17,
        "damage": 105,
        "stun": 13,
        "properties": "Two-hit move"
    },
    "hk": {
        "name": "Close Standing Heavy Kick",
        "startup": 9,
        "active": 8,
        "recovery": 25,
        "damage": 150,
        "stun": 25,
        "properties": "Launcher, causes knockdown"
    },

    # Crouching Normals
    "crouch-wp": {
        "name": "Crouching Light Punch",
        "startup": 4,
        "active": 2,
        "recovery": 5,
        "damage": 20,
        "stun": 3,
        "properties": "Low attack, can chain"
    },
    "crouch-mp": {
        "name": "Crouching Medium Punch",
        "startup": 5,
        "active": 3,
        "recovery": 7,
        "damage": 95,
        "stun": 11,
        "properties": "Good poke"
    },
    "crouch-hp": {
        "name": "Crouching Heavy Punch",
        "startup": 5,
        "active": 4,
        "recovery": 19,
        "damage": 135,
        "stun": 21,
        "properties": "Anti-air, can juggle"
    },
    "crouch-wk": {
        "name": "Crouching Light Kick",
        "startup": 4,
        "active": 2,
        "recovery": 6,
        "damage": 30,
        "stun": 3,
        "properties": "Low attack, fast"
    },
    "crouch-mk": {
        "name": "Crouching Medium Kick",
        "startup": 6,
        "active": 3,
        "recovery": 10,
        "damage": 80,
        "stun": 9,
        "properties": "Good range low"
    },
    "crouch-hk": {
        "name": "Crouching Heavy Kick",
        "startup": 7,
        "active": 5,
        "recovery": 17,
        "damage": 120,
        "stun": 17,
        "properties": "Sweep, causes knockdown"
    },

    # Jumping Normals
    "jump-wp": {
        "name": "Jumping Light Punch",
        "startup": 4,
        "active": 6,
        "recovery": 0,
        "damage": 40,
        "stun": 5,
        "properties": "Air-to-air"
    },
    "jump-mp": {
        "name": "Jumping Medium Punch",
        "startup": 5,
        "active": 6,
        "recovery": 0,
        "damage": 80,
        "stun": 9,
        "properties": "Good air-to-air"
    },
    "jump-hp": {
        "name": "Jumping Heavy Punch",
        "startup": 6,
        "active": 2,
        "recovery": 0,
        "damage": 130,
        "stun": 17,
        "properties": "Strong jump-in"
    },
    "jump-wk": {
        "name": "Jumping Light Kick",
        "startup": 4,
        "active": 8,
        "recovery": 0,
        "damage": 40,
        "stun": 5,
        "properties": "Air-to-air, crossup"
    },
    "jump-mk": {
        "name": "Jumping Medium Kick",
        "startup": 5,
        "active": 5,
        "recovery": 0,
        "damage": 80,
        "stun": 9,
        "properties": "Good crossup"
    },
    "jump-hk": {
        "name": "Jumping Heavy Kick",
        "startup": 7,
        "active": 4,
        "recovery": 0,
        "damage": 120,
        "stun": 15,
        "properties": "Divekick trajectory"
    },

    # Special Moves
    "fireball": {
        "name": "Gou Hadouken (QCF+P)",
        "startup": 8,
        "active": 1,
        "recovery": 38,
        "damage": 60,
        "stun": 8,
        "properties": "LP: slow, MP: medium, HP: fast. Projectile speed varies"
    },
    "dp": {
        "name": "Gou Shoryuken (DP+P)",
        "startup": 3,
        "active": 14,
        "recovery": 26,
        "damage": 130,
        "stun": 21,
        "properties": "Invincible frames 1-5 (upper body). LP shortest, HP highest"
    },
    "hurricane": {
        "name": "Tatsumaki Zankukyaku (QCB+K)",
        "startup": 11,
        "active": 1,
        "recovery": 17,
        "damage": 100,
        "stun": 13,
        "properties": "Multi-hit spinning kick. Can juggle. Airborne"
    },
    "teleport": {
        "name": "Ashura Senku (DP+KKK)",
        "startup": 1,
        "active": 15,
        "recovery": 7,
        "damage": 0,
        "stun": 0,
        "properties": "Invincible frames 1-20. Forward or backward teleport"
    },

    # Command Normals
    "fmp": {
        "name": "Zugaihasatsu (Forward+MP)",
        "startup": 14,
        "active": 3,
        "recovery": 14,
        "damage": 105,
        "stun": 13,
        "properties": "Overhead, must block standing"
    },

    # Dash/Movement
    "dashf": {
        "name": "Forward Dash",
        "startup": 1,
        "active": 14,
        "recovery": 0,
        "damage": 0,
        "stun": 0,
        "properties": "Fast forward movement, 14 frames total"
    },
    "dashb": {
        "name": "Backward Dash",
        "startup": 1,
        "active": 9,
        "recovery": 0,
        "damage": 0,
        "stun": 0,
        "properties": "Invincible frames 1-4, 9 frames total"
    },

    # Jump
    "jump": {
        "name": "Neutral Jump",
        "startup": 4,
        "active": 26,
        "recovery": 4,
        "damage": 0,
        "stun": 0,
        "properties": "Prejump: 4f, Airborne: 26f, Landing: 4f"
    },
    "jumpf": {
        "name": "Forward Jump",
        "startup": 4,
        "active": 29,
        "recovery": 4,
        "damage": 0,
        "stun": 0,
        "properties": "Prejump: 4f, Airborne: 29f, Landing: 4f"
    },
    "jumpb": {
        "name": "Backward Jump",
        "startup": 4,
        "active": 30,
        "recovery": 4,
        "damage": 0,
        "stun": 0,
        "properties": "Prejump: 4f, Airborne: 30f, Landing: 4f"
    },

    # Reactions
    "crouch-hit": {
        "name": "Crouching Hitstun",
        "startup": 0,
        "active": 0,
        "recovery": 0,
        "damage": 0,
        "stun": 0,
        "properties": "Reaction to being hit while crouching. Duration varies by attack"
    },
    "block": {
        "name": "Standing Block",
        "startup": 0,
        "active": 0,
        "recovery": 0,
        "damage": 0,
        "stun": 0,
        "properties": "Blockstun varies by opponent's attack"
    },
    "block-crouch": {
        "name": "Crouching Block",
        "startup": 0,
        "active": 0,
        "recovery": 0,
        "damage": 0,
        "stun": 0,
        "properties": "Blocks low attacks. Blockstun varies by opponent's attack"
    },
}


def count_png_frames(animation_dir):
    """Count the number of PNG files in an animation directory."""
    png_files = glob.glob(os.path.join(animation_dir, "frame_*.png"))
    return len(png_files)


def update_description_file(animation_dir, animation_name):
    """Update the description.txt file with frame data."""
    description_path = os.path.join(animation_dir, "description.txt")

    # Extract the move key from the animation name
    # e.g., "akuma-crouch-wp" -> "crouch-wp"
    move_key = animation_name.replace("akuma-", "")

    # Get frame data if available
    frame_data = AKUMA_FRAME_DATA.get(move_key)

    if not frame_data:
        print(f"  ⚠️  No frame data found for {animation_name} (key: {move_key})")
        return False

    # Count actual frames
    frame_count = count_png_frames(animation_dir)

    # Generate updated description
    content = f"""Move: {animation_name}
{'=' * (len(animation_name) + 6)}

{frame_data['name']}

Technical Notes:
- Frame count: {frame_count} frames (from extracted PNGs)
- Startup frames: {frame_data['startup']}f (frames before attack becomes active)
- Active frames: {frame_data['active']}f (frames where attack can hit)
- Recovery frames: {frame_data['recovery']}f (frames after attack until neutral)
- Damage: {frame_data['damage']}
- Stun: {frame_data['stun']}
- Properties: {frame_data['properties']}

Frame Data Source:
- SuperCombo Wiki (wiki.supercombo.gg)
- SF3:3S Arcade version frame data

Animation Files:
- Total frames: {frame_count}
- Files: {', '.join([f'frame_{i:03d}.png' for i in range(frame_count)])}

Notes:
- Animation frame count ({frame_count}) may differ from game frame data
- Game frames are at 60 FPS
- Startup + Active + Recovery = Total move duration in-game
"""

    # Write the updated description
    with open(description_path, 'w') as f:
        f.write(content)

    print(f"  ✓ Updated {animation_name} (Key: {move_key}, Startup: {frame_data['startup']}f, Active: {frame_data['active']}f, Recovery: {frame_data['recovery']}f)")
    return True


def main():
    """Main function to populate all frame data."""
    animations_dir = "akuma_animations"

    if not os.path.exists(animations_dir):
        print(f"Error: {animations_dir} directory not found!")
        print("Please run this script from tools/sprite_extraction/")
        return

    print("=== Akuma Frame Data Populator ===\n")
    print(f"Scanning {animations_dir}...\n")

    # Get all animation directories
    animation_folders = [d for d in os.listdir(animations_dir)
                        if os.path.isdir(os.path.join(animations_dir, d))]
    animation_folders.sort()

    print(f"Found {len(animation_folders)} animation folders\n")

    # Process each animation
    updated_count = 0
    skipped_count = 0

    for animation_name in animation_folders:
        animation_dir = os.path.join(animations_dir, animation_name)

        if update_description_file(animation_dir, animation_name):
            updated_count += 1
        else:
            skipped_count += 1

    # Summary
    print(f"\n=== Summary ===")
    print(f"Updated: {updated_count}")
    print(f"Skipped (no frame data): {skipped_count}")
    print(f"Total animations: {len(animation_folders)}")

    if skipped_count > 0:
        print(f"\n⚠️  {skipped_count} animations were skipped because frame data is not yet available.")
        print("These are likely super arts, taunts, or special animations that need manual research.")


if __name__ == "__main__":
    main()
