# Blocking System Implementation Plan

**Date:** 2025-10-15
**Status:** Ready to implement
**Estimated Time:** 3-4 hours

---

## Executive Summary

Implement a complete blocking system before adding more attacks. This ensures all future attacks (crouching, jumping, overhead) can be properly blocked with the correct mechanics.

---

## Current State

### ✅ What Exists
- **State enums**: `BLOCKING_HIGH`, `BLOCKING_LOW`, `BLOCKSTUN_HIGH`, `BLOCKSTUN_LOW`
- **Basic detection**: Checks if player holds back while standing/crouching
- **Frame counter**: `blockstun_frames` decrements each frame
- **Blockstun application**: Transitions to blockstun state, calculates frames
- **Sprite assets**: `akuma-block`, `akuma-block-crouch`, `akuma-block-high`

### ❌ What's Missing
- Block animations not wired to states
- No high/low attack classification system
- No overhead attack handling
- No chip damage on block
- No pushback on block
- Missing visual feedback

---

## Implementation Phases

### **Phase 1: Core Blocking System** (MUST HAVE)
Build the fundamental blocking mechanics that all attacks will use.

#### **Task 1.1: High/Low Attack Classification**
**Goal:** Every attack must specify what type of block it requires

**Implementation:**
```python
# Already exists in enums.py:
class HitType(Enum):
    HIGH = auto()      # Must block standing (most standing attacks)
    LOW = auto()       # Must block crouching (sweeps, low pokes)
    MID = auto()       # Can block either way (some pokes)
    OVERHEAD = auto()  # Must block standing (overhead attacks)
    THROW = auto()     # Cannot be blocked
    PROJECTILE = auto()
```

**Changes Required:**
1. Add `hit_type: HitType` to all hitbox definitions in `collision.py`
2. Classify all existing attacks:
   - **Standing normals** → `HIGH` (LP, MP, HP, LK, MK, HK)
   - **Crouching normals** → `LOW` (cr.LP, cr.MP, cr.HP, cr.LK, cr.MK, cr.HK)
   - **Jumping normals** → `HIGH` (all air attacks)
   - **Projectiles** → `MID` or `PROJECTILE` (fireballs)
   - **Special moves** → Case-by-case (DP = HIGH, sweep = LOW)

**Files Modified:**
- `src/street_fighter_3rd/systems/collision.py` (all `_get_active_hitboxes()` hitbox definitions)

**Testing:**
- Verify each attack shows correct hit_type in debug
- Check that classification makes sense

---

#### **Task 1.2: High/Low Blocking Logic**
**Goal:** Blocking only works if using correct block type for attack type

**Current Logic (Too Permissive):**
```python
# collision.py:346
if is_blocking and defender.state in [CharacterState.STANDING, CharacterState.CROUCHING]:
    return True  # Blocks everything!
```

**New Logic (Correct):**
```python
def _is_blocking(self, defender, hitbox: HitboxData) -> bool:
    """Check if defender is blocking the attack."""
    if not defender.input:
        return False

    direction = defender.input.get_direction()

    # Check if holding back
    if defender.is_facing_right():
        holding_back = direction in [InputDirection.BACK, InputDirection.DOWN_BACK]
    else:
        holding_back = direction in [InputDirection.FORWARD, InputDirection.DOWN_FORWARD]

    if not holding_back:
        return False

    # Check block type vs attack type
    defender_state = defender.state
    attack_type = hitbox.hit_type

    # Standing block
    if defender_state == CharacterState.STANDING:
        # Can block: HIGH, MID, OVERHEAD
        # Cannot block: LOW
        if attack_type == HitType.LOW:
            return False  # Low attack hits standing block!
        return attack_type in [HitType.HIGH, HitType.MID, HitType.OVERHEAD]

    # Crouching block
    elif defender_state == CharacterState.CROUCHING:
        # Can block: LOW, MID
        # Cannot block: HIGH, OVERHEAD
        if attack_type in [HitType.HIGH, HitType.OVERHEAD]:
            return False  # Overhead/high hits crouching block!
        return attack_type in [HitType.LOW, HitType.MID]

    return False
```

**Files Modified:**
- `src/street_fighter_3rd/systems/collision.py` (`_is_blocking()` method)

**Testing:**
- Standing block should block standing punch (HIGH) ✅
- Standing block should NOT block crouching kick (LOW) ❌
- Crouching block should block crouching kick (LOW) ✅
- Crouching block should NOT block standing punch (HIGH) ❌
- Either block should work for MID attacks ✅

---

#### **Task 1.3: Block Animations**
**Goal:** Show proper block animation when in blockstun

**Sprite Loading:**
```python
# In akuma.py _setup_animations()
# Load from extracted sprite folders
standing_block_anim = self._load_animation_from_folder("akuma-block")
crouch_block_anim = self._load_animation_from_folder("akuma-block-crouch")

self.animation_controller.add_animation("standing_block", standing_block_anim)
self.animation_controller.add_animation("crouch_block", crouch_block_anim)
```

**Animation Playback:**
```python
# In character.py _transition_to_state()
elif new_state == CharacterState.BLOCKSTUN_HIGH:
    self.animation_controller.play_animation("standing_block")
elif new_state == CharacterState.BLOCKSTUN_LOW:
    self.animation_controller.play_animation("crouch_block")
```

**Helper Method:**
```python
# In akuma.py
def _load_animation_from_folder(self, folder_name: str) -> Animation:
    """Load animation from extracted sprite folder.

    Args:
        folder_name: Name of folder in tools/sprite_extraction/akuma_animations/

    Returns:
        Animation object with all frames loaded
    """
    folder_path = f"tools/sprite_extraction/akuma_animations/{folder_name}"
    frame_files = sorted(glob.glob(f"{folder_path}/frame_*.png"))

    sprite_ids = []
    for frame_file in frame_files:
        # Load and add to sprite manager
        sprite_id = self.sprite_manager.load_sprite(frame_file)
        sprite_ids.append(sprite_id)

    return create_simple_animation(sprite_ids, frame_duration=2, loop=True)
```

**Files Modified:**
- `src/street_fighter_3rd/characters/akuma.py` (`_setup_animations()`, new helper method)
- `src/street_fighter_3rd/characters/character.py` (`_transition_to_state()`)

**Testing:**
- Block an attack while standing → see standing block animation ✅
- Block an attack while crouching → see crouch block animation ✅
- Animation loops if blockstun is long ✅

---

#### **Task 1.4: Chip Damage**
**Goal:** Blocking reduces but doesn't eliminate damage

**Constants:**
```python
# In constants.py
CHIP_DAMAGE_MULTIPLIER = 0.1  # 10% damage on block
```

**Implementation:**
```python
# In collision.py when block detected:
if self._is_blocking(defender, hitbox):
    # Calculate chip damage (10% of normal damage)
    chip_damage = int(hitbox.damage * CHIP_DAMAGE_MULTIPLIER)
    defender.health -= chip_damage

    # Apply blockstun
    blockstun = int(hitbox.hitstun * BLOCKSTUN_MULTIPLIER)
    defender.blockstun_frames = blockstun

    # Transition to blockstun state
    if defender.state == CharacterState.STANDING:
        defender._transition_to_state(CharacterState.BLOCKSTUN_HIGH)
    else:
        defender._transition_to_state(CharacterState.BLOCKSTUN_LOW)

    print(f"BLOCKED! Chip: {chip_damage}, Blockstun: {blockstun}f")

    # Apply blockstun hit freeze (half of normal)
    blockfreeze = hitfreeze // 2
    attacker.hitfreeze_frames = blockfreeze
    defender.hitfreeze_frames = blockfreeze

    # Spawn block spark VFX
    hit_x = (attacker_hitbox.left + attacker_hitbox.right) // 2
    hit_y = (attacker_hitbox.top + attacker_hitbox.bottom) // 2
    vfx_manager.spawn_hit_spark(hit_x, hit_y, "block")

    return  # Don't apply full damage
```

**Files Modified:**
- `src/street_fighter_3rd/data/constants.py` (add constant)
- `src/street_fighter_3rd/systems/collision.py` (add chip damage logic)

**Testing:**
- Block a 100 damage attack → take 10 chip damage ✅
- Health bar decreases slightly on block ✅
- Can be chipped to death? (design decision - usually no)

---

#### **Task 1.5: Pushback on Block**
**Goal:** Defender gets pushed back when blocking, creating spacing

**Implementation:**
```python
# In collision.py when block detected:
if self._is_blocking(defender, hitbox):
    # ... chip damage and blockstun ...

    # Apply pushback
    pushback_distance = 8  # pixels (tune based on feel)

    if defender.is_facing_right():
        defender.x += pushback_distance  # Push right
    else:
        defender.x -= pushback_distance  # Push left

    # Clamp to stage boundaries
    from street_fighter_3rd.data.constants import STAGE_LEFT_BOUND, STAGE_RIGHT_BOUND
    defender.x = max(STAGE_LEFT_BOUND, min(STAGE_RIGHT_BOUND, defender.x))
```

**Files Modified:**
- `src/street_fighter_3rd/systems/collision.py` (add pushback logic)

**Testing:**
- Block attack → defender moves backward ✅
- Multiple blocks → continues pushing back ✅
- Can't be pushed out of bounds ✅
- Pushback stops at corner ✅

---

### **Phase 2: Polish & Feedback** (SHOULD HAVE)

#### **Task 2.1: Block Spark VFX**
**Goal:** Visual feedback when attack is blocked

**Implementation:**
```python
# In vfx.py add new spark type:
class SparkType(Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    SPECIAL = "special"
    BLOCK = "block"  # NEW

# Load block spark sprites
BLOCK_SPARK_SPRITES = [...]  # Load from 22_Ingame effects/
```

**Files Modified:**
- `src/street_fighter_3rd/systems/vfx.py` (add BLOCK spark type)

**Testing:**
- Block attack → see different colored spark ✅

---

#### **Task 2.2: Block Sound Effect**
**Goal:** Audio feedback when attack is blocked

**Implementation:**
```python
# Play block sound on successful block
pygame.mixer.Sound("assets/sounds/block.wav").play()
```

**Files Modified:**
- `src/street_fighter_3rd/systems/collision.py` (play sound on block)

**Note:** Requires adding sound assets first. Skip for now.

---

#### **Task 2.3: Frame Advantage Display (Debug)**
**Goal:** Show frame data for balance testing

**Implementation:**
```python
# In collision.py when block detected:
if DEBUG_MODE:
    frame_advantage = hitbox.recovery - blockstun
    print(f"Frame Advantage on Block: {frame_advantage:+d}")
    # Positive = attacker advantage
    # Negative = defender advantage
```

**Files Modified:**
- `src/street_fighter_3rd/systems/collision.py` (add debug print)

**Testing:**
- Light punch blocked → should be slightly negative ✅
- Heavy punch blocked → should be very negative ✅

---

### **Phase 3: Advanced Features** (NICE TO HAVE - Later)

These are intentionally deferred to avoid scope creep:

#### ❌ **Guard Meter**
- SF3 mechanic where blocking depletes meter
- Guard crush when empty
- Complex system, not needed yet

#### ❌ **Parry System**
- Tap forward right before hit
- SF3's signature mechanic
- Requires precise timing (10f window)
- Very complex, implement much later

#### ❌ **Red Parry**
- Parry during blockstun
- Even tighter timing (3f window)
- Extremely complex

#### ❌ **Instant Block** (Just Frame Block)
- Block at exact moment of hit for bonus
- Frame-perfect timing
- Add after basic blocking works

---

## Implementation Order

### Week 1: Core Blocking
1. ✅ **Day 1-2**: Task 1.1 - Add HitType to all attacks (1-2 hours)
2. ✅ **Day 2-3**: Task 1.2 - High/Low blocking logic (1 hour)
3. ✅ **Day 3-4**: Task 1.3 - Block animations (1 hour)
4. ✅ **Day 4**: Task 1.4 - Chip damage (30 min)
5. ✅ **Day 4**: Task 1.5 - Pushback (30 min)

### Week 1: Testing & Polish
6. ✅ **Day 5**: Task 2.1 - Block spark VFX (30 min)
7. ✅ **Day 5**: Task 2.3 - Frame advantage debug (15 min)
8. ✅ **Day 5**: Full system testing

**Total Estimated Time:** 3-4 hours for Phase 1

---

## Testing Strategy

### Test Cases

#### High/Low Blocking
```
Test: Standing block vs Standing Punch
Expected: Block succeeds ✅

Test: Standing block vs Crouching Kick (LOW)
Expected: Block fails, take full damage ❌

Test: Crouching block vs Crouching Kick (LOW)
Expected: Block succeeds ✅

Test: Crouching block vs Standing Punch (HIGH)
Expected: Block fails, take full damage ❌

Test: Either block vs Fireball (MID)
Expected: Both succeed ✅

Test: Standing block vs Overhead (OVERHEAD)
Expected: Block succeeds ✅

Test: Crouching block vs Overhead (OVERHEAD)
Expected: Block fails, take full damage ❌
```

#### Chip Damage
```
Test: Block 100 damage attack
Expected: Take 10 chip damage ✅

Test: Block multiple attacks
Expected: Health decreases by 10% each time ✅

Test: Can chip damage kill?
Design Decision: Usually NO (leave at 1 HP)
```

#### Pushback
```
Test: Block attack in neutral
Expected: Pushed back 8 pixels ✅

Test: Block attack in corner
Expected: Pushed to wall, stops ✅

Test: Block multiple attacks
Expected: Each pushes back, creates spacing ✅
```

#### Blockstun
```
Test: Block light attack
Expected: Short blockstun (~6-8f) ✅

Test: Block heavy attack
Expected: Long blockstun (~15-20f) ✅

Test: Try to attack during blockstun
Expected: Cannot act, attack doesn't come out ❌
```

---

## Files to Modify

### Phase 1 (Core)
1. `src/street_fighter_3rd/data/constants.py` - Add `CHIP_DAMAGE_MULTIPLIER`
2. `src/street_fighter_3rd/systems/collision.py`:
   - Add `hit_type` to all hitboxes
   - Update `_is_blocking()` logic
   - Add chip damage
   - Add pushback
3. `src/street_fighter_3rd/characters/akuma.py`:
   - Load block animations
   - Add helper method for loading from extracted folders
4. `src/street_fighter_3rd/characters/character.py`:
   - Wire block animations to blockstun states

### Phase 2 (Polish)
5. `src/street_fighter_3rd/systems/vfx.py` - Add block spark type

---

## Attack Classification Reference

### Standing Normals → HIGH
- LP, MP, HP
- LK, MK, HK
- Block: Standing ✅ | Crouch ❌

### Crouching Normals → LOW
- cr.LP, cr.MP, cr.HP
- cr.LK, cr.MK, cr.HK
- Block: Standing ❌ | Crouch ✅

### Jumping Normals → HIGH
- j.LP, j.MP, j.HP
- j.LK, j.MK, j.HK
- Block: Standing ✅ | Crouch ❌

### Special Cases
- **Overhead (F+MP)** → OVERHEAD (must block standing)
- **Sweep (cr.HK)** → LOW (must block crouching)
- **Fireball** → MID (block either way) or PROJECTILE
- **Dragon Punch** → HIGH (block standing)
- **Hurricane Kick** → HIGH (hits high initially)

---

## Success Criteria

### Phase 1 Complete When:
- ✅ All attacks have correct HitType
- ✅ Standing block works vs HIGH attacks
- ✅ Crouching block works vs LOW attacks
- ✅ Wrong block type gets hit
- ✅ Block animations play
- ✅ Chip damage applies (10%)
- ✅ Pushback creates spacing
- ✅ All tests pass

### Ready for Next Steps When:
- ✅ Can add crouching attacks (knowing they're LOW)
- ✅ Can add jumping attacks (knowing they're HIGH)
- ✅ Can add overhead attacks (knowing they're OVERHEAD)
- ✅ Blocking feels good and looks good

---

## Risk Mitigation

### Potential Issues

**Issue:** Blocking feels too strong
**Solution:** Increase chip damage, increase blockstun, decrease pushback

**Issue:** Blocking feels too weak
**Solution:** Decrease chip damage, decrease blockstun, increase pushback

**Issue:** High/low mixup too confusing
**Solution:** Add visual indicators (LOW attacks have blue hitbox, HIGH have red)

**Issue:** Pushback creates too much distance
**Solution:** Reduce pushback value from 8px to 4-6px

**Issue:** Animations look wrong
**Solution:** Use different frames from extracted sprites, adjust frame duration

---

## Post-Implementation

### After Blocking Works, We Can Add:
1. ✅ **Crouching normals** - All LOW attacks
2. ✅ **Jumping normals** - All HIGH attacks
3. ✅ **Overhead attacks** - OVERHEAD type
4. ✅ **Throws** - Beat blocking (unblockable)
5. ✅ **Command normals** - Various types
6. ⏳ **Parry system** - Advanced defensive option (much later)

### Documentation to Update:
- README.md - Add blocking to features list
- CONTROLS.md - Explain how to block
- ROADMAP.md - Mark blocking as complete

---

## Notes

- **Keep it simple first** - Basic blocking must work before advanced features
- **Test thoroughly** - High/low system is foundational
- **Tune feel** - Chip damage and pushback values may need adjustment
- **Visual feedback** - Animations and sparks are critical for player understanding
- **Frame data** - Use debug mode to verify frame advantage is correct
- **Don't over-engineer** - Guard meter and parry can wait

---

**End of Document**
