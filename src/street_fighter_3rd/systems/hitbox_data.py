"""Runtime hitbox data shared by the collision pipeline."""

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
