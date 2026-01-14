"""
SF3:3S Character Dimensions

This module defines the authentic character dimensions from SF3:3S.
These dimensions are used for hurtbox calculations and collision detection.

Reference: https://github.com/Grouflon/3rd_training_lua/blob/master/src/framedata.lua
All values are directly from the SF3:3S decompilation.

Dimensions:
- half_width: Half of the character's width (used for centered collision boxes)
- height: Character's total height from ground to top
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class CharacterDimensions:
    """Character-specific dimensions for SF3:3S"""
    half_width: int  # Half of character width (pixels)
    height: int      # Total character height (pixels)
    name: str        # Character name


# SF3:3S Authentic Character Dimensions
# Source: 3rd_training_lua framedata.lua character_specific table
SF3_CHARACTER_DIMENSIONS: Dict[str, CharacterDimensions] = {
    "alex": CharacterDimensions(half_width=45, height=104, name="Alex"),
    "chunli": CharacterDimensions(half_width=39, height=97, name="Chun-Li"),
    "dudley": CharacterDimensions(half_width=29, height=109, name="Dudley"),
    "elena": CharacterDimensions(half_width=44, height=88, name="Elena"),
    "gouki": CharacterDimensions(half_width=33, height=107, name="Gouki/Akuma"),
    "akuma": CharacterDimensions(half_width=33, height=107, name="Gouki/Akuma"),  # Alias
    "hugo": CharacterDimensions(half_width=43, height=137, name="Hugo"),
    "ibuki": CharacterDimensions(half_width=34, height=92, name="Ibuki"),
    "ken": CharacterDimensions(half_width=30, height=107, name="Ken"),
    "makoto": CharacterDimensions(half_width=42, height=90, name="Makoto"),
    "necro": CharacterDimensions(half_width=26, height=89, name="Necro"),
    "oro": CharacterDimensions(half_width=40, height=88, name="Oro"),
    "q": CharacterDimensions(half_width=25, height=130, name="Q"),
    "remy": CharacterDimensions(half_width=32, height=114, name="Remy"),
    "ryu": CharacterDimensions(half_width=31, height=101, name="Ryu"),
    "sean": CharacterDimensions(half_width=29, height=103, name="Sean"),
    "twelve": CharacterDimensions(half_width=33, height=91, name="Twelve"),
    "urien": CharacterDimensions(half_width=36, height=121, name="Urien"),
    "yang": CharacterDimensions(half_width=41, height=89, name="Yang"),
    "yun": CharacterDimensions(half_width=37, height=89, name="Yun"),
}


def get_character_dimensions(character_name: str) -> CharacterDimensions:
    """
    Get SF3:3S authentic dimensions for a character.

    Args:
        character_name: Character name (case insensitive)

    Returns:
        CharacterDimensions object with half_width and height

    Raises:
        KeyError: If character not found
    """
    name_lower = character_name.lower()

    if name_lower not in SF3_CHARACTER_DIMENSIONS:
        raise KeyError(f"Character '{character_name}' not found in SF3 dimensions database")

    return SF3_CHARACTER_DIMENSIONS[name_lower]


def get_default_hurtbox_for_character(character_name: str, is_crouching: bool = False) -> tuple:
    """
    Get default hurtbox dimensions for a character based on SF3 dimensions.

    Args:
        character_name: Character name
        is_crouching: Whether character is in crouching state

    Returns:
        Tuple of (offset_x, offset_y, width, height) for hurtbox
    """
    dims = get_character_dimensions(character_name)

    if is_crouching:
        # Crouching hurtbox is approximately 60% of standing height
        crouch_height = int(dims.height * 0.6)
        return (
            0,                      # offset_x (centered)
            -crouch_height,         # offset_y (from ground up)
            dims.half_width * 2,    # width (full character width)
            crouch_height           # height
        )
    else:
        # Standing hurtbox uses full character dimensions
        return (
            0,                      # offset_x (centered)
            -dims.height,           # offset_y (from ground up)
            dims.half_width * 2,    # width (full character width)
            dims.height             # height
        )


# Quick reference for implementation
AKUMA_DIMENSIONS = get_character_dimensions("akuma")
RYU_DIMENSIONS = get_character_dimensions("ryu")
KEN_DIMENSIONS = get_character_dimensions("ken")


if __name__ == "__main__":
    # Test the dimensions system
    print("SF3:3S Character Dimensions Test\n")

    # Test Akuma dimensions
    akuma_dims = get_character_dimensions("akuma")
    print(f"Akuma: half_width={akuma_dims.half_width}, height={akuma_dims.height}")
    print(f"  Full width: {akuma_dims.half_width * 2}")

    # Test hurtbox generation
    standing_hurtbox = get_default_hurtbox_for_character("akuma", is_crouching=False)
    crouching_hurtbox = get_default_hurtbox_for_character("akuma", is_crouching=True)

    print(f"\nAkuma Standing Hurtbox: {standing_hurtbox}")
    print(f"Akuma Crouching Hurtbox: {crouching_hurtbox}")

    # Show all characters
    print("\n\nAll SF3:3S Characters:")
    print("-" * 50)
    for char_id, dims in SF3_CHARACTER_DIMENSIONS.items():
        if char_id != "akuma":  # Skip alias
            print(f"{dims.name:15} | Width: {dims.half_width*2:3}px | Height: {dims.height:3}px")
