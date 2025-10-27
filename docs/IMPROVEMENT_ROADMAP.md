# Street Fighter III: 3rd Strike - Improvement Roadmap

## Current State Analysis

### ✅ What We Have
- ✅ 60 FPS game loop
- ✅ Full movement (walk, jump neutral/forward/backward, crouch)
- ✅ One attack (standing light punch)
- ✅ Hit/hurtbox collision system
- ✅ Hit freeze (hitstop) for both players
- ✅ Blocking detection
- ✅ Blockstun and hitstun
- ✅ Input buffer (60 frames)
- ✅ Motion input detection (QCF, DP, QCB)
- ✅ Sprite animation system
- ✅ VFX system (hit sparks)
- ✅ Health bars
- ✅ Crossup protection
- ✅ Debug visualization

### ❌ What's Missing
- ❌ Only 1 attack (need 17 more normals per character)
- ❌ No special moves implemented (only detection)
- ❌ No projectile system
- ❌ No air attacks
- ❌ No crouching attacks
- ❌ No throws
- ❌ No knockdown/wakeup
- ❌ No chip damage
- ❌ No pushback on hit/block
- ❌ No corner mechanics
- ❌ No round system
- ❌ No KO state
- ❌ Only 1 character (Akuma)
- ❌ No sound/music

---

## 🎯 Improvement Roadmap

### TIER 1: Complete Basic Combat (Make it Playable)
**Goal**: Create a fully functional 1v1 fighting game with complete movesets

#### 1.1 Complete Akuma's Normal Moves (HIGH PRIORITY)
**Impact**: ⭐⭐⭐⭐⭐ (Essential for actual gameplay)
**Effort**: Medium (repetitive but straightforward)

**Standing Normals** (5 more):
- [ ] Standing Medium Punch (s.MP)
- [ ] Standing Heavy Punch (s.HP)
- [ ] Standing Light Kick (s.LK)
- [ ] Standing Medium Kick (s.MK)
- [ ] Standing Heavy Kick (s.HK)

**Crouching Normals** (6 total):
- [ ] Crouching Light Punch (c.LP)
- [ ] Crouching Medium Punch (c.MP)
- [ ] Crouching Heavy Punch (c.HP)
- [ ] Crouching Light Kick (c.LK)
- [ ] Crouching Medium Kick (c.MK)
- [ ] Crouching Heavy Kick (c.HK) - knockdown

**Jump Normals** (6 total):
- [ ] Jump Light Punch (j.LP)
- [ ] Jump Medium Punch (j.MP)
- [ ] Jump Heavy Punch (j.HP)
- [ ] Jump Light Kick (j.LK)
- [ ] Jump Medium Kick (j.MK)
- [ ] Jump Heavy Kick (j.HK) - overhead on landing

**Steps**:
1. Download remaining sprite GIFs from justnopoint.com
2. Extract frames to PNGs
3. Add animations to `akuma.py`
4. Define hitboxes in `collision.py`
5. Add input detection in `_check_normal_attacks()`
6. Test frame data accuracy vs real SF3:3S

**Resources Needed**:
- Akuma sprite GIFs (s.MP, s.HP, s.LK, s.MK, s.HK, c.LP, c.MP, c.HP, c.LK, c.MK, c.HK, j.LP, j.MP, j.HP, j.LK, j.MK, j.HK)
- SF3:3S frame data from SuperCombo wiki

#### 1.2 Implement Special Moves (HIGH PRIORITY)
**Impact**: ⭐⭐⭐⭐⭐ (Signature moves, essential for character identity)
**Effort**: High (requires projectile system, invincibility frames, multi-hit)

**Gohadoken (Fireball)** - QCF + P:
- [ ] Create Projectile system class
- [ ] Projectile physics (velocity, lifetime, collision)
- [ ] Projectile hitboxes (hurt opponent, destroyed by opponent's projectile)
- [ ] Three versions: LP (slow), MP (medium), HP (fast)
- [ ] Akuma recovery animation
- [ ] Projectile sprites (justnopoint.com)

**Goshoryuken (Dragon Punch)** - DP + P:
- [ ] Invincibility frames (frame 1-5 fully invincible)
- [ ] Launch upward with velocity curve
- [ ] Multi-hit detection (3 hits)
- [ ] Knockdown on final hit
- [ ] Three versions: LP (1 hit), MP (2 hits), HP (3 hits)
- [ ] Landing recovery

**Tatsumaki Zankukyaku (Hurricane Kick)** - QCB + K:
- [ ] Forward movement during animation
- [ ] Multi-hit detection (up to 5 hits)
- [ ] Spinning hitboxes at different heights
- [ ] Three versions: LK (2 hits), MK (3 hits), HK (5 hits, knockdown)
- [ ] Air version (different properties)

**Steps**:
1. Create `src/street_fighter_3rd/systems/projectile.py`
2. Download special move sprite GIFs
3. Implement invincibility frame system in Character
4. Add knockdown state and wakeup system
5. Test special move priority and cancels

#### 1.3 Add Throws (MEDIUM PRIORITY)
**Impact**: ⭐⭐⭐⭐ (Essential fighting game mechanic)
**Effort**: Medium

- [ ] Throw input detection (LP+LK pressed simultaneously)
- [ ] Throw range check (proximity detection)
- [ ] Throw startup (3 frames)
- [ ] Throw tech window (5 frames to input LP+LK)
- [ ] Throw animation (attacker and defender)
- [ ] Throw damage and positioning
- [ ] Air throw (for Akuma's j.LP+LK)
- [ ] Throw invulnerable states (during attacks, hitstun, etc.)

#### 1.4 Knockdown and Wakeup System (MEDIUM PRIORITY)
**Impact**: ⭐⭐⭐⭐ (Required for heavy attacks and special moves)
**Effort**: Medium

- [ ] Knockdown state (character falls, hits ground)
- [ ] Lying down state (brief invincibility)
- [ ] Wakeup state (stand up animation)
- [ ] Quick rise vs normal rise (hold up/down during knockdown)
- [ ] Wakeup throw protection (can't be thrown immediately)
- [ ] Hard knockdown (no quick rise option)

---

### TIER 2: Polish Combat Feel (Make it Feel Good)
**Goal**: Add the satisfying details that make SF3 feel amazing

#### 2.0 Hit Reaction System (CRITICAL PRIORITY) ⚡
**Impact**: ⭐⭐⭐⭐⭐ (ESSENTIAL - game feels broken without this!)
**Effort**: Low-Medium

**Current Issue**: Opponent doesn't visually react when hit - they just stay in standing animation!

**Hit Reaction Animations**:
- [ ] Standing hitstun animation (recoil backward)
- [ ] Crouching hitstun animation (different from standing)
- [ ] Air hitstun animation (tumble/spin)
- [ ] Light hit reaction (small recoil, 2-3 frames)
- [ ] Medium hit reaction (medium recoil, 3-4 frames)
- [ ] Heavy hit reaction (large recoil, 4-5 frames)
- [ ] Knockdown animation (sweep, heavy hits)

**Visual Feedback on Hit**:
- [ ] Opponent sprite changes to hitstun frame
- [ ] Hit spark spawns at collision point (DONE ✅)
- [ ] Hit freeze for both players (DONE ✅)
- [ ] Defender pushed back (needs implementation)
- [ ] Flash/blink defender sprite white (1 frame)

**Physical Feedback on Block**:
- [ ] Blockstun animation (guarding pose, arms up)
- [ ] Block spark (different from hit spark)
- [ ] Pushback on block (DONE: blockstun ✅, needs animation)
- [ ] Chip damage on special moves (future)

**Steps to Implement**:
1. Find hitstun sprite sequences from justnopoint.com
2. Add `hitstun_light`, `hitstun_medium`, `hitstun_heavy` animations
3. Trigger hitstun animation in `take_damage()` based on damage level
4. Add sprite flash effect in render (white overlay for 1 frame)
5. Implement pushback physics (move defender X pixels based on hit strength)
6. Add blockstun animation (arms up, guarding pose)

**Priority**: This should be done IMMEDIATELY after completing standing normals. The game currently feels unresponsive because hits don't have visual/physical feedback!

#### 2.1 Pushback System (HIGH PRIORITY)
**Impact**: ⭐⭐⭐⭐ (Critical for spacing and corner pressure)
**Effort**: Low-Medium

- [ ] Attacker pushback on hit (small)
- [ ] Defender pushback on hit (medium)
- [ ] Attacker pushback on block (medium)
- [ ] Defender pushback on block (large)
- [ ] Different pushback values per move
- [ ] Corner collision (can't push through wall)

#### 2.2 Screen Shake (MEDIUM PRIORITY)
**Impact**: ⭐⭐⭐ (Adds impact to heavy hits)
**Effort**: Low

- [ ] Shake on heavy attacks (HP, HK)
- [ ] Shake on special moves
- [ ] Shake on knockdown
- [ ] Configurable intensity (constants.py already has values)
- [ ] Decay over time (6 frames default)

#### 2.3 Sound Effects (MEDIUM PRIORITY)
**Impact**: ⭐⭐⭐⭐ (HUGE impact on feel, but not gameplay-critical)
**Effort**: Medium (requires sound assets)

**Essential Sounds**:
- [ ] Hit sounds (light, medium, heavy)
- [ ] Block sounds
- [ ] Whiff sounds (punch swish, kick swish)
- [ ] Jump/land sounds
- [ ] Special move sounds (Hadoken!, Shoryuken!, etc.)
- [ ] Voice clips (character-specific)
- [ ] KO sound

**Steps**:
1. Create `src/street_fighter_3rd/systems/audio.py`
2. Find SF3 sound rips (freesound.org or game rips)
3. Integrate with pygame.mixer
4. Add sound triggers to collision system

#### 2.4 Improved VFX (LOW PRIORITY)
**Impact**: ⭐⭐⭐ (Nice to have, adds polish)
**Effort**: Low-Medium

- [ ] Block sparks (different from hit sparks)
- [ ] Dust clouds on landing
- [ ] Speed lines during dashes
- [ ] Projectile impact effects
- [ ] Screen flash on super moves
- [ ] Damage numbers (optional, arcade-style)

---

### TIER 3: Game Structure (Make it Complete)
**Goal**: Turn it into a full game with menus, rounds, win conditions

#### 3.1 Round System (HIGH PRIORITY)
**Impact**: ⭐⭐⭐⭐⭐ (Required for actual matches)
**Effort**: Low-Medium

- [ ] Best of 3 rounds
- [ ] Round timer (99 seconds)
- [ ] Round start sequence ("Round 1... Fight!")
- [ ] Round win conditions (health = 0 or timeout)
- [ ] Round victory (pose, freeze)
- [ ] Match victory (2 round wins)
- [ ] Round counter UI
- [ ] Timer UI

#### 3.2 KO State (HIGH PRIORITY)
**Impact**: ⭐⭐⭐⭐⭐ (Required for win conditions)
**Effort**: Low

- [ ] KO animation (character falls)
- [ ] KO voice clip
- [ ] Victory pose for winner
- [ ] Freeze on KO (brief hitstop)
- [ ] "K.O." text overlay
- [ ] Prevent further input during KO

#### 3.3 Main Menu (MEDIUM PRIORITY)
**Impact**: ⭐⭐⭐ (Professional presentation)
**Effort**: Medium

- [ ] Title screen
- [ ] Menu options (Versus, Training, Options, Quit)
- [ ] Menu navigation (keyboard/joystick)
- [ ] Background animation (character demos?)
- [ ] SF3 style UI graphics

#### 3.4 Character Select Screen (MEDIUM PRIORITY)
**Impact**: ⭐⭐⭐⭐ (Required for multiple characters)
**Effort**: Medium

- [ ] Character grid layout
- [ ] Character portraits
- [ ] Player 1 and Player 2 cursors
- [ ] Random select option
- [ ] Character preview animations
- [ ] Stage select (optional)

---

### TIER 4: Advanced Mechanics (Make it Authentic SF3)
**Goal**: Implement SF3-specific systems that define the game

#### 4.1 Parry System (VERY HIGH PRIORITY for SF3 authenticity)
**Impact**: ⭐⭐⭐⭐⭐ (THE signature SF3 mechanic)
**Effort**: High

**Ground Parry**:
- [ ] Tap forward to parry high attacks (10-frame window)
- [ ] Tap down to parry low attacks (10-frame window)
- [ ] Held input reduces window to 6 frames
- [ ] Parry freeze (16 frames for both players)
- [ ] Parry sound/visual effect
- [ ] No chip damage on parry
- [ ] Frame advantage on parry

**Air Parry**:
- [ ] Tap forward/down during jump (7-frame window)
- [ ] Reset to neutral in air
- [ ] Different properties than ground parry

**Red Parry** (Advanced):
- [ ] Parry during blockstun
- [ ] Only 2-frame window
- [ ] Massive frame advantage

**Auto-Parry**:
- [ ] Subsequent hits auto-parry if within 2-frame window
- [ ] Essential for multi-hit moves

This is THE feature that makes SF3 unique. Should be high priority after basic combat is complete.

#### 4.2 Super Meter and Super Arts (HIGH PRIORITY)
**Impact**: ⭐⭐⭐⭐⭐ (Core SF3 mechanic)
**Effort**: High

**Super Meter**:
- [ ] Meter gain on hit (5 units)
- [ ] Meter gain on block (2 units)
- [ ] Meter gain on whiff (1 unit)
- [ ] Max meter = 100 units
- [ ] Meter carries between rounds
- [ ] Visual meter bar

**Akuma's Super Arts** (choose 1 per match):
- [ ] SA1: Messatsu Gou Hadou (QCFx2 + P) - 1 stock, multi-hit fireball
- [ ] SA2: Messatsu Gou Shoryu (QCFx2 + K) - 2 stocks, invincible DP
- [ ] SA3: Kongou Kokuretsu Zan (QCFx2 + P) - 3 stocks, ground pound

**Super Art Selection**:
- [ ] Choose super at character select
- [ ] Different meter lengths per super (SA1 = short, SA3 = long)
- [ ] EX moves consume meter (if SA allows multiple stocks)

#### 4.3 EX Moves (MEDIUM PRIORITY)
**Impact**: ⭐⭐⭐⭐ (Important depth mechanic)
**Effort**: Medium

- [ ] Execute with PP or KK (two buttons)
- [ ] Costs 1/3 of super meter
- [ ] Enhanced properties (faster, more damage, invincibility)
- [ ] EX Gohadoken (2 hits, faster)
- [ ] EX Goshoryuken (full invincibility, 5 hits)
- [ ] EX Tatsumaki (more hits, juggle properties)

#### 4.4 Guard Break (LOW PRIORITY)
**Impact**: ⭐⭐ (Rare occurrence, low priority)
**Effort**: Low

- [ ] Track "guard meter" (hidden)
- [ ] Depletes when blocking attacks
- [ ] Guard break stun if meter fully depleted
- [ ] Vulnerable to big punish
- [ ] Visual guard break effect

---

### TIER 5: Content Expansion (Make it Bigger)
**Goal**: Add more characters, stages, variety

#### 5.1 Add Second Character - Ryu (HIGH PRIORITY)
**Impact**: ⭐⭐⭐⭐⭐ (Doubles content, proves system works)
**Effort**: High (but easier now that framework exists)

**Why Ryu Next?**:
- Shares moves with Akuma (Hadoken, Shoryuken, Tatsumaki)
- Can reuse some sprites (same style)
- Different frame data and properties
- Ken would be even easier after Ryu

**Ryu-Specific**:
- [ ] Ryu sprites (justnopoint.com)
- [ ] Denjin Hadoken (charge fireball)
- [ ] Higher health than Akuma (160 vs 145)
- [ ] Different walk speed, jump arc
- [ ] Different super arts (Shinku Hadoken, Shin Shoryuken, Denjin Hadoken)

#### 5.2 Add More Stages (MEDIUM PRIORITY)
**Impact**: ⭐⭐⭐ (Visual variety)
**Effort**: Low (just finding/loading images)

- [ ] Ken's stage (ship)
- [ ] Chun-Li's stage (market)
- [ ] Yun/Yang's stage (Hong Kong)
- [ ] Stage parallax scrolling (optional)
- [ ] Stage-specific music

#### 5.3 Add Third Character - Ken (MEDIUM PRIORITY)
**Impact**: ⭐⭐⭐⭐ (Similar to Ryu, easier to implement)
**Effort**: Medium

- [ ] Ken sprites
- [ ] Faster Shoryuken
- [ ] Different Tatsumaki properties
- [ ] Shippu Jinrai Kyaku (forward kicks)

---

### TIER 6: Training Mode Features (For Competitive Players)
**Goal**: Add tools for learning and practice

#### 6.1 Training Mode Basics (LOW PRIORITY)
**Impact**: ⭐⭐⭐ (Important for serious players)
**Effort**: Medium

- [ ] Dummy controls (stand, crouch, jump, block, record)
- [ ] Reset positions button
- [ ] Infinite health toggle
- [ ] Infinite meter toggle
- [ ] Display frame data on screen
- [ ] Hitbox visualization (already have debug mode!)
- [ ] Input display (show last 10 inputs)

#### 6.2 Advanced Training Features (VERY LOW PRIORITY)
**Impact**: ⭐⭐ (Nice to have for advanced players)
**Effort**: High

- [ ] Record/playback dummy actions
- [ ] Frame-by-frame stepping
- [ ] Save states
- [ ] Counter-hit toggle
- [ ] Randomized blocking
- [ ] Punish training (auto-block, show punish window)

---

### TIER 7: Online Play (Future Vision)
**Goal**: Enable online multiplayer (VERY ambitious)

#### 7.1 Rollback Netcode (EXTREMELY HIGH EFFORT)
**Impact**: ⭐⭐⭐⭐⭐ (Modern standard for online fighters)
**Effort**: Extremely High (months of work)

This is a massive undertaking that requires:
- [ ] Deterministic game state
- [ ] Serialize/deserialize full game state
- [ ] Rollback and re-simulate on desync
- [ ] Input delay compensation
- [ ] Network protocol (UDP for low latency)
- [ ] GGPO or similar library integration

**Recommendation**: Only attempt this MUCH later when core game is polished.

---

## 📊 Recommended Priority Order

### Phase 1: "Playable Game" (Weeks 1-3)
1. ✅ Complete all standing normals (6 total)
2. ✅ Complete all crouching normals (6 total)
3. ✅ Complete all jump normals (6 total)
4. ✅ Implement Gohadoken (projectile system)
5. ✅ Implement Goshoryuken (invincibility, knockdown)
6. ✅ Implement Tatsumaki
7. ✅ Add throws
8. ✅ Add knockdown/wakeup
9. ✅ Add pushback system

**Result**: Full 1v1 Akuma mirror matches possible!

### Phase 2: "Feels Good" (Weeks 4-5)
1. ✅ Add screen shake
2. ✅ Add sound effects (hits, blocks, moves)
3. ✅ Add round system
4. ✅ Add KO state
5. ✅ Polish VFX

**Result**: Game feels satisfying and complete!

### Phase 3: "Authentic SF3" (Weeks 6-8)
1. ✅ Implement parry system (THE signature mechanic)
2. ✅ Implement super meter
3. ✅ Implement Akuma's super arts
4. ✅ Implement EX moves

**Result**: It's actually SF3:3S now!

### Phase 4: "Real Game" (Weeks 9-12)
1. ✅ Add Ryu (second character)
2. ✅ Add main menu
3. ✅ Add character select
4. ✅ Add more stages
5. ✅ Add training mode basics

**Result**: Publishable game!

### Phase 5: "Expansion" (Months 4+)
1. Add Ken, Chun-Li, Yun, etc.
2. Advanced training features
3. Combo trials
4. (Maybe) Rollback netcode

---

## 🎯 Quick Wins (High Impact, Low Effort)

These should be done ASAP for maximum improvement:

1. **Screen Shake** (2 hours) - Massive impact on feel
2. **Pushback System** (4 hours) - Critical for spacing
3. **Round Timer** (2 hours) - Adds urgency
4. **KO State** (3 hours) - Required for win condition
5. **Standing Medium/Heavy Punch** (4 hours each) - More attack variety

---

## 🔥 The "Make it Feel Like SF3" Priority List

If I had to pick the TOP 10 improvements for maximum authenticity:

1. **Complete Akuma's normal moves** (all 18 attacks)
2. **Implement Gohadoken** (projectile system)
3. **Implement Goshoryuken** (invincibility frames)
4. **Implement Tatsumaki** (multi-hit)
5. **Add pushback on hit/block** (spacing is everything)
6. **Add parry system** (THE SF3 mechanic)
7. **Add sound effects** (transforms feel)
8. **Add round system** (makes it a game)
9. **Add super meter and super arts** (big moments)
10. **Add screen shake** (impact feedback)

---

## 📈 Metrics for Success

How do we know we're making progress?

- **Playability**: Can two players have a full match? (Not yet - need normals)
- **Fun Factor**: Is it satisfying to land combos? (Partially - need sound + shake)
- **Authenticity**: Does it feel like SF3? (Not yet - need parries)
- **Completeness**: Can you pick characters, play rounds, win? (No - need menus)
- **Depth**: Are there advanced techniques? (Not yet - need cancels, parries, meter)

---

**Last Updated**: 2025-10-11
**Total Items**: 150+ improvements identified
**Estimated Time to "Complete"**: 3-6 months of focused development
