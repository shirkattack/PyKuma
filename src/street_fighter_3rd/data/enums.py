"""Enumerations for game states, character states, and inputs."""

from enum import Enum, auto


class GameState(Enum):
    """Overall game state."""
    TITLE_SCREEN = auto()  # Press start to begin
    MAIN_MENU = auto()
    CHARACTER_SELECT = auto()
    STAGE_SELECT = auto()
    LOADING = auto()
    PRE_ROUND = auto()  # Round announcement, characters frozen
    FIGHTING = auto()  # Active gameplay
    ROUND_END = auto()  # K.O./Time Over display
    MATCH_END = auto()  # Winner announced
    CONTINUE_SCREEN = auto()  # Play again prompt
    PAUSE = auto()


class RoundResult(Enum):
    """Result of a round."""
    K_O = auto()  # One player's health depleted
    TIME_OVER = auto()  # Timer reached 0
    PERFECT = auto()  # Winner took no damage
    DOUBLE_K_O = auto()  # Both players K.O.'d simultaneously
    NONE = auto()  # Round still in progress


class CharacterState(Enum):
    """Character state machine states."""
    # Neutral states
    STANDING = auto()
    CROUCHING = auto()
    WALKING_FORWARD = auto()
    WALKING_BACKWARD = auto()

    # Air states
    JUMP_STARTUP = auto()  # Prejump frames (throw invulnerable)
    JUMPING = auto()
    JUMPING_FORWARD = auto()
    JUMPING_BACKWARD = auto()
    AIRBORNE = auto()
    LANDING = auto()

    # Dash states
    DASH_FORWARD = auto()
    DASH_BACKWARD = auto()

    # Attack states
    LIGHT_PUNCH = auto()
    MEDIUM_PUNCH = auto()
    HEAVY_PUNCH = auto()
    LIGHT_KICK = auto()
    MEDIUM_KICK = auto()
    HEAVY_KICK = auto()

    # Crouch attacks
    CROUCH_LIGHT_PUNCH = auto()
    CROUCH_MEDIUM_PUNCH = auto()
    CROUCH_HEAVY_PUNCH = auto()
    CROUCH_LIGHT_KICK = auto()
    CROUCH_MEDIUM_KICK = auto()
    CROUCH_HEAVY_KICK = auto()

    # Air attacks
    JUMP_LIGHT_PUNCH = auto()
    JUMP_MEDIUM_PUNCH = auto()
    JUMP_HEAVY_PUNCH = auto()
    JUMP_LIGHT_KICK = auto()
    JUMP_MEDIUM_KICK = auto()
    JUMP_HEAVY_KICK = auto()

    # Special moves (examples for Akuma)
    GOHADOKEN = auto()  # Fireball
    GOSHORYUKEN = auto()  # Dragon punch
    TATSUMAKI = auto()  # Hurricane kick
    ASHURA_SENKU = auto()  # Teleport

    # Super arts
    SUPER_ART_1 = auto()
    SUPER_ART_2 = auto()
    SUPER_ART_3 = auto()

    # Defensive states
    BLOCKING_HIGH = auto()
    BLOCKING_LOW = auto()
    BLOCKSTUN_HIGH = auto()
    BLOCKSTUN_LOW = auto()

    # Hit states
    HITSTUN_STANDING = auto()
    HITSTUN_CROUCHING = auto()
    HITSTUN_AIRBORNE = auto()
    KNOCKDOWN = auto()
    WAKEUP = auto()

    # Throw states
    THROW_STARTUP = auto()
    THROWING = auto()
    THROWN = auto()
    TECH_THROW = auto()

    # SF3 Parry states
    PARRY_HIGH = auto()
    PARRY_LOW = auto()
    PARRY_AIR = auto()
    PARRY_SUCCESS = auto()

    # Universal moves
    OVERHEAD = auto()  # MP+MK
    TAUNT = auto()  # Personal action


class InputDirection(Enum):
    """Directional inputs using numpad notation."""
    NEUTRAL = 5
    UP = 8
    UP_FORWARD = 9
    FORWARD = 6
    DOWN_FORWARD = 3
    DOWN = 2
    DOWN_BACK = 1
    BACK = 4
    UP_BACK = 7


class Button(Enum):
    """Attack buttons."""
    LIGHT_PUNCH = auto()
    MEDIUM_PUNCH = auto()
    HEAVY_PUNCH = auto()
    LIGHT_KICK = auto()
    MEDIUM_KICK = auto()
    HEAVY_KICK = auto()


class HitType(Enum):
    """Type of hit for collision detection."""
    HIGH = auto()  # Can be blocked standing
    LOW = auto()  # Must be blocked crouching
    MID = auto()  # Can be blocked either way
    OVERHEAD = auto()  # Must be blocked standing
    THROW = auto()  # Cannot be blocked
    PROJECTILE = auto()


class HitEffect(Enum):
    """Effects applied on successful hit."""
    NORMAL = auto()
    KNOCKDOWN = auto()
    JUGGLE = auto()
    WALL_BOUNCE = auto()
    GROUND_BOUNCE = auto()
    CRUMPLE = auto()


class FacingDirection(Enum):
    """Which way the character is facing."""
    LEFT = -1
    RIGHT = 1
