# Akuma Animation Reference Guide

## 🎉 Major Discovery: Animation GIFs Available!

You found that https://www.justnopoint.com/zweifuss/ provides **67 named animation GIFs** for Akuma! This is a massive breakthrough for mapping sprites to moves.

## Complete Animation List (67 animations)

### Basic Movement
- `akuma-stance` - Standing idle (breathing animation)
- `akuma-crouch` / `akuma-crouching` - Crouching pose
- `akuma-walkf` - Walk forward
- `akuma-walkb` - Walk backward
- `akuma-dashf` - Dash forward
- `akuma-dashb` - Dash backward

### Jumping
- `akuma-jump` - Neutral jump
- `akuma-jumpf` - Jump forward
- `akuma-jumpb` - Jump backward

### Standing Normal Attacks
- `akuma-wp` - Weak/Light Punch (standing LP) ⭐
- `akuma-wpc` - Weak Punch Close
- `akuma-mp` - Medium Punch (standing MP) ⭐
- `akuma-mpc` - Medium Punch Close
- `akuma-fmp` - Forward Medium Punch
- `akuma-hp` - Heavy/Hard Punch (standing HP) ⭐
- `akuma-hpc` - Heavy Punch Close
- `akuma-wk` - Weak/Light Kick (standing LK) ⭐
- `akuma-mk` - Medium Kick (standing MK) ⭐
- `akuma-mkc` - Medium Kick Close
- `akuma-hk` - Heavy/Hard Kick (standing HK) ⭐
- `akuma-hkc` - Heavy Kick Close

### Crouching Attacks
- `akuma-crouch-wp` - Crouching light punch
- `akuma-crouch-wk` - Crouching light kick
- `akuma-crouch-mp` - Crouching medium punch
- `akuma-crouch-mk` - Crouching medium kick
- `akuma-crouch-hp` - Crouching heavy punch
- `akuma-crouch-hk` - Crouching heavy kick

### Jumping Attacks
- `akuma-jump-wp` - Jumping light punch
- `akuma-jump-wk` - Jumping light kick
- `akuma-jump-mp` - Jumping medium punch
- `akuma-jump-mk` - Jumping medium kick
- `akuma-jump-hk` - Jumping heavy kick
- `akuma-jump-hp` - Jumping heavy punch
- `akuma-jumpf-mk` - Jump forward medium kick
- `akuma-airkick` - Air kick special

### Special Moves (Shoto Classics)
- `akuma-fireball` - Gohadoken (QCF+P) - Fireball ⭐⭐⭐
- `akuma-fireball2` - Gohadoken variant
- `akuma-dp` - Goshoryuken (DP+P) - Dragon Punch ⭐⭐⭐
- `akuma-hurricane` - Tatsumaki Zankukyaku (QCB+K) - Hurricane Kick ⭐⭐⭐
- `akuma-teleport` - Ashura Senku - Teleport ⭐⭐

### Akuma-Specific Moves
- `akuma-hyakkishuu` - Hyakki Shu (Demon Flip)
- `akuma-slam` - Demon Flip follow-up
- `akuma-overhead` - Overhead attack
- `akuma-flame` - Shakunetsu Hadoken (Red fireball)

### Super Arts
- `akuma-sa1-air` - Super Art 1 (Air)
- `akuma-sa2` - Super Art 2 (Shun Goku Satsu / Raging Demon)
- `akuma-sa3` - Super Art 3
- `akumaragingstorm2` - Raging Demon alternate

### Defensive/Reactions
- `akuma-block` - Standing block
- `akuma-block-high` - High block
- `akuma-block-crouch` - Crouching block
- `akuma-parry` - Parry (standing) ⭐⭐
- `akuma-parry-low` - Parry (crouching)

### Hit Reactions
- `akuma-stand-hit` - Standing hit stun
- `akuma-crouch-hit` - Crouching hit stun
- `akuma-shocked` - Shocked/stunned
- `akuma-chipdeath` - Chip death animation

### Throws
- `akuma-throw-forward` - Forward throw
- `akuma-throw-back` - Back throw
- `akuma-throw-miss` - Throw whiff
- `akuma-airthrow` - Air throw

### Taunts & Intros/Outros
- `akuma-intro1` - Intro animation
- `akuma-taunt` - Taunt
- `akuma-twist` - Twist taunt
- `akuma-win1` - Win pose 1
- `akuma-win2` - Win pose 2
- `akuma-win3` - Win pose 3
- `akuma-timeout` - Timeout pose

## How to Use These GIFs for Animation Mapping

### Method 1: Visual Reference (Recommended for Now)
The GIFs serve as **visual references** to understand:
1. **Move timing** - How many frames each animation should take
2. **Key poses** - Which sprite poses to look for in your 14_Akuma folder
3. **Animation flow** - The sequence of motion (startup → active → recovery)

### Method 2: Frame-by-Frame Comparison
For each animation you want to implement:

1. **Download the GIF:**
   ```bash
   curl -s "https://www.justnopoint.com/zweifuss/colorswap.php?pcolorstring=AkumaPalette.bin&pcolornum=7&pname=akuma/akuma-wp.gif" -o akuma-wp.gif
   ```

2. **Extract frames** using the provided tool:
   ```bash
   python3 tools/extract_gif_frames.py akuma-wp
   ```

3. **Manually browse your 14_Akuma folder** to find sprites that visually match each GIF frame

4. **Record the sprite sequence** (e.g., standing light punch = 18650, 18651, 18652, 18653, 18654, 18655)

### Example: Standing Light Punch (akuma-wp)

The `akuma-wp` GIF shows 6 frames:
- Frame 0: Standing neutral (startup)
- Frame 1: Arm beginning to extend
- Frame 2: **Arm fully extended (active frame)** ⚡
- Frame 3: Arm beginning to retract
- Frame 4: Arm pulling back
- Frame 5: Return to neutral (recovery complete)

**Your task:** Find 6 sprites in `14_Akuma/` that match these poses. Visual inspection is key!

## Priority Animation Mapping (Recommended Order)

### Phase 1: Essential Combat (Start Here!)
1. ✅ **akuma-stance** - Already using 18318.png, works great!
2. **akuma-wp** - Standing light punch (6 frames)
3. **akuma-mp** - Standing medium punch (~8 frames)
4. **akuma-hp** - Standing heavy punch (~10 frames)
5. **akuma-wk** - Standing light kick (~7 frames)
6. **akuma-mk** - Standing medium kick (~9 frames)
7. **akuma-hk** - Standing heavy kick (~12 frames)

**Estimate:** 4-6 hours to find and map all basic standing attacks

### Phase 2: Movement
8. **akuma-walkf** - Walk forward (3-4 frame loop)
9. **akuma-walkb** - Walk backward (3-4 frame loop)
10. **akuma-jump** - Jump (startup, air, landing = ~8-10 frames)
11. **akuma-crouch** - Crouch transition (2-3 frames)

**Estimate:** 2-3 hours

### Phase 3: Special Moves
12. **akuma-fireball** - Gohadoken projectile (~15 frames)
13. **akuma-dp** - Goshoryuken uppercut (~20 frames)
14. **akuma-hurricane** - Tatsumaki hurricane kick (~25 frames)

**Estimate:** 6-10 hours (complex animations with projectiles/movement)

### Phase 4: Polish
15. Hit reactions, blocks, parries
16. Throws and grabs
17. Win poses and taunts

**Estimate:** 8-12 hours

## Sprite Numbering Hypothesis

Based on the 885 sprites (18273-19438) and 67 animations, each animation averages ~13 frames. The sprites are likely organized by animation type:

- **18273-18400:** Stance, idle, basic movement (~127 sprites)
- **18400-18700:** Standing/crouching normal attacks (~300 sprites)
- **18700-19000:** Jumping attacks and aerials (~300 sprites)
- **19000-19200:** Special moves (Gohadoken, DP, Hurricane) (~200 sprites)
- **19200-19438:** Super arts, win poses, effects (~238 sprites)

**This is speculation** - actual organization may differ!

## Tools Created

### extract_gif_frames.py
Located at `tools/extract_gif_frames.py`

**Usage:**
```bash
# Extract single animation
python3 tools/extract_gif_frames.py akuma-wp

# Extract all 67 animations (WARNING: Takes time!)
python3 tools/extract_gif_frames.py --all
```

**What it does:**
- Downloads GIF from justnopoint.com
- Extracts individual frames as PNG files
- Attempts to match frames to your sprite numbers (limited success - GIFs are composites)
- Saves results to `/tmp/akuma_frames/`

## Next Steps

### Immediate Action: Manual Mapping
Pick ONE attack to fully map as proof-of-concept:

**Suggested:** Standing Light Punch (`akuma-wp`)

1. Download the GIF
2. Extract 6 frames
3. Visually browse `14_Akuma/` folder to find matching sprites
4. Create animation definition:
   ```python
   STANDING_LIGHT_PUNCH = {
       "frames": [18650, 18651, 18652, 18653, 18654, 18655],  # Example
       "frame_duration": 2,  # Hold each sprite for 2 game frames (60 FPS)
       "loop": False
   }
   ```
5. Implement in game and test!

Once you successfully animate ONE move, you'll have the workflow down and can systematically map the rest.

### Long-term: Community Resources
Consider searching for:
- **MUGEN Akuma SF3** character files (may contain sprite mappings)
- **SF3 romhacking forums** (animation data extracted from arcade ROM)
- **Frame data spreadsheets** from competitive SF3 community

## Key Insight

**The GIFs are a HUGE help!** They give you:
- ✅ Exact move names mapped to animations
- ✅ Visual reference for pose matching
- ✅ Frame counts for timing
- ✅ Animation flow understanding

**What you still need to do:**
- Manual visual matching between GIF frames and your PNG sprites
- Recording which sprite numbers form which sequences

This is still manual work, but you now have **clear references** instead of blind guessing!

---

**Status:** Research complete, animation list catalogued ✅
**Next:** Manual sprite matching for one attack (recommended: akuma-wp)
