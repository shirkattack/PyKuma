# SF3:3S Source Code Navigation Guide
## For Non-C Programmers

This guide helps you explore the SF3 decompilation source code to understand game mechanics, even without C knowledge.

---

## 🎯 Most Important Files to Study

### 1. **HITCHECK.c** - Collision Detection System
**Link**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/HITCHECK.c

**Why it's interesting**: This is the heart of SF3's combat - how attacks hit, block, and connect.

**What to look for**:
- Function names like `attack_hit_check()`, `catch_hit_check()`, `set_struck_status()` 
- Look for loops (lines with `for` or `while`) - these check all hitboxes
- Look for `if` statements with conditions - these are the collision rules
- Variable names like `h_att` (attack hitbox), `h_bod` (body hurtbox), `damage`, `guard` 

**Key concepts you'll see**:
```c
// Pseudocode translation of what you'll see:
for each attacker:
    for each defender:
        if (attack_box overlaps body_box):
            if (defender is blocking):
                apply_blockstun()
            else:
                apply_damage()
```

**Questions this file answers**:
- How does the game check if an attack hits?
- What happens when you block vs get hit?
- How does the priority system work?
- How are throws different from normal attacks?

---

### 2. **PLMAIN.c** - Character State Machine
**Link**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/PLMAIN.c

**Why it's interesting**: This controls what state a character is in (standing, attacking, hurt, etc.)

**What to look for**:
- Functions named `player_mv_####()` - these are different game phases
- Array definitions like `plmain_lv_00[]` - these are state transition tables
- Variables like `routine_no[0]`, `routine_no[1]`, `routine_no[2]` - the 3-level state system
- Switch statements `switch(state)` - these handle different states

**Key pattern you'll see**:
```c
// State hierarchy
routine_no[0] = 4000;  // Main gameplay
routine_no[1] = 10;    // Attacking state
routine_no[2] = 5;     // Specific move (like cr.MK)
```

**Questions this file answers**:
- How does SF3 organize character states?
- How do characters transition from neutral to attacking?
- What happens when you get hit during an attack?
- How does the game know when an animation is done?

---

### 3. **CMD_MAIN.c** - Input Command System
**Link**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/CMD_MAIN.c

**Why it's interesting**: This is how special moves are detected (QCF+P = Hadouken)

**What to look for**:
- Arrays like `waza_ptr[]` or `cmd_table[]` - these store move commands
- Bit operations `&`, `|`, `<<` - these check button states efficiently
- Input buffer variables - usually named `lever`, `button`, `history` 
- Functions checking sequences of inputs

**Key pattern**:
```c
// Checking for Quarter Circle Forward (↓↘→)
if (input[0] == DOWN &&
    input[1] == DOWN_FORWARD &&
    input[2] == FORWARD &&
    button_pressed(PUNCH)) {
    // Execute Hadouken
}
```

**Questions this file answers**:
- How long does the input buffer last?
- How does SF3 detect motion inputs?
- Can you buffer inputs during hitstun?
- What's the difference between light/medium/heavy versions?

---

### 4. **PLPAT02.c** - Ryu's Move Data
**Link**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/PLPAT02.c

**Why it's interesting**: This shows how a specific character's moves are implemented.

**What to look for**:
- Function names like `Att_HADOUKEN()`, `Att_SHOURYUUKEN()` - special move implementations
- Projectile spawning code
- Animation frame counters
- Hit detection setup for each move

**Key pattern**:
```c
Att_HADOUKEN() {
    switch(routine_step) {
        case 0:  // Startup
            animate_wind_up();
            break;
        case 1:  // Active - spawn projectile
            create_projectile(x, y, speed);
            break;
        case 2:  // Recovery
            return_to_neutral();
            break;
    }
}
```

**Questions this file answers**:
- How are special moves structured?
- When do projectiles spawn during the animation?
- How does the game handle different button strengths (LP/MP/HP)?
- What happens during super flash?

---

### 5. **structs.h** - Data Structure Definitions
**Link**: https://github.com/crowded-street/3s-decomp/blob/main/include/structs.h

**Why it's interesting**: This shows what data the game tracks for each character.

**What to look for**:
- `struct WORK` - main character data (around line 100+)
- Field names like `position_x`, `vitality`, `direction`, `hit_range` 
- Offsets like `0x54`, `0x9C` - these show memory layout
- Pointer variables (ones with `*`) - these reference other data

**Key structure to understand**:
```c
struct WORK {
    // Position
    short position_x;    // X coordinate
    short position_y;    // Y coordinate

    // State
    int vitality;        // Health
    byte direction;      // Facing left/right

    // Collision
    void* hit_ix_table;  // Pointer to hitbox data
    void* body_adrs;     // Pointer to hurtbox data

    // ... many more fields
};
```

**Questions this file answers**:
- What data does each character store?
- How is position tracked?
- Where are hitboxes stored?
- What flags track special states?

---

## 🔍 How to Read the Code (Without Knowing C)

### Pattern 1: Function Definitions
```c
void attack_hit_check(WORK* attacker, WORK* defender) {
    // Code here
}
```
**Translation**: "This function checks if attacker's attack hit defender"

### Pattern 2: If Statements (Logic)
```c
if (defender->direction == LEFT && attack_from_right) {
    apply_damage();
} else {
    apply_block();
}
```
**Translation**: "If defender faces left AND attack comes from right, then damage, otherwise block"

### Pattern 3: Loops (Repetition)
```c
for (int i = 0; i < num_hitboxes; i++) {
    check_hitbox(hitbox[i]);
}
```
**Translation**: "For each hitbox in the list, check if it collides"

### Pattern 4: Switch Statements (Multiple Options)
```c
switch (state) {
    case STANDING:
        handle_standing();
        break;
    case ATTACKING:
        handle_attacking();
        break;
}
```
**Translation**: "Depending on what state we're in, do different things"

### Pattern 5: Arrays and Tables
```c
int damage_table[] = {10, 15, 20};  // LP, MP, HP
```
**Translation**: "This is a list of damage values for light, medium, heavy"

---

## 📚 Interesting Sections by Topic

### Topic: **How Blocking Works**

**Files to check**:
1. **HITCHECK.c** - Search for: `guard`, `block`, `struck` 
2. Look for functions with "guard" in the name

**What to notice**:
- Separate code paths for blocking vs getting hit
- Chip damage calculation (damage * 0.1 or similar)
- Blockstun formula (usually related to hitstun)
- High/low blocking logic

**Key line patterns**:
```c
if (holding_back && !is_overhead) {
    // Successful block
}
```

---

### Topic: **How Combos Work**

**Files to check**:
1. **HITCHECK.c** - Search for: `combo`, `cancel`, `chain` 
2. **PLMAIN.c** - Look at animation canceling logic

**What to notice**:
- "Cancelable frames" windows
- Combo counter incrementing
- Damage scaling based on combo length
- Juggle limit tracking

**Key patterns**:
```c
if (hit_connected && in_cancel_window && special_input) {
    cancel_current_animation();
    start_special_move();
}
```

---

### Topic: **How Projectiles Work**

**Files to check**:
1. **PLPAT02.c** (Ryu) - Search for: `HADOUKEN` 
2. Look for projectile spawn functions

**What to notice**:
- When projectile spawns (usually during "active" frames)
- Projectile speed by strength (light/medium/heavy)
- Projectile lifespan (how long it travels)
- Collision detection with projectiles

**Key patterns**:
```c
if (animation_frame == spawn_frame) {
    projectile = create_projectile();
    projectile->speed = speed_by_strength[button_strength];
}
```

---

### Topic: **How the Input Buffer Works**

**Files to check**:
1. **CMD_MAIN.c** - Main input detection
2. Look for arrays storing previous inputs

**What to notice**:
- Input history size (usually 10-15 frames)
- How motion inputs are detected (arrays of directions)
- Button press vs button release detection
- Priority when multiple commands match

**Key patterns**:
```c
// Store input history
input_buffer[current_frame % 15] = current_input;

// Check for QCF pattern in last 15 frames
if (matches_pattern(input_buffer, QCF_PATTERN)) {
    // Execute special move
}
```

---

## 🎮 Practical Exercise: Trace a Single Attack

Let's trace what happens when Ryu does a standing medium punch:

### Step 1: Input Detection
**File**: Player's input handling
- Player presses Medium Punch button
- Game records: `button = MP`, `direction = NEUTRAL` 

### Step 2: State Change
**File**: PLMAIN.c
- Current state: `STANDING` (routine_no[1] = NEUTRAL)
- Input detected: `MP` 
- State changes to: `ATTACKING` → `STANDING_MP` 

### Step 3: Animation Start
**File**: PLPAT02.c (Ryu's patterns)
- Look up `STANDING_MP` animation
- Load sprite sequence
- Set frame counter to 0
- Mark frames 6-8 as "active" (hitbox on)

### Step 4: Each Frame Update
**File**: PLMAIN.c + HITCHECK.c
- Frame 1-5: Startup (no hitbox)
- Frame 6-8: Active (hitbox enabled)
  - **HITCHECK.c** checks: Does hitbox overlap opponent?
  - If yes: Apply damage/blockstun
  - If no: Continue animation
- Frame 9-18: Recovery (no hitbox, can't cancel)

### Step 5: Return to Neutral
**File**: PLMAIN.c
- Animation complete
- State changes back to: `STANDING` (routine_no[1] = NEUTRAL)
- Ready for next input

---

## 🔗 Quick Reference Links

### Core Game Systems
- **Main Game Loop**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/Game.c
- **Collision System**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/HITCHECK.c
- **Character State**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/PLMAIN.c
- **Input System**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/CMD_MAIN.c

### Character-Specific Files
- **Ryu (PL02)**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/PLPAT02.c
- **Ken (PL03)**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/PLPAT03.c
- **Urien (PL00)**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/PLPAT00.c

### Data Structures
- **Main Structures**: https://github.com/crowded-street/3s-decomp/blob/main/include/structs.h
- **Common Headers**: https://github.com/crowded-street/3s-decomp/blob/main/include/common.h

### Special Systems
- **Super Meter**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/spgauge.c
- **Stun System**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/stun.c
- **Sound Effects**: https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/Sound3rd.c

---

## 💡 Tips for Exploring

1. **Use GitHub's search** (press `/` on any page)
   - Search for terms like: `damage`, `hitbox`, `block`, `combo` 

2. **Look at function names** - they're usually descriptive
   - `check_hit()` - probably checks if attack hit
   - `apply_damage()` - probably deals damage
   - `set_blockstun()` - probably sets blocking state

3. **Follow the flow**
   - Start at high-level functions (like `main_game_loop`)
   - Click on function calls to see what they do
   - Work your way down to specific details

4. **Focus on patterns, not syntax**
   - You don't need to understand every character
   - Look for repeated structures
   - Variable names tell you what they store

5. **Compare with your code**
   - When you see a concept (like input buffer)
   - Think: "How would I do this in Python?"
   - Adapt the concept, not the exact code

---

## 🎯 Most Useful Things to Learn

**Priority Order**:
1. ✅ **HITCHECK.c** - Collision detection logic
2. ✅ **PLMAIN.c** - State machine architecture
3. ✅ **CMD_MAIN.c** - Input buffering
4. ⚠️ **PLPAT##.c** - Character-specific moves (pick one character)
5. ⚠️ **structs.h** - Data organization

**Less Important for Now**:
- Graphics rendering code (PS2-specific)
- Audio playback (CRI middleware)
- Memory management (platform-specific)
- Save data handling

---

## 📝 Notes

- Many files return 404 - the repo is incomplete
- Some code uses Japanese romanization (Shouryuuken, Hadouken)
- The code is decompiled, so variable names are approximations
- Focus on **logic and structure**, not exact implementation

**Remember**: You're learning **game design patterns**, not C programming!

---

**Last Updated**: 2025-10-15
