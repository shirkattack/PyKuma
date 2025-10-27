# Akuma Frame Data Reference

**Source**: [SuperCombo Wiki - SF3:3S Akuma](https://wiki.supercombo.gg/w/Street_Fighter_3:_3rd_Strike/Akuma)
**Last Updated**: 2025-10-11

This document maps all of Akuma's moves from Street Fighter III: 3rd Strike with accurate frame data for implementation.

## Frame Data Notation

- **Startup**: Frames before hitbox becomes active
- **Active**: Frames where hitbox can hit opponent
- **Recovery**: Frames after active frames before character can act again
- **Total**: Startup + Active + Recovery
- **Damage**: Raw damage value
- **Guard**: HIGH (must block standing), LOW (must block crouching), MID (can block either way)

---

## Standing Normal Moves

### Close Standing Light Punch (c.s.LP)
- **Startup**: 3 frames
- **Active**: 3 frames
- **Recovery**: 3 frames
- **Total**: 9 frames
- **Damage**: 3
- **Guard**: HIGH
- **Properties**: Fast jab, good for pressure and confirms
- **Cancel**: Special cancelable

### Far Standing Light Punch (f.s.LP)
- **Startup**: 4 frames
- **Active**: 3 frames
- **Recovery**: 5 frames
- **Total**: 12 frames
- **Damage**: 5
- **Guard**: HIGH
- **Properties**: Longer range poke
- **Cancel**: Special cancelable

### Close Standing Medium Punch (c.s.MP)
- **Startup**: 5 frames
- **Active**: 4 frames
- **Recovery**: 9 frames
- **Total**: 18 frames
- **Damage**: 18
- **Guard**: HIGH
- **Properties**: Good combo starter, links into itself
- **Cancel**: Special cancelable

### Far Standing Medium Punch (f.s.MP)
- **Startup**: 5 frames
- **Active**: 4 frames
- **Recovery**: 10 frames
- **Total**: 19 frames
- **Damage**: 20
- **Guard**: HIGH
- **Properties**: Longer range, good poke
- **Cancel**: Special cancelable

### Close Standing Heavy Punch (c.s.HP)
- **Startup**: 4 frames
- **Active**: 4 frames
- **Recovery**: 17 frames
- **Total**: 25 frames
- **Damage**: 24
- **Guard**: HIGH
- **Properties**: Two-hit uppercut, both hits combo, launcher
- **Cancel**: Special cancelable on hit

### Far Standing Heavy Punch (f.s.HP)
- **Startup**: 8 frames
- **Active**: 5 frames
- **Recovery**: 22 frames
- **Total**: 35 frames
- **Damage**: 24
- **Guard**: HIGH
- **Properties**: Long-range straight punch
- **Cancel**: Not cancelable

### Standing Light Kick (s.LK)
- **Startup**: 4 frames
- **Active**: 4 frames
- **Recovery**: 7 frames
- **Total**: 15 frames
- **Damage**: 7
- **Guard**: HIGH
- **Properties**: Fast poke
- **Cancel**: Special cancelable

### Close Standing Medium Kick (c.s.MK)
- **Startup**: 4 frames
- **Active**: 5 frames
- **Recovery**: 11 frames
- **Total**: 20 frames
- **Damage**: 16
- **Guard**: HIGH
- **Properties**: Fast mid-range kick
- **Cancel**: Special cancelable

### Far Standing Medium Kick (f.s.MK)
- **Startup**: 5 frames
- **Active**: 5 frames
- **Recovery**: 17 frames
- **Total**: 27 frames
- **Damage**: 20
- **Guard**: HIGH
- **Properties**: Long-range poke, good spacing tool
- **Cancel**: Not cancelable

### Close Standing Heavy Kick (c.s.HK)
- **Startup**: 5 frames
- **Active**: 5 frames
- **Recovery**: 20 frames
- **Total**: 30 frames
- **Damage**: 25
- **Guard**: HIGH
- **Properties**: Knee strike, good for combos
- **Cancel**: Special cancelable

### Far Standing Heavy Kick (f.s.HK)
- **Startup**: 9 frames
- **Active**: 8 frames
- **Recovery**: 25 frames
- **Total**: 42 frames
- **Damage**: 33
- **Guard**: HIGH
- **Properties**: Slow but powerful roundhouse
- **Cancel**: Not cancelable

---

## Crouching Normal Moves

### Crouching Light Punch (c.LP)
- **Startup**: 4 frames
- **Active**: 3 frames
- **Recovery**: 4 frames
- **Total**: 11 frames
- **Damage**: 3
- **Guard**: HIGH
- **Properties**: Fast low poke, good for pressure
- **Cancel**: Special cancelable

### Crouching Medium Punch (c.MP)
- **Startup**: 4 frames
- **Active**: 4 frames
- **Recovery**: 8 frames
- **Total**: 16 frames
- **Damage**: 16
- **Guard**: HIGH
- **Properties**: Anti-air, good combo starter
- **Cancel**: Special cancelable

### Crouching Heavy Punch (c.HP)
- **Startup**: 4 frames
- **Active**: 5 frames
- **Recovery**: 19 frames
- **Total**: 28 frames
- **Damage**: 24
- **Guard**: HIGH
- **Properties**: Strong anti-air, launcher
- **Cancel**: Special cancelable

### Crouching Light Kick (c.LK)
- **Startup**: 4 frames
- **Active**: 3 frames
- **Recovery**: 6 frames
- **Total**: 13 frames
- **Damage**: 3
- **Guard**: LOW
- **Properties**: Fast low poke, can chain into itself
- **Cancel**: Special cancelable

### Crouching Medium Kick (c.MK)
- **Startup**: 5 frames
- **Active**: 3 frames
- **Recovery**: 11 frames
- **Total**: 19 frames
- **Damage**: 16
- **Guard**: LOW
- **Properties**: Good low poke, long range
- **Cancel**: Special cancelable

### Crouching Heavy Kick (c.HK)
- **Startup**: 5 frames
- **Active**: 6 frames
- **Recovery**: 21 frames
- **Total**: 32 frames
- **Damage**: 25
- **Guard**: LOW
- **Properties**: **KNOCKDOWN**, sweep attack
- **Cancel**: Not cancelable

---

## Jump Normal Moves

### Jump Light Punch (j.LP)
- **Startup**: 4 frames
- **Active**: Until landing
- **Damage**: 8
- **Guard**: HIGH/AIR
- **Properties**: Fast air-to-air, air throw when combined with LK

### Jump Medium Punch (j.MP)
- **Startup**: 5 frames
- **Active**: Until landing
- **Damage**: 16
- **Guard**: HIGH/AIR
- **Properties**: Good jump-in, crossup potential

### Jump Heavy Punch (j.HP)
- **Startup**: 7 frames
- **Active**: Until landing
- **Damage**: 24
- **Guard**: HIGH/AIR
- **Properties**: Strong jump-in, big hitbox

### Jump Light Kick (j.LK)
- **Startup**: 4 frames
- **Active**: Until landing
- **Damage**: 8
- **Guard**: HIGH/AIR
- **Properties**: Fast air-to-air, air throw when combined with LP

### Jump Medium Kick (j.MK)
- **Startup**: 5 frames
- **Active**: Until landing
- **Damage**: 16
- **Guard**: HIGH/AIR
- **Properties**: Good crossup kick

### Jump Heavy Kick (j.HK)
- **Startup**: 8 frames
- **Active**: Until landing
- **Damage**: 25
- **Guard**: HIGH/AIR
- **Properties**: **OVERHEAD on landing**, demon kick animation

---

## Special Moves

### Gou Hadouken (Fireball) - QCF + P (236P)
**Motion**: ↓ ↘ → + Punch

#### Light Punch Version
- **Startup**: 8 frames
- **Active**: Projectile lifetime
- **Recovery**: 38 frames (total animation)
- **Damage**: 17
- **Properties**: Slow fireball, travels 40% screen speed
- **Projectile**: Can be destroyed by opponent's fireball

#### Medium Punch Version
- **Startup**: 8 frames
- **Active**: Projectile lifetime
- **Recovery**: 38 frames
- **Damage**: 17
- **Properties**: Medium speed fireball, travels 60% screen speed

#### Heavy Punch Version
- **Startup**: 8 frames
- **Active**: Projectile lifetime
- **Recovery**: 38 frames
- **Damage**: 17
- **Properties**: Fast fireball, travels 80% screen speed

### Shakunetsu Hadouken (Red Fireball) - HCB + P (63214P)
**Motion**: → ↘ ↓ ↙ ← + Punch

#### Light Punch Version
- **Startup**: 14 frames
- **Recovery**: 42 frames
- **Damage**: 8 (1 hit)
- **Properties**: Single-hit red fireball

#### Medium Punch Version
- **Startup**: 18 frames
- **Recovery**: 43 frames
- **Damage**: 16 (2 hits)
- **Properties**: Two-hit red fireball

#### Heavy Punch Version
- **Startup**: 22 frames
- **Recovery**: 44 frames
- **Damage**: 24 (3 hits)
- **Properties**: Three-hit red fireball, juggles

### Gou Shoryuken (Dragon Punch) - DP + P (623P)
**Motion**: → ↓ ↘ + Punch

#### Light Punch Version
- **Startup**: 3 frames
- **Active**: 14 frames
- **Recovery**: 26 frames
- **Total**: 43 frames
- **Damage**: 23 (1 hit)
- **Properties**: **Invincible frames 1-5**, anti-air, knockdown

#### Medium Punch Version
- **Startup**: 2 frames
- **Active**: 18 frames
- **Recovery**: 32 frames
- **Total**: 52 frames
- **Damage**: 26 (2 hits)
- **Properties**: **Invincible frames 1-7**, hits twice, knockdown

#### Heavy Punch Version
- **Startup**: 1 frame
- **Active**: 23 frames
- **Recovery**: 41 frames
- **Total**: 65 frames
- **Damage**: 29 (3 hits)
- **Properties**: **Invincible frames 1-9**, hits three times, knockdown, highest damage

### Tatsumaki Zankuu Kyaku (Hurricane Kick) - QCB + K (214K)
**Motion**: ↓ ↙ ← + Kick

#### Light Kick Version (Ground)
- **Startup**: 11 frames
- **Active**: 4 frames (per hit)
- **Recovery**: 17 frames
- **Damage**: 17 (2 hits max)
- **Properties**: Two hits, short distance

#### Medium Kick Version (Ground)
- **Startup**: 8 frames
- **Active**: 8 frames (per hit)
- **Recovery**: 14 frames
- **Damage**: 21 (3 hits max)
- **Properties**: Three hits, medium distance

#### Heavy Kick Version (Ground)
- **Startup**: 2 frames
- **Active**: 18 frames (per hit)
- **Recovery**: 10 frames
- **Damage**: 25 (5 hits max)
- **Properties**: Five hits, long distance, **KNOCKDOWN on final hit**

#### Air Tatsumaki (Any Kick in Air)
- **Startup**: 8 frames
- **Active**: Until landing
- **Damage**: 17-25 (depends on version)
- **Properties**: Can be done in air, useful for mobility

### Demon Flip - QCF + K (623K)
**Motion**: → ↓ ↘ + Kick

- **Startup**: 40 frames (flip animation)
- **Active**: 15 frames (if attacking)
- **Recovery**: 13 frames
- **Damage**: 17
- **Properties**: Flip over opponent, can attack/throw/land

---

## Super Arts (Choose 1 per match)

### SA1: Messatsu Gou Hadou (Beam Super) - QCF×2 + P (236236P)
**Motion**: ↓ ↘ → ↓ ↘ → + Punch

- **Startup**: 2 frames (freeze) + projectile
- **Active**: 42 frames (beam duration)
- **Recovery**: 50+ frames
- **Damage**: 47 (multi-hit)
- **Meter Length**: 1 stock (shortest bar)
- **Properties**: Screen-filling beam, punishable on block
- **EX Moves Available**: Yes (meter divided into 3)

### SA2: Messatsu Gou Shoryuu (DP Super) - QCF×2 + K (236236K)
**Motion**: ↓ ↘ → ↓ ↘ → + Kick

- **Startup**: 1 frame
- **Active**: 24 frames
- **Recovery**: High (very unsafe)
- **Damage**: 66 (multi-hit uppercut)
- **Meter Length**: 2 stocks (medium bar)
- **Properties**: **Fully invincible startup**, anti-air, massive damage
- **EX Moves Available**: Yes (meter divided into 2)

### SA3: Messatsu Gou Rasen (Spinning Demon) - QCF×2 + P (236236P)
**Motion**: ↓ ↘ → ↓ ↘ → + Punch

- **Startup**: 4 frames
- **Active**: 22 frames
- **Recovery**: Moderate
- **Damage**: 65 (multi-hit spinning attack)
- **Meter Length**: 3 stocks (longest bar)
- **Properties**: Vacuum effect, pulls opponent in
- **EX Moves Available**: No (3 separate uses)
- **Note**: Most popular choice in competitive play

### Shun Goku Satsu (Raging Demon) - LP LP → LK HP (when close)
**Motion**: Jab Jab Forward Light Kick Heavy Punch

- **Startup**: 1 frame
- **Damage**: Massive (30-50% health)
- **Properties**: **Fully invincible**, unblockable, throw, only avoidable by jumping or being invincible
- **Requirements**: Must be on ground, close range
- **Note**: Iconic super, very hard to land

---

## Universal Mechanics

### Throws
- **Forward Throw**: LP + LK (close range)
- **Damage**: 33
- **Properties**: Cannot be blocked, 7-frame startup, can be teched

### Air Throw
- **Input**: LP + LK in air (when close)
- **Damage**: 30
- **Properties**: Akuma-specific, very useful

### Parry
- **Ground Parry High**: Tap Forward (10-frame window)
- **Ground Parry Low**: Tap Down (10-frame window)
- **Air Parry**: Tap Forward/Down in air (7-frame window)
- **Red Parry**: Tap during blockstun (2-frame window)
- **Properties**: No chip damage, frame advantage on successful parry

---

## Implementation Priority (TIER 1)

Based on the improvement roadmap, here's the recommended order for implementation:

### Week 1-2: Complete Standing Normals
1. ✅ Standing Light Punch (DONE - already implemented)
2. Standing Medium Punch (c.s.MP + f.s.MP)
3. Standing Heavy Punch (c.s.HP + f.s.HP)
4. Standing Light Kick (s.LK)
5. Standing Medium Kick (c.s.MK + f.s.MK)
6. Standing Heavy Kick (c.s.HK + f.s.HK)

### Week 2-3: Complete Crouching Normals
7. Crouching Light Punch (c.LP)
8. Crouching Medium Punch (c.MP)
9. Crouching Heavy Punch (c.HP)
10. Crouching Light Kick (c.LK)
11. Crouching Medium Kick (c.MK)
12. Crouching Heavy Kick (c.HK) - **Requires knockdown system**

### Week 3-4: Complete Jump Normals
13. Jump Light Punch (j.LP)
14. Jump Medium Punch (j.MP)
15. Jump Heavy Punch (j.HP)
16. Jump Light Kick (j.LK)
17. Jump Medium Kick (j.MK)
18. Jump Heavy Kick (j.HK) - **Overhead property**

### Week 4-6: Special Moves (Requires new systems)
19. Gou Hadouken (QCF+P) - **Requires projectile system**
20. Gou Shoryuken (DP+P) - **Requires invincibility frames + knockdown**
21. Tatsumaki Zankuu Kyaku (QCB+K) - **Requires multi-hit system + knockdown**

---

## Notes for Implementation

### Hitbox Positioning
- All X/Y values are relative to character position
- Positive X = in front of character
- Negative Y = above character's feet
- Width/Height in pixels (our sprites are 2x scale)

### Frame Data Accuracy
- SF3:3S runs at 60 FPS
- All frame counts are exact (1 frame = 1/60 second)
- Must match these numbers for authentic feel

### Cancel Windows
- "Special cancelable" means can buffer special move during active frames
- Window starts on first active frame
- Must detect motion input within 12-frame buffer

### Damage Scaling
- First hit: 100% damage
- Second hit: 80% damage
- Third hit: 70% damage
- Fourth+ hit: 60% damage

### Proximity Detection
- "Close" normals trigger within ~50 pixels
- "Far" normals trigger beyond that range
- Check distance at startup frame

---

**Ready for Implementation**: All frame data is now mapped and ready to be coded into the collision system and character classes.
