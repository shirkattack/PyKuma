# Akuma Sprite Animation Research

## Summary of Findings

After researching the sprite package at https://www.justnopoint.com/zweifuss/ and analyzing your local sprite files, here's what I found:

### ✅ Good News: You Have the Correct Sprite Package!

**Source:** Zwei_Fuss's official Street Fighter III: 3rd Strike sprite rips
**Character:** Akuma (Gouki) - Complete sprite set
**Total Sprites:** 885 individual PNG files (numbered 18273-19438)
**Format:** Individual trimmed sprites with transparency

### ❌ Challenge: No Official Animation Mapping Available

The sprite package does NOT include:
- Animation sequence definitions (which frames belong to which move)
- Frame timing data (how long to display each frame)
- Move boundaries (where one animation starts/ends)
- Hitbox/hurtbox frame data embedded in sprites

## What the JSON File Contains

The `akuma.json` file at https://www.justnopoint.com/zweifuss/all/akuma.json is a **sprite sheet packing manifest**, NOT an animation guide. It contains:

```json
{
  "filename": "18318.png",
  "frame": {"x": 2751, "y": 323, "w": 80, "h": 115},
  "spriteSourceSize": {"x": 106, "y": 322, "w": 80, "h": 115},
  "sourceSize": {"w": 290, "h": 505}
}
```

This tells you:
- Where each sprite was cropped from the original sprite sheet
- The sprite's trimmed dimensions
- The original canvas size (290x505)
- Sprite positioning offsets

**What it does NOT tell you:**
- Which sprites form a "standing light punch" animation
- In what order to play the frames
- How many frames per sprite
- Which sprites belong to which move

## Sprite Numbering Analysis

Based on visual inspection of your sprites:

### Standing Animations (18318-18323)
- 18318.png: Standing idle frame 1
- 18319.png: Standing idle frame 2 (slight variation)
- 18320.png: Standing idle frame 3 (crouched stance)
- 18321-18323: Idle breathing animation continuation

These sprites show Akuma's standing idle pose with subtle breathing animation.

### Movement Animations
- ~18400: Appears to be crouching
- ~18500: Knockdown/lying down frames
- ~18600: Taunt or win pose (arms spread)
- ~18700: Kick animations

### Special Move Effects
- ~19100: Purple/dark effects (likely Ashura Senku teleport or similar)

### Attack Animations
- Scattered throughout 18700-19000 range
- Includes standing attacks, crouching attacks, jumping attacks
- Special moves (Gohadoken, Goshoryuken, Tatsumaki) likely in higher ranges

## The Manual Mapping Challenge

To properly use these sprites, you'll need to **manually map** sprite sequences to moves by:

1. **Visual inspection** - Look at consecutive sprites to identify animation sequences
2. **Reference videos** - Watch SF3:3S Akuma gameplay to see actual move animations
3. **Frame data research** - Use sites like EventHubs or SuperCombo Wiki for frame counts
4. **Trial and error** - Test sprite sequences in-game to verify they look correct

### Example Mapping Process

For a standing light punch, you'd need to:
1. Find the starting frame (Akuma begins punch startup)
2. Identify active frames (arm extended, hitting)
3. Locate recovery frames (arm returning to neutral)
4. Count total frames and verify against official frame data (startup: 3, active: 3, recovery: 6)

## Recommended Approaches

### Option 1: Manual Mapping (Most Accurate)
**Pros:**
- Complete control over animation quality
- Can match official SF3:3S frame data exactly
- Proper hitbox alignment per frame

**Cons:**
- VERY time-consuming (885 sprites × manual inspection)
- Requires deep SF3 knowledge
- Prone to human error

**Estimate:** 40-80 hours of work for complete character

### Option 2: Community Resources
**Search for:**
- MUGEN character definitions (`.air` files often contain animation data)
- FightCade replay analysis
- Frame data dumps from arcade ROM hacking communities
- SF3 modding communities (may have reverse-engineered data)

**Pros:**
- Leverages existing community work
- Faster than manual mapping
- May include hitbox data

**Cons:**
- Hard to find definitive sources
- Quality/accuracy varies
- May not exist for this exact sprite rip

### Option 3: Phased Implementation (RECOMMENDED)
**Start small, expand gradually:**

**Phase 1: Core Poses (2-4 hours)**
- Standing idle: 1 sprite (18318.png - DONE!)
- Crouching: 1 sprite
- Walking: 2-3 sprites
- Jumping: 3 sprites (startup, peak, landing)

**Phase 2: Basic Attacks (8-12 hours)**
- Standing LP, MP, HP: 3-5 sprites each
- Standing LK, MK, HK: 3-5 sprites each
- Crouching attacks: Similar
- Use frame data to guide timing

**Phase 3: Special Moves (12-20 hours)**
- Gohadoken: Full animation + projectile sprites
- Goshoryuken: Multi-frame uppercut
- Tatsumaki: Hurricane kick rotation
- Ashura Senku: Teleport effect

**Phase 4: Polish (10-15 hours)**
- Win poses, taunts
- Hit reactions, block animations
- Super arts
- Perfect frame timing

## My Assessment

### Are you using the correct sprite package? ✅ YES

The sprites you have (14_Akuma folder, 885 files, numbered 18273-19438) are:
- **Official SF3:3S sprites** ripped by Zwei_Fuss
- **Complete character set** including all moves, effects, and poses
- **High quality** with proper transparency and trimming
- **Industry standard** - same files used by MUGEN creators and sprite artists

### Do the sprites correspond to moves? ⚠️ PARTIALLY

The sprites themselves are correct and complete, BUT:
- No official mapping exists linking sprite numbers to move names
- Animation sequences must be manually identified
- Frame timing must be researched separately
- Hitbox data must be created independently

## Next Steps Recommendation

1. **Start with what you have:** Keep using 18318.png as standing sprite (working perfectly!)

2. **Find one attack sequence:** Pick a simple move (standing light punch) and manually find its 8-12 sprite sequence by visual inspection

3. **Implement animation system:** Build a frame-based animation player that can cycle through sprite lists

4. **Gradually expand:** Add one move at a time, testing each thoroughly

5. **Community search:** Look for MUGEN Akuma character files (`.def`, `.air`, `.sff`) which often contain animation mappings

## Resources for Animation Mapping

1. **Frame Data:** https://www.eventhubs.com/guides/2011/aug/21/akumas-frame-data-street-fighter-3-third-strike/
   - Use frame counts to verify animation length

2. **Video Reference:** YouTube "SF3:3S Akuma frame-by-frame" or slow-motion gameplay
   - Visual confirmation of sprite sequences

3. **SuperCombo Wiki:** https://wiki.supercombo.gg/w/Street_Fighter_3:_3rd_Strike/Akuma
   - Move descriptions and frame data

4. **MUGEN Database:** Search "SF3 Akuma MUGEN" for potential animation mappings
   - May contain `.air` files with sprite sequence definitions

## Conclusion

You have the **correct and complete sprite package**, but the real work ahead is **animation archaeology** - piecing together which sprites form which moves. This is a common challenge with arcade game sprite rips, as the original game stored this data in compiled ROM code, not in external files.

The good news: Your sprites are pixel-perfect arcade-accurate rips. The challenge: You'll need to become a SF3 animation detective to map them all correctly!

---

**Status:** Research complete ✅
**Next Task:** Decide on implementation approach (manual mapping vs. community resources vs. phased implementation)
