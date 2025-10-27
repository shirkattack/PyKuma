# Hitbox Integration Test Instructions

## What Was Fixed

The hitbox data is now being properly loaded into the SF3CollisionSystem. Here's what changed:

1. **Created `akuma_hitboxes.py`** - Complete frame data for all 6 standing normals
2. **Populated SF3HitboxManager** - The `_create_hitbox_manager()` method now converts our hitbox data into SF3Hitbox objects and adds them to the manager
3. **Frame-accurate collision** - Hitboxes only appear on active frames (e.g., LP active on frames 4-5)

## How to Test

### 1. Run the game
```bash
uv run sf3 > /tmp/test.log 2>&1 &
```

### 2. Press attack buttons (Player 1 controls)
- **J** = Light Punch (3f startup, frames 4-5 active, 12 damage)
- **K** = Medium Punch (5f startup, frames 6-8 active, 18 damage)
- **L** = Heavy Punch (7f startup, frames 8-11 active, 25 damage)
- **U** = Light Kick (4f startup, frames 5-6 active, 14 damage)
- **I** = Medium Kick (6f startup, frames 7-9 active, 20 damage)
- **O** = Heavy Kick (9f startup, frames 10-13 active, 28 damage)

### 3. Check the log for debug output

When you press an attack button during active frames, you should see:
```
DEBUG: Character Akuma state=LIGHT_PUNCH, frame=4, has 1 attack hitbox(es)
DEBUG: Character Akuma state=LIGHT_PUNCH, frame=5, has 1 attack hitbox(es)
```

### 4. When attacks connect, you should see:
```
SF3 Hit Applied: 12 damage, 12 hitstun
```

Or with combos:
```
🥊 SF3 Hit Applied: 25 → 23 damage, 18 hitstun (Combo: 2)
```

## Expected Behavior

### Attack Timing
- **Startup frames**: No hitbox appears
- **Active frames**: Hitbox is present and can hit
- **Recovery frames**: No hitbox

Example for Standing LP:
- Frames 1-3: Startup (no hitbox)
- Frames 4-5: Active (hitbox present - can hit)
- Frames 6-11: Recovery (no hitbox)

### On Hit
- Defender takes damage
- Defender enters hitstun state
- Both characters freeze for 8 frames (hitfreeze)
- "SF3 Hit Applied" message appears

### Damage Values
- LP: 12 damage
- MP: 18 damage
- HP: 25 damage
- LK: 14 damage
- MK: 20 damage
- HK: 28 damage

## Troubleshooting

If you don't see damage:

1. **Check if hitboxes are being created**
   ```bash
   tail -f /tmp/test.log | grep "DEBUG: Character"
   ```
   You should see messages when attacks have active hitboxes

2. **Check if collision is being detected**
   ```bash
   tail -f /tmp/test.log | grep "SF3 Hit"
   ```
   You should see "SF3 Hit Applied" when hits connect

3. **Make sure players are close enough**
   - Walk forward with D/F keys to get in range
   - Hitboxes extend about 45-65 pixels forward

4. **Check frame timing**
   - Attacks have startup frames before they become active
   - Press the button, then wait a few frames

## Next Steps

Once you confirm hits are connecting:
1. Add crouching normals hitbox data
2. Add special moves (Hadoken, DP, Hurricane Kick)
3. Re-integrate parry system
4. Add pushback and frame advantage
5. Add combo scaling system
