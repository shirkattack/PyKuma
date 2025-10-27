# Akuma Frame Data Population - Summary

## Overview

Successfully populated **31 out of 69** animation folders with canonical SF3:3rd Strike frame data from SuperCombo Wiki and EventHubs.

## Data Sources

- **SuperCombo Wiki**: https://wiki.supercombo.gg/w/Street_Fighter_3:_3rd_Strike/Akuma
- **EventHubs**: Frame data tables for SF3:3S Akuma
- **Version**: Arcade version frame data (not Dreamcast)

## Successfully Populated Animations (31)

### Normal Attacks (14)
- ✅ akuma-wp (Standing Light Punch): 3f startup, 3f active, 5f recovery
- ✅ akuma-mp (Standing Medium Punch): 5f startup, 4f active, 9f recovery
- ✅ akuma-hp (Standing Heavy Punch): 4f startup, 4f active, 17f recovery
- ✅ akuma-wk (Standing Light Kick): 4f startup, 4f active, 7f recovery
- ✅ akuma-mk (Standing Medium Kick): 5f startup, 5f active, 17f recovery
- ✅ akuma-hk (Standing Heavy Kick): 9f startup, 8f active, 25f recovery
- ✅ akuma-crouch-wp (Crouching Light Punch): 4f startup, 2f active, 5f recovery
- ✅ akuma-crouch-mp (Crouching Medium Punch): 5f startup, 3f active, 7f recovery
- ✅ akuma-crouch-hp (Crouching Heavy Punch): 5f startup, 4f active, 19f recovery
- ✅ akuma-crouch-wk (Crouching Light Kick): 4f startup, 2f active, 6f recovery
- ✅ akuma-crouch-mk (Crouching Medium Kick): 6f startup, 3f active, 10f recovery
- ✅ akuma-crouch-hk (Crouching Heavy Kick): 7f startup, 5f active, 17f recovery
- ✅ akuma-fmp (Forward+MP Overhead): 14f startup, 3f active, 14f recovery
- ✅ akuma-crouch-hit (Crouching Hitstun)

### Jumping Attacks (6)
- ✅ akuma-jump-wp (Jumping Light Punch): 4f startup, 6f active
- ✅ akuma-jump-mp (Jumping Medium Punch): 5f startup, 6f active
- ✅ akuma-jump-hp (Jumping Heavy Punch): 6f startup, 2f active
- ✅ akuma-jump-wk (Jumping Light Kick): 4f startup, 8f active
- ✅ akuma-jump-mk (Jumping Medium Kick): 5f startup, 5f active
- ✅ akuma-jump-hk (Jumping Heavy Kick): 7f startup, 4f active

### Special Moves (3)
- ✅ akuma-fireball (Gou Hadouken): 8f startup, 1f active, 38f recovery, 60 damage
- ✅ akuma-dp (Gou Shoryuken): 3f startup, 14f active, 26f recovery, 130 damage, invincible frames 1-5
- ✅ akuma-hurricane (Tatsumaki): 11f startup, 1f active, 17f recovery, 100 damage
- ✅ akuma-teleport (Ashura Senku): 1f startup, 15f active, 7f recovery, invincible frames 1-20

### Movement (5)
- ✅ akuma-dashf (Forward Dash): 14 frames total
- ✅ akuma-dashb (Backward Dash): 9 frames total, invincible frames 1-4
- ✅ akuma-jump (Neutral Jump): 4f prejump, 26f airborne, 4f landing
- ✅ akuma-jumpf (Forward Jump): 4f prejump, 29f airborne, 4f landing
- ✅ akuma-jumpb (Backward Jump): 4f prejump, 30f airborne, 4f landing

### Defense (2)
- ✅ akuma-block (Standing Block)
- ✅ akuma-block-crouch (Crouching Block)

## Animations Requiring Manual Research (38)

These animations were skipped because they are:
- Super Arts (SA1, SA2, SA3)
- Taunts and intros
- Special animations (Raging Demon, Hyakkishu)
- Victory poses
- Misc states (dizzy, throw, parry)

### Super Arts & Special Moves
- ⚠️ akuma-sa1-air (Super Art 1 - Messatsu Gou Hadou Air)
- ⚠️ akuma-sa2 (Super Art 2 - Raging Demon)
- ⚠️ akuma-sa3 (Super Art 3 - Kongou Kokuretsu Zan)
- ⚠️ akuma-flame (Shakunetsu Hadouken - Red Fireball)
- ⚠️ akuma-fireball2 (EX Fireball variant)
- ⚠️ akuma-hyakkishuu (Demon Flip)
- ⚠️ akumaragingstorm2 (Raging Demon animation)

### Throws
- ⚠️ akuma-throw-forward
- ⚠️ akuma-throw-back
- ⚠️ akuma-throw-miss
- ⚠️ akuma-airthrow

### Hit Reactions & States
- ⚠️ akuma-stand-hit (Standing Hitstun)
- ⚠️ akuma-shocked (Dizzy/Stun state)
- ⚠️ akuma-chipdeath (Chip damage K.O.)
- ⚠️ akuma-slam (Ground bounce/slam)
- ⚠️ akuma-timeout (Time over pose)

### Parry System
- ⚠️ akuma-parry (Ground Parry)
- ⚠️ akuma-parry-low (Low Parry)

### Movement & Stance
- ⚠️ akuma-stance (Idle stance)
- ⚠️ akuma-walkf (Walk forward)
- ⚠️ akuma-walkb (Walk backward)
- ⚠️ akuma-crouch (Crouch transition)
- ⚠️ akuma-crouching (Crouching idle)
- ⚠️ akuma-airkick (Special air kick)

### Command Normals
- ⚠️ akuma-overhead (Different overhead variant)
- ⚠️ akuma-twist (Command normal)
- ⚠️ akuma-hpc, akuma-hkc, akuma-mpc, akuma-mkc, akuma-wpc (Close range variants)
- ⚠️ akuma-jumpf-mk (Forward jump MK variant)

### Victory & Taunts
- ⚠️ akuma-win1, akuma-win2, akuma-win3
- ⚠️ akuma-taunt
- ⚠️ akuma-intro1

### Blocking
- ⚠️ akuma-block-high (Alternate high block)

## Frame Data Format

Each populated description.txt file now contains:

```
Move: [animation-name]
==================

[Move Name]

Technical Notes:
- Frame count: Xf (from extracted PNGs)
- Startup frames: Xf (frames before attack becomes active)
- Active frames: Xf (frames where attack can hit)
- Recovery frames: Xf (frames after attack until neutral)
- Damage: X
- Stun: X
- Properties: [Special properties like invincibility, knockdown, etc.]

Frame Data Source:
- SuperCombo Wiki (wiki.supercombo.gg)
- SF3:3S Arcade version frame data

Animation Files:
- Total frames: X
- Files: frame_000.png, frame_001.png, ...

Notes:
- Animation frame count (X) may differ from game frame data
- Game frames are at 60 FPS
- Startup + Active + Recovery = Total move duration in-game
```

## Next Steps

1. **Manual Research**: Populate the 38 remaining animations with frame data from:
   - SuperCombo Wiki super art pages
   - EventHubs complete move list
   - Frame data websites like Hatson or FAT

2. **Implementation Ready**: All core normals, special moves, and jumps now have accurate frame data for implementation

3. **Testing**: Verify frame data in-game and adjust if needed based on feel

## Usage

To re-run the population script:
```bash
cd tools/sprite_extraction/
python populate_frame_data.py
```

To add more frame data, edit the `AKUMA_FRAME_DATA` dictionary in `populate_frame_data.py`.
