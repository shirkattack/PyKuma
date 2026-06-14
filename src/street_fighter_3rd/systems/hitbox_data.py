"""Runtime hitbox data container used by the collision adapter.

This is a lightweight, mutable hitbox record produced from frame data at
collision time (distinct from the validated ``schemas.sf3_schemas.HitboxData``
and from the persistent ``SF3Hitbox``). It carries the per-attack values the
collision adapter needs while a hit is being resolved.
"""

from street_fighter_3rd.data.enums import HitType


class HitboxData:
    """Runtime hitbox data for an active attack."""

    def __init__(self, x: int, y: int, width: int, height: int, damage: int,
                 hitstun: int, hit_type: HitType = HitType.MID):
        """Initialize hitbox.

        Args:
            x, y: Position relative to character
            width, height: Hitbox dimensions
            damage: Damage dealt
            hitstun: Frames of hitstun on hit
            hit_type: Type of hit (high/mid/low)
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.damage = damage
        self.hitstun = hitstun
        self.hit_type = hit_type
        self.has_hit = False  # Track if this hitbox already connected
