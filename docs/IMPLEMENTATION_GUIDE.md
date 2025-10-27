# Implementation Guide - Adding Akuma's Moves

**Purpose**: Step-by-step guide for implementing each move from frame data to working code.

**Prerequisites**:
- Read `AKUMA_FRAME_DATA.md` for complete frame data
- Read `CLAUDE.md` for project conventions
- Sprites must be extracted to `assets/sprites/akuma/sprite_sheets/`

---

## Implementation Checklist Template

For each move, follow this 5-step process:

### Step 1: Get Sprites
- [ ] Download GIF from justnopoint.com
- [ ] Extract frames using `tools/sprite_extraction/extract_gif_to_pngs.py`
- [ ] Flip sprites if needed using `tools/sprite_extraction/fix_sprite_flip.py`
- [ ] Verify sprites face LEFT by default

### Step 2: Add Animation (in `akuma.py`)
- [ ] Add sprite sequence to `_setup_animations()`
- [ ] Calculate appropriate `frame_duration` (typically 1-3)
- [ ] Set `loop=False` for attacks, `loop=True` for idle animations

### Step 3: Define Hitbox Data (in `collision.py`)
- [ ] Add case to `_get_active_hitboxes()`
- [ ] Set startup frame (when hitbox becomes active)
- [ ] Set active frame range
- [ ] Define hitbox position (x, y, width, height)
- [ ] Set damage value
- [ ] Set hitstun frames
- [ ] Set hit_type (HIGH, LOW, MID)
- [ ] Add special properties (knockdown, overhead, etc.)

### Step 4: Wire Input Detection (in `character.py`)
- [ ] Add button mapping to `_check_normal_attacks()`
- [ ] Check appropriate state requirements (standing, crouching, jumping)
- [ ] Add state transition call

### Step 5: Test
- [ ] Run game with `uv run sf3`
- [ ] Enable debug mode in `constants.py`
- [ ] Verify hitbox appears on correct frames
- [ ] Verify damage is correct
- [ ] Verify animation looks smooth
- [ ] Test against blocking opponent
- [ ] Test frame advantage

---

## Example: Standing Medium Punch

Let's walk through implementing Standing Medium Punch as a complete example.

### Frame Data (from AKUMA_FRAME_DATA.md)
```
Close Standing Medium Punch (c.s.MP)
- Startup: 5 frames
- Active: 4 frames (frames 5-8)
- Recovery: 9 frames
- Total: 18 frames
- Damage: 18
- Guard: HIGH
- Special cancelable
```

### Step 1: Get Sprites

```bash
# Download akuma-mp.gif from justnopoint.com
curl -O https://www.justnopoint.com/zweifuss/akuma/gifs/akuma-mp.gif

# Run analysis to see frame count
python tools/sprite_extraction/analyze_frames.py akuma-mp.gif
# Output: 18 frames detected

# Extract to numbered PNGs (continuing sprite numbering from last sprite)
# Assume last sprite was 18439, so start at 18440
python tools/sprite_extraction/extract_gif_to_pngs.py akuma-mp.gif 18440

# Verify orientation
# If sprites face RIGHT, flip them:
python tools/sprite_extraction/fix_sprite_flip.py 18440 18457
```

### Step 2: Add Animation

Edit `src/street_fighter_3rd/characters/akuma.py`:

```python
def _setup_animations(self):
    # ... existing animations ...

    # Standing Medium Punch (18 frames)
    # Frame duration: 1 for startup/active, 2 for recovery (makes it feel snappier)
    standing_mp_anim = create_simple_animation(
        # Sprites 18440-18457 (18 frames total)
        [18440, 18441, 18442, 18443, 18444,  # Frames 1-5 (startup)
         18445, 18446, 18447, 18448,          # Frames 6-9 (active)
         18449, 18450, 18451, 18452, 18453,   # Frames 10-14 (recovery)
         18454, 18455, 18456, 18457],         # Frames 15-18 (recovery)
        frame_duration=1,  # Each sprite shows for 1 game frame
        loop=False
    )
    self.animation_controller.add_animation("standing_medium_punch", standing_mp_anim)
```

### Step 3: Define Hitbox Data

Edit `src/street_fighter_3rd/systems/collision.py`:

```python
def _get_active_hitboxes(self, character) -> List[HitboxData]:
    """Get hitboxes that are currently active based on character state and frame."""
    hitboxes = []

    # ... existing hitbox definitions ...

    elif character.state == CharacterState.STANDING_MEDIUM_PUNCH:
        # Active frames: 5-8 (state_frame starts at 0, so frames 4-7)
        if 4 <= character.state_frame <= 7:
            hitbox_data = HitboxData(
                # Hitbox position relative to character
                x=45,      # 45 pixels in front of character
                y=-70,     # 70 pixels above feet (chest height)
                width=60,  # Wider than light punch
                height=40, # Taller hitbox

                # Combat properties
                damage=18,
                hitstun=15,  # Longer than light punch (5+15=20 frame advantage)
                blockstun=12,  # On block: 5+12=17, attacker recovers at 18 = -1 on block
                hit_type=HitType.HIGH,

                # Special properties
                properties={
                    'special_cancelable': True,  # Can cancel into special moves
                    'knockback': 15,  # Pushes opponent back 15 pixels
                }
            )
            hitboxes.append(hitbox_data)

    return hitboxes
```

### Step 4: Wire Input Detection

Edit `src/street_fighter_3rd/characters/character.py`:

```python
def _check_normal_attacks(self, buttons: Dict[str, bool]):
    """Check for normal attack button presses."""

    # Can only attack in certain states
    if self.state not in [CharacterState.STANDING, CharacterState.CROUCHING,
                          CharacterState.JUMPING, CharacterState.WALKING_FORWARD,
                          CharacterState.WALKING_BACKWARD]:
        return

    # ... existing light punch code ...

    # Medium Punch
    if buttons.get('MP', False):
        if self.state in [CharacterState.STANDING, CharacterState.WALKING_FORWARD,
                         CharacterState.WALKING_BACKWARD]:
            # Standing medium punch
            self._transition_to_state(CharacterState.STANDING_MEDIUM_PUNCH)
            return
        elif self.state == CharacterState.CROUCHING:
            # Crouching medium punch (implement later)
            self._transition_to_state(CharacterState.CROUCHING_MEDIUM_PUNCH)
            return
```

And add the state transition in `_transition_to_state()`:

```python
def _transition_to_state(self, new_state: CharacterState):
    """Transition to a new character state."""

    # ... existing code ...

    elif new_state == CharacterState.STANDING_MEDIUM_PUNCH:
        self.animation_controller.play_animation("standing_medium_punch", force_restart=True)
```

### Step 5: Add the State Enum

Edit `src/street_fighter_3rd/data/enums.py`:

```python
class CharacterState(Enum):
    # ... existing states ...
    STANDING_LIGHT_PUNCH = "standing_light_punch"
    STANDING_MEDIUM_PUNCH = "standing_medium_punch"  # ADD THIS
    # ... rest of states ...
```

### Step 6: Test

```bash
# Run game
uv run sf3

# Enable debug mode (if not already)
# Edit src/street_fighter_3rd/data/constants.py:
# DEBUG_MODE = True
# SHOW_HITBOXES = True

# Test checklist:
# 1. Press K (medium punch) as Player 1
# 2. Verify animation plays (18 frames)
# 3. Verify RED hitbox appears on frames 5-8
# 4. Hit opponent and verify 18 damage dealt
# 5. Hit opponent and verify they're pushed back
# 6. Test blocking - verify blockstun
# 7. Try canceling into Hadouken (when implemented)
```

---

## Quick Reference: Character States

Add these to `enums.py` as you implement moves:

```python
class CharacterState(Enum):
    # Idle
    STANDING = "standing"
    CROUCHING = "crouching"

    # Movement
    WALKING_FORWARD = "walking_forward"
    WALKING_BACKWARD = "walking_backward"
    JUMP_STARTUP = "jump_startup"
    JUMPING = "jumping"
    JUMP_LANDING = "jump_landing"

    # Standing Normals
    STANDING_LIGHT_PUNCH = "standing_light_punch"      # ✅ DONE
    STANDING_MEDIUM_PUNCH = "standing_medium_punch"    # Next
    STANDING_HEAVY_PUNCH = "standing_heavy_punch"
    STANDING_LIGHT_KICK = "standing_light_kick"
    STANDING_MEDIUM_KICK = "standing_medium_kick"
    STANDING_HEAVY_KICK = "standing_heavy_kick"

    # Crouching Normals
    CROUCHING_LIGHT_PUNCH = "crouching_light_punch"
    CROUCHING_MEDIUM_PUNCH = "crouching_medium_punch"
    CROUCHING_HEAVY_PUNCH = "crouching_heavy_punch"
    CROUCHING_LIGHT_KICK = "crouching_light_kick"
    CROUCHING_MEDIUM_KICK = "crouching_medium_kick"
    CROUCHING_HEAVY_KICK = "crouching_heavy_kick"

    # Jump Normals
    JUMP_LIGHT_PUNCH = "jump_light_punch"
    JUMP_MEDIUM_PUNCH = "jump_medium_punch"
    JUMP_HEAVY_PUNCH = "jump_heavy_punch"
    JUMP_LIGHT_KICK = "jump_light_kick"
    JUMP_MEDIUM_KICK = "jump_medium_kick"
    JUMP_HEAVY_KICK = "jump_heavy_kick"

    # Special Moves
    GOHADOKEN = "gohadoken"
    GOSHORYUKEN = "goshoryuken"
    TATSUMAKI = "tatsumaki"
    DEMON_FLIP = "demon_flip"

    # Special States
    HITSTUN = "hitstun"
    BLOCKSTUN = "blockstun"
    KNOCKDOWN = "knockdown"
    WAKEUP = "wakeup"
    THROW = "throw"
    THROWN = "thrown"
```

---

## Common Hitbox Positions (Reference)

Based on Akuma's sprite dimensions (approximate, adjust per move):

```python
# Standing attacks (character feet at y=0)
HEAD_HEIGHT = -90    # Head punches
CHEST_HEIGHT = -70   # Most punches
WAIST_HEIGHT = -50   # Low punches, high kicks
KNEE_HEIGHT = -30    # Mid kicks
FOOT_HEIGHT = -10    # Low kicks

# Horizontal positions (character facing RIGHT)
CLOSE_RANGE = 30     # Very close attacks
MID_RANGE = 50       # Most attacks
FAR_RANGE = 70       # Extended attacks
VERY_FAR = 90        # Longest range pokes

# Typical hitbox sizes
LIGHT_WIDTH = 40
LIGHT_HEIGHT = 30

MEDIUM_WIDTH = 60
MEDIUM_HEIGHT = 40

HEAVY_WIDTH = 80
HEAVY_HEIGHT = 50

SWEEP_WIDTH = 100
SWEEP_HEIGHT = 30
```

---

## Button Mapping Reference

Current button layout (from `input_system.py`):

### Player 1 (Keyboard):
- `J` = Light Punch (LP)
- `K` = Medium Punch (MP)
- `L` = Heavy Punch (HP)
- `U` = Light Kick (LK)
- `I` = Medium Kick (MK)
- `O` = Heavy Kick (HK)

### Player 2 (Numpad):
- `NumPad 1` = LP
- `NumPad 2` = MP
- `NumPad 3` = HP
- `NumPad 4` = LK
- `NumPad 5` = MK
- `NumPad 6` = HK

---

## Special Move Implementation (Complex)

Special moves require additional systems. Here's the roadmap:

### 1. Projectile System (for Gohadoken)

Create `src/street_fighter_3rd/systems/projectile.py`:

```python
class Projectile:
    def __init__(self, x, y, velocity_x, damage, owner):
        self.x = x
        self.y = y
        self.velocity_x = velocity_x
        self.damage = damage
        self.owner = owner
        self.active = True
        self.hitbox = HitboxData(...)

    def update(self):
        self.x += self.velocity_x
        # Check if off screen
        # Check collision with opponent

    def render(self, screen):
        # Draw projectile sprite

class ProjectileManager:
    def __init__(self):
        self.projectiles = []

    def spawn_hadoken(self, character, strength):
        # Create projectile based on character position
        # LP = slow, MP = medium, HP = fast

    def update(self):
        # Update all projectiles
        # Remove inactive ones

    def check_collision(self, opponent):
        # Check if any projectile hits opponent
```

### 2. Invincibility Frames (for Goshoryuken)

Add to `Character` class in `character.py`:

```python
class Character:
    def __init__(self):
        # ... existing ...
        self.invincible = False
        self.invincibility_frames = 0

    def update(self):
        # ... existing ...

        # Update invincibility
        if self.invincibility_frames > 0:
            self.invincibility_frames -= 1
            self.invincible = True
        else:
            self.invincible = False

    def set_invincible(self, frames):
        """Make character invincible for N frames."""
        self.invincibility_frames = frames
        self.invincible = True
```

Then in `_transition_to_state()`:

```python
elif new_state == CharacterState.GOSHORYUKEN:
    # Goshoryuken has invincibility on startup
    self.set_invincible(5)  # 5 frames invincible
    self.animation_controller.play_animation("goshoryuken_lp", force_restart=True)
```

And in collision detection (`collision.py`):

```python
def check_collision(self, attacker, defender):
    # ... existing code ...

    # Check if defender is invincible
    if defender.invincible:
        return  # No hit

    # ... rest of collision code ...
```

### 3. Knockdown System

Add states to `enums.py`:

```python
class CharacterState(Enum):
    # ... existing ...
    KNOCKDOWN = "knockdown"          # Falling down
    LYING_DOWN = "lying_down"        # On ground, invincible
    WAKEUP = "wakeup"                # Standing up
```

Add to `Character` class:

```python
def _handle_knockdown(self):
    """Handle knockdown state progression."""
    if self.state == CharacterState.KNOCKDOWN:
        # Fall to ground
        if self.state_frame >= 15:  # 15 frames to hit ground
            self._transition_to_state(CharacterState.LYING_DOWN)

    elif self.state == CharacterState.LYING_DOWN:
        # Lying on ground, invincible
        self.invincible = True
        if self.state_frame >= 30:  # 30 frames lying down
            self._transition_to_state(CharacterState.WAKEUP)

    elif self.state == CharacterState.WAKEUP:
        # Standing up
        self.invincible = False
        if self.state_frame >= 20:  # 20 frames to stand
            self._transition_to_state(CharacterState.STANDING)
```

---

## Testing Guidelines

### Frame-by-Frame Verification

To verify frame data accuracy:

1. Enable debug mode
2. Record gameplay with OBS or similar
3. Play back at 0.25x speed
4. Count frames manually:
   - First frame of startup
   - First frame hitbox appears (active)
   - Last frame hitbox exists
   - Frame character can act again

### Hitbox Visualization

With `SHOW_HITBOXES = True`:
- **RED boxes** = Hitboxes (attack boxes)
- **BLUE boxes** = Hurtboxes (vulnerable boxes)
- Hitboxes should only appear during active frames
- Hitboxes should align with sprite's attack visuals

### Damage Testing

```python
# Test damage calculation
opponent_health_before = opponent.health
# Land attack
opponent_health_after = opponent.health
damage_dealt = opponent_health_before - opponent_health_after
assert damage_dealt == expected_damage, f"Expected {expected_damage}, got {damage_dealt}"
```

---

## Performance Optimization

### Sprite Caching

Sprites are cached automatically in `SpriteManager`. Don't load sprites every frame.

### Hitbox Pooling

For projectiles, consider object pooling:

```python
class ProjectilePool:
    def __init__(self, size=10):
        self.pool = [Projectile(...) for _ in range(size)]
        self.active = []

    def get(self):
        if len(self.pool) > 0:
            proj = self.pool.pop()
            self.active.append(proj)
            return proj
        return None  # Pool exhausted

    def return_to_pool(self, projectile):
        projectile.reset()
        self.active.remove(projectile)
        self.pool.append(projectile)
```

---

## Implementation Order (Recommended)

Follow the TIER 1 priority from the improvement roadmap:

### Week 1: Standing Normals (6 moves)
1. ✅ Standing Light Punch (DONE)
2. Standing Medium Punch
3. Standing Heavy Punch
4. Standing Light Kick
5. Standing Medium Kick
6. Standing Heavy Kick

### Week 2: Crouching Normals (6 moves)
7. Crouching Light Punch
8. Crouching Medium Punch
9. Crouching Heavy Punch
10. Crouching Light Kick
11. Crouching Medium Kick
12. Crouching Heavy Kick (needs knockdown system)

### Week 3: Jump Normals (6 moves)
13. Jump Light Punch
14. Jump Medium Punch
15. Jump Heavy Punch
16. Jump Light Kick
17. Jump Medium Kick
18. Jump Heavy Kick

### Week 4-5: Special Moves (3 moves + systems)
19. Build projectile system
20. Gohadoken (QCF+P)
21. Build invincibility system
22. Goshoryuken (DP+P)
23. Build knockdown system
24. Tatsumaki (QCB+K)

---

## Common Pitfalls

### 1. Sprite Numbering Gaps
Some sprite sequences from justnopoint.com have gaps (missing numbers). Skip those in your animation arrays.

```python
# WRONG - includes missing sprite
[18283, 18284, 18285, 18286, 18287, 18288]

# CORRECT - skips missing sprites 18286-18287
[18283, 18284, 18285, 18288, 18289, 18290]
```

### 2. Frame Timing Off-by-One
`state_frame` starts at 0, not 1!

```python
# If active frames are 5-8 in frame data:
# WRONG
if 5 <= character.state_frame <= 8:

# CORRECT (frame data uses 1-indexed, code uses 0-indexed)
if 4 <= character.state_frame <= 7:
```

### 3. Forgetting to Flip Sprites
All sprites must face LEFT by default. New sprites from GIFs often face RIGHT.

```bash
# Always check and flip if needed
python tools/sprite_extraction/fix_sprite_flip.py <start> <end>
```

### 4. Hitbox Positioning
Remember: X is relative to character center, Y is relative to character feet (y=0 at ground).

```python
# Standing character attacking in front
x=50   # 50 pixels in front (correct)
y=-70  # 70 pixels above feet (correct)

# NOT absolute screen coordinates!
```

### 5. State Transitions
Always return after transitioning to prevent multiple transitions in one frame.

```python
# CORRECT
if buttons.get('MP'):
    self._transition_to_state(CharacterState.STANDING_MEDIUM_PUNCH)
    return  # IMPORTANT - prevents other attacks from triggering

if buttons.get('HP'):
    self._transition_to_state(CharacterState.STANDING_HEAVY_PUNCH)
    return
```

---

## Next Steps

Ready to start implementing? Follow this exact process:

1. Read `AKUMA_FRAME_DATA.md` for the move you want to implement
2. Follow the 5-step template above
3. Test thoroughly with debug mode enabled
4. Verify frame data matches SF3:3S
5. Move on to next move

**Start with Standing Medium Punch** - it's straightforward and follows the same pattern as Light Punch (already done).

---

**Last Updated**: 2025-10-11
