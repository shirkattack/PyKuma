"""Frame data structures for moves and animations."""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from street_fighter_3rd.data.enums import HitType, HitEffect, CharacterState


@dataclass
class HitBox:
    """Represents an offensive hitbox (attack area)."""
    x: int  # Relative to character position
    y: int
    width: int
    height: int
    damage: int
    hitstun: int  # Frames of hitstun on hit
    blockstun: int  # Frames of blockstun on block
    hit_type: HitType
    hit_effect: HitEffect
    pushback: int = 10  # Pushback on hit/block
    chip_damage: int = 0  # Damage through block
    stun_damage: int = 0  # Stun meter damage


@dataclass
class HurtBox:
    """Represents a vulnerable area (can be hit)."""
    x: int  # Relative to character position
    y: int
    width: int
    height: int


@dataclass
class FrameData:
    """Frame data for a single animation frame."""
    duration: int  # How many game frames this animation frame lasts
    sprite_index: int  # Index into sprite sheet
    hitboxes: List[HitBox] = field(default_factory=list)
    hurtboxes: List[HurtBox] = field(default_factory=list)
    offset_x: int = 0  # Visual offset from position
    offset_y: int = 0


@dataclass
class MoveData:
    """Complete data for a move/attack."""
    name: str
    state: CharacterState
    frames: List[FrameData]
    startup: int  # Frames before hitbox becomes active
    active: int  # Frames hitbox is active
    recovery: int  # Frames after active before can act again
    on_hit: int  # Frame advantage on hit (+ is advantageous)
    on_block: int  # Frame advantage on block
    damage: int
    meter_gain: int = 5
    meter_cost: int = 0
    cancellable: bool = False  # Can cancel into special/super
    cancel_window_start: int = 0  # Frame when cancelling becomes possible
    cancel_window_end: int = 0

    @property
    def total_frames(self) -> int:
        """Total frames for the move."""
        return sum(frame.duration for frame in self.frames)

    @property
    def frame_advantage_hit(self) -> int:
        """Frame advantage on hit."""
        return self.on_hit

    @property
    def frame_advantage_block(self) -> int:
        """Frame advantage on block."""
        return self.on_block


# Example move data for testing (will be replaced with actual data)
def create_sample_jab() -> MoveData:
    """Create sample light punch data."""
    return MoveData(
        name="Light Punch",
        state=CharacterState.LIGHT_PUNCH,
        frames=[
            FrameData(duration=3, sprite_index=0),  # Startup
            FrameData(
                duration=2,
                sprite_index=1,
                hitboxes=[
                    HitBox(
                        x=30, y=-60, width=40, height=20,
                        damage=10, hitstun=12, blockstun=8,
                        hit_type=HitType.HIGH,
                        hit_effect=HitEffect.NORMAL,
                        stun_damage=5
                    )
                ],
                hurtboxes=[
                    HurtBox(x=0, y=-80, width=50, height=80)
                ]
            ),  # Active
            FrameData(duration=6, sprite_index=2),  # Recovery
        ],
        startup=3,
        active=2,
        recovery=6,
        on_hit=+4,  # +4 on hit
        on_block=+1,  # +1 on block
        damage=10,
        cancellable=True,
        cancel_window_start=4,
        cancel_window_end=5
    )
