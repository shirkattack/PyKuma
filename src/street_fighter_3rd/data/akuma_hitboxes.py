"""
Akuma Hitbox and Frame Data
Based on SF3:3S frame data and hitbox measurements

This file defines the complete hitbox/hurtbox data for all of Akuma's moves.
All coordinates are relative to the character's position (x, y is at feet).

Frame timing reference:
- Startup: frames before hitbox becomes active
- Active: frames where hitbox can hit
- Recovery: frames after active before character can act
- Total: startup + active + recovery

Position reference:
- X offset: positive = forward, negative = backward
- Y offset: negative = up from ground, positive = down
"""

from dataclasses import dataclass
from typing import List, Tuple
from street_fighter_3rd.data.enums import HitType, CharacterState

@dataclass
class HitboxFrame:
    """Defines a hitbox for a specific frame or frame range"""
    offset_x: int  # X offset from character center (+ = forward)
    offset_y: int  # Y offset from ground (- = up, + = down)
    width: int
    height: int
    damage: int
    hitstun: int  # Frames of hitstun on hit
    blockstun: int  # Frames of blockstun on block
    hit_type: HitType = HitType.MID

@dataclass
class HurtboxFrame:
    """Defines character's hurtbox (vulnerable area)"""
    offset_x: int
    offset_y: int
    width: int
    height: int

@dataclass
class MoveFrameData:
    """Complete frame data for a move"""
    name: str
    state: CharacterState
    startup: int  # Frames before active
    active: List[int]  # List of active frame numbers (1-indexed)
    recovery: int  # Frames after active
    on_hit: int  # Frame advantage on hit
    on_block: int  # Frame advantage on block
    hitboxes: List[Tuple[List[int], HitboxFrame]]  # (active_frames, hitbox)
    hurtboxes: List[HurtboxFrame]  # Character's vulnerable areas


# ==========================================
# AKUMA STANDING NORMALS
# ==========================================

# Standing Light Punch (5LP / st.LP)
# Fast jab - primary pressure tool
AKUMA_ST_LP = MoveFrameData(
    name="Standing Light Punch",
    state=CharacterState.LIGHT_PUNCH,
    startup=3,
    active=[4, 5],  # Active on frames 4-5
    recovery=6,
    on_hit=+4,  # Advantage on hit
    on_block=+2,  # Advantage on block
    hitboxes=[
        ([4, 5], HitboxFrame(
            offset_x=45,
            offset_y=-70,
            width=50,
            height=35,
            damage=12,
            hitstun=12,
            blockstun=10,
            hit_type=HitType.HIGH
        ))
    ],
    hurtboxes=[
        HurtboxFrame(offset_x=0, offset_y=-60, width=40, height=60),  # Body
        HurtboxFrame(offset_x=30, offset_y=-70, width=25, height=20),  # Extended arm
    ]
)

# Standing Medium Punch (5MP / st.MP)
# Good poke - cancelable
AKUMA_ST_MP = MoveFrameData(
    name="Standing Medium Punch",
    state=CharacterState.MEDIUM_PUNCH,
    startup=5,
    active=[6, 7, 8],  # Active on frames 6-8
    recovery=10,
    on_hit=+5,
    on_block=+1,
    hitboxes=[
        ([6, 7, 8], HitboxFrame(
            offset_x=55,
            offset_y=-65,
            width=60,
            height=40,
            damage=18,
            hitstun=15,
            blockstun=12,
            hit_type=HitType.MID
        ))
    ],
    hurtboxes=[
        HurtboxFrame(offset_x=0, offset_y=-60, width=40, height=60),  # Body
        HurtboxFrame(offset_x=40, offset_y=-65, width=30, height=20),  # Extended arm
    ]
)

# Standing Heavy Punch (5HP / st.HP)
# Strong anti-air and combo ender
AKUMA_ST_HP = MoveFrameData(
    name="Standing Heavy Punch",
    state=CharacterState.HEAVY_PUNCH,
    startup=7,
    active=[8, 9, 10, 11],  # Active on frames 8-11
    recovery=17,
    on_hit=+8,
    on_block=-2,
    hitboxes=[
        ([8, 9, 10, 11], HitboxFrame(
            offset_x=40,
            offset_y=-85,
            width=55,
            height=50,
            damage=25,
            hitstun=18,
            blockstun=14,
            hit_type=HitType.HIGH
        ))
    ],
    hurtboxes=[
        HurtboxFrame(offset_x=0, offset_y=-60, width=40, height=60),  # Body
        HurtboxFrame(offset_x=35, offset_y=-85, width=30, height=30),  # Upper body/arm
    ]
)

# Standing Light Kick (5LK / st.LK)
# Fast low poke
AKUMA_ST_LK = MoveFrameData(
    name="Standing Light Kick",
    state=CharacterState.LIGHT_KICK,
    startup=4,
    active=[5, 6],  # Active on frames 5-6
    recovery=7,
    on_hit=+3,
    on_block=+1,
    hitboxes=[
        ([5, 6], HitboxFrame(
            offset_x=50,
            offset_y=-35,
            width=45,
            height=30,
            damage=14,
            hitstun=13,
            blockstun=11,
            hit_type=HitType.LOW
        ))
    ],
    hurtboxes=[
        HurtboxFrame(offset_x=0, offset_y=-60, width=40, height=60),  # Body
        HurtboxFrame(offset_x=40, offset_y=-35, width=30, height=15),  # Extended leg
    ]
)

# Standing Medium Kick (5MK / st.MK)
# Solid mid-range poke
AKUMA_ST_MK = MoveFrameData(
    name="Standing Medium Kick",
    state=CharacterState.MEDIUM_KICK,
    startup=6,
    active=[7, 8, 9],  # Active on frames 7-9
    recovery=11,
    on_hit=+6,
    on_block=+2,
    hitboxes=[
        ([7, 8, 9], HitboxFrame(
            offset_x=60,
            offset_y=-50,
            width=50,
            height=35,
            damage=20,
            hitstun=16,
            blockstun=13,
            hit_type=HitType.MID
        ))
    ],
    hurtboxes=[
        HurtboxFrame(offset_x=0, offset_y=-60, width=40, height=60),  # Body
        HurtboxFrame(offset_x=50, offset_y=-50, width=35, height=20),  # Extended leg
    ]
)

# Standing Heavy Kick (5HK / st.HK)
# Powerful kick - good range
AKUMA_ST_HK = MoveFrameData(
    name="Standing Heavy Kick",
    state=CharacterState.HEAVY_KICK,
    startup=9,
    active=[10, 11, 12, 13],  # Active on frames 10-13
    recovery=18,
    on_hit=+10,
    on_block=-3,
    hitboxes=[
        ([10, 11, 12, 13], HitboxFrame(
            offset_x=65,
            offset_y=-60,
            width=60,
            height=45,
            damage=28,
            hitstun=20,
            blockstun=15,
            hit_type=HitType.MID
        ))
    ],
    hurtboxes=[
        HurtboxFrame(offset_x=0, offset_y=-60, width=40, height=60),  # Body
        HurtboxFrame(offset_x=55, offset_y=-60, width=40, height=25),  # Extended leg
    ]
)

# ==========================================
# LOOKUP TABLE
# ==========================================

AKUMA_MOVE_DATA = {
    CharacterState.LIGHT_PUNCH: AKUMA_ST_LP,
    CharacterState.MEDIUM_PUNCH: AKUMA_ST_MP,
    CharacterState.HEAVY_PUNCH: AKUMA_ST_HP,
    CharacterState.LIGHT_KICK: AKUMA_ST_LK,
    CharacterState.MEDIUM_KICK: AKUMA_ST_MK,
    CharacterState.HEAVY_KICK: AKUMA_ST_HK,
}

def get_akuma_hitboxes(state: CharacterState, frame_number: int) -> List[HitboxFrame]:
    """
    Get active hitboxes for Akuma's current state and frame.

    Args:
        state: Current character state
        frame_number: Current frame in the state (1-indexed)

    Returns:
        List of active hitboxes for this frame
    """
    move_data = AKUMA_MOVE_DATA.get(state)
    if not move_data:
        return []

    active_hitboxes = []
    for active_frames, hitbox in move_data.hitboxes:
        if frame_number in active_frames:
            active_hitboxes.append(hitbox)

    return active_hitboxes

def get_akuma_hurtboxes(state: CharacterState) -> List[HurtboxFrame]:
    """
    Get hurtboxes for Akuma's current state.

    Args:
        state: Current character state

    Returns:
        List of hurtboxes (vulnerable areas)
    """
    move_data = AKUMA_MOVE_DATA.get(state)
    if move_data:
        return move_data.hurtboxes

    # Default standing hurtbox
    return [HurtboxFrame(offset_x=0, offset_y=-60, width=40, height=120)]

def get_move_frame_data(state: CharacterState) -> MoveFrameData | None:
    """Get complete frame data for a move"""
    return AKUMA_MOVE_DATA.get(state)
