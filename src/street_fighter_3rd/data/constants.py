"""Game constants and configuration values."""

# Display settings
SCREEN_WIDTH = 896  # Match stage background width
SCREEN_HEIGHT = 512  # Match stage background height
FPS = 60  # Fighting games run at 60 FPS (non-negotiable)
WINDOW_TITLE = "Street Fighter Third Strike - Python Edition"

# Sprites are drawn at this scale from their native frame size. Single source of
# truth: the sprite renderer AND the debug hitbox overlay both use it, so boxes
# (stored in ROM-native ~107px units) line up with the on-screen sprite.
SPRITE_SCALE = 2.0

# Stage boundaries
STAGE_LEFT_BOUND = 80
STAGE_RIGHT_BOUND = SCREEN_WIDTH - 80
STAGE_FLOOR = 344  # Character Y position (sprite.bottom = 344 + 136 = 480, leaving 32px from screen bottom)

# Physics — ROM-derived (see data/characters/akuma/physics.yaml; captured from
# sfiii3nr1 live memory). Symmetric 60 FPS jump tuned to the measured apex (~83px)
# and air time (~44f): vy0 = 4*apex/airborne, gravity = 2*vy0/airborne.
GRAVITY = 0.34          # was 0.8 (jump used to be ~2x too tall)
JUMP_VELOCITY = -7.5    # was -16.0 -> apex ~83, airborne ~44 frames
WALK_SPEED = 3.0        # matches the ROM walk speed
DASH_SPEED = 6.0

# Input system
INPUT_BUFFER_SIZE = 60  # Store last 60 frames (1 second at 60 FPS)
MOTION_INPUT_WINDOW = 16  # Frames to complete a motion input (e.g., 236P) - slightly lenient for pad/keyboard
NEGATIVE_EDGE_ENABLED = True  # Allow specials on button release

# Parry system (SF3 specific)
PARRY_WINDOW_GROUND = 10  # Frames to input ground parry
PARRY_WINDOW_GROUND_HELD = 6  # Frames if direction is held
PARRY_WINDOW_AIR = 7  # Frames for air parry
PARRY_FREEZE_FRAMES = 16  # Both characters freeze on successful parry
PARRY_COOLDOWN_GROUND = 23  # Frames before another parry
PARRY_COOLDOWN_AIR = 20
PARRY_AUTO_WINDOW = 2  # Auto-parry additional hits within this window

# Throw system
THROW_STARTUP_FRAMES = 3
THROW_ACTIVE_FRAMES = 1
THROW_TECH_WINDOW = 5  # Frames to tech a throw
THROW_RANGE = 40  # Pixels

# Frame advantage
BLOCKSTUN_MULTIPLIER = 0.7  # Blockstun is typically less than hitstun
HITSTUN_BASE = 12  # Base hitstun in frames
CROUCH_HIT_DAMAGE_MULTIPLIER = 1.25  # 25% more damage when hit crouching

# Blocking
CHIP_DAMAGE_MULTIPLIER = 0.1  # 10% damage on block (chip damage)

# Damage scaling
COMBO_SCALING_START = 2  # Start scaling after 2nd hit
COMBO_SCALING_FACTOR = 0.9  # Each hit does 90% of previous
MIN_DAMAGE_SCALING = 0.1  # Minimum 10% damage

# Health and meter
MAX_HEALTH = 1050  # SF3 vitality scale (matches the Baston damage values, e.g. MP=115 ~ 11%)
MAX_SUPER_METER = 100
SUPER_METER_GAIN_ON_HIT = 5
SUPER_METER_GAIN_ON_BLOCK = 2
SUPER_METER_GAIN_ON_WHIFF = 1

# Round system
ROUND_TIMER_START = 99  # Starting timer value
TIMER_FRAME_DURATION = 55  # Frames per in-game second (at 60 FPS)
ROUNDS_TO_WIN = 2  # Best of 3 rounds
PRE_ROUND_FREEZE_FRAMES = 90  # Frames before "FIGHT!" (1.5 seconds)
ROUND_END_HOLD_FRAMES = 120  # Frames to display round result (2 seconds)
MATCH_END_HOLD_FRAMES = 180  # Frames to display match winner (3 seconds)

# Stun system
MAX_STUN = 100  # Varies by character
STUN_RECOVERY_RATE = 1  # Stun recovers per frame when not hit
STUN_TIME = 180  # Frames when stunned (3 seconds)

# Camera
CAMERA_ZOOM_MIN = 0.7
CAMERA_ZOOM_MAX = 1.0
CAMERA_ZOOM_SPEED = 0.05
CAMERA_FOLLOW_SPEED = 0.1

# Visual effects
HIT_FREEZE_FRAMES = 8  # Brief pause on hit for impact
SCREEN_SHAKE_DURATION = 6
SCREEN_SHAKE_INTENSITY = 4

# Colors (RGB)
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (255, 0, 0)
COLOR_BLUE = (0, 0, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_YELLOW = (255, 255, 0)
COLOR_HEALTH_BAR = (220, 50, 50)
COLOR_SUPER_METER = (255, 215, 0)
COLOR_STUN_BAR = (100, 100, 100)

# Debug settings
DEBUG_MODE = False  # Set to True for development/debugging
SHOW_HITBOXES = True
SHOW_FRAME_DATA = True
SHOW_INPUT_DISPLAY = True
