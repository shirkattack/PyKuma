#!/usr/bin/env python3
"""Test script to verify hitbox data integration"""

from street_fighter_3rd.data.enums import CharacterState
from street_fighter_3rd.data.akuma_hitboxes import get_akuma_hitboxes, get_akuma_hurtboxes, get_move_frame_data

def test_hitbox_data():
    """Test that hitbox data is loaded correctly"""
    print("Testing Akuma Hitbox Data Integration\n" + "="*50)

    # Test all standing normals
    moves = [
        (CharacterState.LIGHT_PUNCH, "Standing Light Punch"),
        (CharacterState.MEDIUM_PUNCH, "Standing Medium Punch"),
        (CharacterState.HEAVY_PUNCH, "Standing Heavy Punch"),
        (CharacterState.LIGHT_KICK, "Standing Light Kick"),
        (CharacterState.MEDIUM_KICK, "Standing Medium Kick"),
        (CharacterState.HEAVY_KICK, "Standing Heavy Kick"),
    ]

    for state, name in moves:
        print(f"\n{name}:")
        print("-" * 50)

        # Get move frame data
        move_data = get_move_frame_data(state)
        if move_data:
            print(f"  Startup: {move_data.startup}f")
            print(f"  Active: frames {move_data.active}")
            print(f"  Recovery: {move_data.recovery}f")
            print(f"  Total: {move_data.startup + len(move_data.active) + move_data.recovery}f")
            print(f"  Damage: {move_data.hitboxes[0][1].damage} HP")
            print(f"  On Hit: {move_data.on_hit:+d} frames")
            print(f"  On Block: {move_data.on_block:+d} frames")

            # Test hitbox on active frames
            for frame in move_data.active:
                hitboxes = get_akuma_hitboxes(state, frame)
                if hitboxes:
                    hb = hitboxes[0]
                    print(f"  Frame {frame} hitbox: ({hb.offset_x}, {hb.offset_y}) {hb.width}x{hb.height}")
                    break  # Just show first active frame

            # Test hurtboxes
            hurtboxes = get_akuma_hurtboxes(state)
            print(f"  Hurtboxes: {len(hurtboxes)} boxes")
            for i, hb in enumerate(hurtboxes):
                print(f"    Box {i+1}: ({hb.offset_x}, {hb.offset_y}) {hb.width}x{hb.height}")
        else:
            print(f"  ❌ No frame data found!")

    # Test frame-by-frame for one move
    print("\n" + "="*50)
    print("Frame-by-frame test for Standing Light Punch:")
    print("-" * 50)

    for frame in range(1, 16):  # Test first 15 frames
        hitboxes = get_akuma_hitboxes(CharacterState.LIGHT_PUNCH, frame)
        if hitboxes:
            print(f"  Frame {frame}: ✅ ACTIVE ({len(hitboxes)} hitbox(es))")
        else:
            print(f"  Frame {frame}: Startup/Recovery")

    print("\n" + "="*50)
    print("✅ All tests completed!")

if __name__ == "__main__":
    test_hitbox_data()
