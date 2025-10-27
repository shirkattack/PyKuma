# Street Fighter III: 3rd Strike - Development Roadmap

## 🎯 Project Vision

Transform our fighting game into a **pixel-perfect SF3:3S recreation** using **authentic Capcom algorithms** from the official decompilation, combined with modern Python practices, comprehensive data validation, and **next-generation AI integration**. We're building the **definitive SF3:3S experience** that surpasses the original with enhanced features while maintaining 100% gameplay accuracy.

---

## 🚨 Current State Assessment

### ✅ **What's Working Well:**
- Solid foundational architecture with clean separation of concerns
- YAML-based animation system (partial implementation)
- Responsive input system with motion detection
- Basic collision detection and state management
- Modern Python patterns (type hints, dataclasses)

### ⚠️ **Critical Issues to Address:**
- **Inauthentic Mechanics**: Current implementation doesn't match SF3:3S behavior
- **Missing SF3 Collision System**: No 32-slot hit queue or priority-based processing
- **Incorrect State Management**: Flat states vs SF3's 8-level routine hierarchy
- **No Parry System**: Missing frame-perfect parry mechanics with guard direction
- **No Damage Scaling**: Missing authentic combo scaling and hit counting
- **Positioning Inaccuracy**: No next-position prediction or rollback system
- **No Multi-Character Strategy**: Current system won't scale for SF3 roster
- **Basic Input System**: Missing SF3's input validation and CPU algorithm integration

### 🎯 **SF3:3S Decompilation Analysis:**
After analyzing the **official SF3:3S source code** from crowded-street/3s-decomp, we identified:

**🔥 Authentic Capcom Systems We Must Implement:**
- **32-Slot Hit Queue System** (HS hs[32]) with priority-based collision processing
- **8-Level State Hierarchy** (routine_no[0-7]) for complex character behavior
- **Professional Parry System** with frame-perfect timing and guard direction
- **Damage Scaling Algorithm** with combo hit counting and clean hit tracking
- **Position Rollback System** with old_pos tracking for accurate collision
- **Input Validation System** with illegal input correction and CPU integration
- **Multiple Hitbox Types** (h_att, h_bod, h_han) per frame
- **Throw Priority System** (catch_hit_check before attack_hit_check)

**📊 Frame Data Accuracy Requirements:**
- **Baston ESN3S Database**: Community gold standard for authentic frame data
- **Pixel-Perfect Hitboxes**: Multiple collision boxes per frame like SF3
- **Authentic Timing**: Exact startup/active/recovery frames from Capcom data

---

## 🏗️ **Phase 0: Authentic SF3 Foundation** 
*Priority: CRITICAL | Timeline: 2-3 weeks*

### **0.1 SF3 Source Code Integration (Week 1)**
**Goal**: Implement authentic Capcom algorithms from official decompilation

**Immediate SF3 System Implementation:**
1. **32-Slot Hit Queue System**
   ```python
   # /src/systems/sf3_collision.py
   class SF3CollisionSystem:
       def __init__(self):
           self.hit_status = [HitStatus() for _ in range(32)]  # HS hs[32]
           self.hit_queue_input = 0  # hpq_in
           self.catch_check_flag = False  # ca_check_flag
       
       def hit_check_main_process(self):
           """Exact replica of SF3's HITCHECK.c"""
           if self.hit_queue_input > 1:
               if self.catch_check_flag:
                   self.catch_hit_check()  # Throws processed FIRST
               self.attack_hit_check()     # Then normal attacks
               if self.set_judge_result():
                   self.check_result_extra()
           self.clear_hit_queue()
   ```

2. **8-Level State Machine**
   ```python
   # /src/systems/sf3_state.py
   class SF3StateManager:
       def __init__(self):
           self.routine_no = [0] * 8      # SF3's 8-level hierarchy
           self.old_routine_no = [0] * 8  # Position rollback support
           
       def player_move(self, wk: PlayerWork, input_data: int):
           """Exact replica of SF3's Player_move() from PLMAIN.c"""
           # Store previous states for rollback
           for i in range(8):
               wk.old_rno[i] = wk.routine_no[i]
           
           # Execute state function like SF3
           self.plmain_lv_00[wk.routine_no[0]](wk)
   ```

3. **Professional Input System**
   ```python
   # /src/systems/sf3_input.py
   class SF3InputSystem:
       def __init__(self):
           self.correct_lever_data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
           
       def check_illegal_lever_data(self, data: int) -> int:
           """Exact replica of SF3's input validation"""
           lever = data & 0xF
           return (data & ~0xF) | self.correct_lever_data[lever]
           
       def cpu_algorithm(self, wk: PlayerWork) -> int:
           """SF3's built-in AI system integration"""
           # AI generates inputs using same system as humans
           pass
   ```

### **0.2 Authentic Frame Data Integration (Week 2)**
**Goal**: Replace all frame data with authentic SF3 values from Baston ESN3S

**Data Migration Tasks:**
- [ ] **Download complete SF3 frame data** from baston.esn3s.com
- [ ] **Create SF3-accurate Pydantic schemas** matching WORK structure
- [ ] **Implement multiple hitbox types** (attack/body/hand per frame)
- [ ] **Add position prediction system** (next_x, next_y, next_z)
- [ ] **Validate against authentic SF3 behavior**

**SF3 Data Structures:**
```python
# /data/schemas/sf3_authentic.py
class SF3WorkStructure(BaseModel):
    """Matches SF3's WORK structure (0x388 bytes)"""
    position_x: float
    position_y: float
    position_z: float
    next_x: float      # Next frame position prediction
    next_y: float
    next_z: float
    current_colcd: int # Current collision code
    hit_range: int     # Hit detection range
    vitality: int      # Character health
    direction: int     # Facing direction (-1 or 1)
    routine_no: List[int] = Field(min_items=8, max_items=8)  # 8-level state

class SF3HitboxData(BaseModel):
    """Multiple hitbox types like SF3"""
    attack_boxes: List[HitboxData]  # h_att - areas that can hit
    body_boxes: List[HitboxData]    # h_bod - main hurtboxes
    hand_boxes: List[HitboxData]    # h_han - limb hurtboxes
    
class SF3FrameData(BaseModel):
    """Authentic SF3 frame data from Baston ESN3S"""
    startup: int = Field(ge=1, le=60)
    active: int = Field(ge=1, le=30)
    recovery: int = Field(ge=1, le=60)
    hit_advantage: int = Field(ge=-20, le=20)
    block_advantage: int = Field(ge=-20, le=20)
    damage: int = Field(ge=0, le=999)
    stun: int = Field(ge=0, le=100)
```

---

## 🏗️ **Phase 1: Modern Python Integration** 
*Priority: CRITICAL | Timeline: 2-3 weeks*

### **1.1 Pydantic Schema Foundation (Week 1)**
**Goal**: Wrap authentic SF3 systems with modern Python validation

**Implementation Priority:**
1. **Day 1-2: Base Types & Enums**
   ```python
   # /data/schemas/base.py
   class CharacterArchetype(str, Enum):
       SHOTO = "shoto"
       GRAPPLER = "grappler"
       RUSHDOWN = "rushdown"
       ZONER = "zoner"
   
   class HitType(str, Enum):
       LIGHT = "light"
       MEDIUM = "medium"
       HEAVY = "heavy"
       SPECIAL = "special"
       SUPER = "super"
   
   class Vector2(BaseModel):
       x: float = 0.0
       y: float = 0.0
   ```

2. **Day 3-4: Combat & Physics Data**
   ```python
   # /data/schemas/combat.py
   class FrameData(BaseModel):
       startup: int = Field(ge=1, le=60)
       active: int = Field(ge=1, le=30)
       recovery: int = Field(ge=1, le=60)
       
       @validator('total')
       def validate_frame_consistency(cls, v, values):
           expected = values['startup'] + values['active'] + values['recovery']
           if v != expected:
               raise ValueError(f"Total frames {v} != {expected}")
           return v
   
   class HitboxData(BaseModel):
       offset: Vector2
       size: Vector2
       damage: int = Field(ge=0, le=999)
       hitstun: int = Field(ge=0, le=100)
       hit_type: HitType
       active_frames: List[int] = Field(min_items=1)
       
       # AI metadata
       ai_utility: float = Field(ge=0, le=1, default=0.5)
       ai_risk_level: float = Field(ge=0, le=1, default=0.5)
   ```

3. **Day 5-7: Character Inheritance System**
   ```python
   # /data/schemas/character.py
   class MoveData(BaseModel):
       name: str
       frame_data: FrameData
       hitbox: Optional[HitboxData]
       actions: Dict[str, Any]  # For protocol action system
       ai_metadata: AIMoveMetadata
   
   class CharacterData(BaseModel):
       name: str
       archetype: CharacterArchetype
       base_moves: Dict[str, MoveData]      # Inherited moves
       unique_moves: Dict[str, MoveData]    # Character-specific
       move_overrides: Dict[str, MoveData]  # Override base moves
       ai_personality: AIPersonality
   
   class ShotuCharacterData(CharacterData):
       archetype: Literal[CharacterArchetype.SHOTO] = CharacterArchetype.SHOTO
       # Automatically includes Hadoken, Shoryuken, Tatsumaki
   ```

**New Data Structure:**
```
/data/
├── schemas/                   # Pydantic model definitions
│   ├── base.py               # Core types, enums, vectors
│   ├── combat.py             # Frame data, hitboxes, damage
│   ├── character.py          # Character data with inheritance
│   ├── ai.py                 # AI behavior and personality data
│   ├── collision.py          # Collision event schemas
│   └── actions.py            # Action protocol definitions
├── characters/               # Character-specific data
│   ├── base/                 # Shared data inheritance
│   │   ├── shoto_moves.yaml  # Shared Shoto archetype moves
│   │   ├── universal_moves.yaml # Walk, jump, etc.
│   │   └── physics.yaml      # Standard physics constants
│   ├── akuma/
│   │   ├── character.yaml    # Akuma-specific data + overrides
│   │   ├── unique_moves.yaml # Akuma-only moves
│   │   ├── ai_patterns.yaml  # AI behavior patterns
│   │   └── sprites/          # Sprite data
│   └── ken/                  # Future character
│       ├── character.yaml    # Ken-specific data + overrides
│       └── unique_moves.yaml # Ken-only moves
└── ai/                       # AI system data
    ├── behavior_trees.yaml   # Decision trees
    ├── training_data/        # ML training data
    └── models/               # Trained AI models
```

### **1.2 SF3 Parry & Guard System (Week 2)**
**Goal**: Implement authentic SF3 parry mechanics with frame-perfect timing

**Professional Parry Implementation:**
```python
# /src/systems/sf3_parry.py
class SF3ParrySystem:
    def __init__(self):
        self.parry_window = 7  # SF3's 7-frame parry window
        self.guard_directions = ["high", "mid", "low"]
        
    def defense_ground(self, attacker: PlayerWork, defender: PlayerWork, guard_dir: str) -> int:
        """Exact replica of SF3's defense_ground() function"""
        if self.check_parry_timing(defender, guard_dir):
            return 0  # Parry successful
        elif self.check_guard_success(defender, guard_dir):
            return 1  # Block successful
        else:
            return 2  # Hit confirmed
            
    def check_parry_timing(self, defender: PlayerWork, guard_dir: str) -> bool:
        """Frame-perfect parry detection like SF3"""
        # Check if input occurred within parry window
        # Validate guard direction matches attack type
        pass
        
    def set_parry_status(self, defender: PlayerWork):
        """Apply parry effects like SF3"""
        defender.routine_no[2] = "parry_success"
        defender.parry_advantage = 8  # SF3's parry advantage
```

**Damage Scaling System:**
```python
# /src/systems/sf3_damage.py
class SF3DamageSystem:
    def __init__(self):
        self.combo_scaling = [100, 90, 80, 70, 60, 50, 40, 30, 20, 10]  # SF3 scaling
        
    def calculate_damage(self, base_damage: int, combo_count: int) -> int:
        """Authentic SF3 damage scaling"""
        if combo_count >= len(self.combo_scaling):
            scale = self.combo_scaling[-1]
        else:
            scale = self.combo_scaling[combo_count]
        return int(base_damage * scale / 100)
        
    def grade_add_clean_hits(self, attacker: PlayerWork):
        """Track combo hits like SF3"""
        attacker.combo_count += 1
        attacker.clean_hits += 1
```

### **1.3 Position Rollback System (Week 3)**
**Goal**: Implement SF3's position prediction and rollback for accurate collision

**Position Management:**
```python
# /src/systems/sf3_position.py
class SF3PositionSystem:
    def __init__(self):
        self.position_history = deque(maxlen=60)  # 1 second of history
        
    def update_position(self, player: PlayerWork):
        """Store position history like SF3"""
        # Store old position for rollback
        for i in range(3):
            player.old_pos[i] = player.xyz[i].disp.pos
            
        # Calculate next position for collision prediction
        player.next_x = player.position_x + player.velocity_x
        player.next_y = player.position_y + player.velocity_y
        player.next_z = player.position_z + player.velocity_z
        
        # Store in history for rollback
        self.position_history.append({
            'frame': player.current_frame,
            'pos': [player.position_x, player.position_y, player.position_z],
            'routine_no': player.routine_no.copy()
        })
        
    def rollback_to_frame(self, target_frame: int) -> Optional[Dict]:
        """Rollback to specific frame for netplay/debugging"""
        for state in reversed(self.position_history):
            if state['frame'] == target_frame:
                return state
        return None
```

---

## 🏗️ **Phase 2: Authentic Character Implementation**
*Priority: HIGH | Timeline: 3-4 weeks*

### **2.1 Akuma SF3 Accuracy Implementation**
**Goal**: Make Akuma 100% accurate to SF3:3S using authentic data

**Authentic Akuma Implementation:**
- [ ] **Import Akuma frame data** from Baston ESN3S database
- [ ] **Implement SF3 Akuma moveset** with exact properties:
  - **Gohadoken**: Startup 13, Active 2, Recovery 31 (authentic SF3 timing)
  - **Goshoryuken**: 3-frame startup, full invincibility, authentic damage
  - **Tatsumaki Zankukyaku**: Air/ground versions with exact properties
  - **Messatsu Gou Hadou**: Super Art with authentic scaling
- [ ] **Multiple hitboxes per move** (attack/body/hand like SF3)
- [ ] **Authentic character stats** (health, stun, walk speed, jump arc)
- [ ] **SF3 Akuma AI patterns** using cpu_algorithm integration

**SF3 Akuma Specifications:**
```yaml
# /data/characters/akuma/sf3_authentic.yaml
character_name: "Akuma"
sf3_character_id: 14  # Baston ESN3S ID
health: 1050          # SF3 authentic health
stun: 64              # SF3 authentic stun
walk_speed: 0.032     # SF3 authentic movement
jump_startup: 4       # SF3 authentic jump frames

moves:
  standing_medium_punch:
    startup: 5
    active: 3    # Corrected from our current 4
    recovery: 10 # Corrected from our current 9
    damage: 115  # SF3 authentic damage
    stun: 7      # SF3 authentic stun
    hit_advantage: 2
    block_advantage: 1
    hitboxes:
      attack: [{ offset_x: 50, offset_y: -65, width: 60, height: 40 }]
      body: [{ offset_x: 0, offset_y: -80, width: 40, height: 80 }]
      hand: [{ offset_x: 30, offset_y: -65, width: 25, height: 25 }]
```

**Character Inheritance Example:**
```yaml
# /data/characters/base/shoto_moves.yaml
hadoken:
  frame_data:
    startup: 13
    active: 2
    recovery: 31
  hitbox:
    damage: 60
    hit_type: "special"
  ai_metadata:
    utility_score: 0.7
    preferred_ranges: ["medium", "far"]

# /data/characters/akuma/character.yaml
extends: "base/shoto"
move_overrides:
  hadoken:
    frame_data:
      startup: 11  # Akuma's is faster
    hitbox:
      damage: 70   # Akuma's does more damage
unique_moves:
  gohadoken:
    frame_data: {...}
    ai_metadata:
      utility_score: 0.8
```

### **2.2 AI Integration Architecture**
**Goal**: Implement AI-ready interfaces and data structures

**Core AI Components:**
```python
# /data/schemas/ai.py
class AIPersonality(BaseModel):
    aggression: float = Field(ge=0, le=1)
    risk_taking: float = Field(ge=0, le=1)
    combo_preference: float = Field(ge=0, le=1)
    zoning_preference: float = Field(ge=0, le=1)
    reaction_time_ms: int = Field(ge=50, le=500)

class GameState(BaseModel):
    """Complete game state for AI decision making"""
    player_pos: Vector2
    enemy_pos: Vector2
    player_health: float
    enemy_health: float
    distance: float
    frame_advantage: int
    # we need to know the time on the clock too
    # All data AI needs for decisions

class AIController:
    def __init__(self, character_data: CharacterData, ai_model: AIModel):
        self.character_data = character_data
        self.ai_model = ai_model
    
    def get_next_action(self, game_state: GameState) -> InputAction:
        return self.ai_model.predict(game_state, self.character_data)
```

**AI Model Support:**
- [ ] **Rule-Based AI**: Traditional behavior trees and hardcoded strategies
- [ ] **ML-Based AI**: Neural network integration for advanced behavior
- [ ] **Hybrid AI**: Combination of rules and machine learning
- [ ] **AI Training Pipeline**: Data collection and model training infrastructure

### **2.3 Component Architecture Implementation**
**Goal**: Modular, testable component system

**Core Components:**
```python
class PhysicsComponent:
    def __init__(self, mass: float, gravity: float):
        self.mass = mass
        self.gravity = gravity
        self.velocity = Vector2()
        self.acceleration = Vector2()

class RenderComponent:
    def __init__(self, sprite_data: SpriteData):
        self.current_sprite = sprite_data
        self.position_offset = Vector2()
        self.scale = Vector2(1.0, 1.0)

class AIComponent:
    def __init__(self, ai_controller: AIController):
        self.controller = ai_controller
        self.decision_history = []
        
class BaseActiveObject:
    def __init__(self, config: ObjectConfig):
        self.physics = PhysicsComponent(config.mass, config.gravity)
        self.render = RenderComponent(config.sprite_data)
        self.ai = AIComponent(config.ai_controller) if config.ai_enabled else None
        self.collision_events = CollisionEventManager()
```

---

## 🤺 **Phase 3: Advanced Combat Systems & Ken Implementation**
*Priority: MEDIUM | Timeline: 3-4 weeks*

### **3.1 Complete Box System Implementation**
**Goal**: Implement all 7 collision box types from professional standards

**Box Types to Add:**
- [ ] **Pushbox**: Character spacing and positioning
- [ ] **Grabbox**: Throw attempt collision  
- [ ] **Takebox**: Being grabbed collision
- [ ] **Triggerbox**: Conditional state changes
- [ ] **Boundingbox**: Ground collision and stage boundaries
- [ ] **Enhanced Hitbox**: Multi-hit, priority system
- [ ] **Enhanced Hurtbox**: Invincibility frames, armor

### **3.2 Advanced Combat Mechanics**
**Goal**: Implement professional fighting game systems

**Systems to Build:**
- [ ] **Damage Scaling System**: Combo damage reduction with AI-readable data
- [ ] **Combo Tracking**: Hit counter, combo list for AI analysis
- [ ] **Block System**: High/mid/low blocking with chip damage
- [ ] **Parry System**: Frame-perfect defensive mechanics
- [ ] **Juggle System**: Air combo limitations
- [ ] **Wall Bounce Physics**: Corner interactions
- [ ] **Priority System**: Attack vs attack resolution

### **3.3 Ken Character Implementation**
**Goal**: Prove multi-character architecture with Ken

**Ken Implementation:**
- [ ] **Inherit from Shoto base** with shared moves
- [ ] **Override Shoto moves** with Ken-specific properties
- [ ] **Add Ken unique moves** (Heavy Shoryuken variations, Tatsumaki variations)
- [ ] **Ken AI personality** (more aggressive than Akuma)
- [ ] **Validate inheritance system** works correctly

**Ken vs Akuma Differences:**
```yaml
# Ken's overrides
hadoken:
  frame_data:
    startup: 15  # Slower than Akuma
  hitbox:
    damage: 50   # Less damage than Akuma
  ai_metadata:
    utility_score: 0.6  # Ken prefers rushdown over zoning

# Ken's AI personality
ai_personality:
  aggression: 0.9      # Very aggressive
  risk_taking: 0.7     # High risk tolerance
  combo_preference: 0.9 # Loves combos
  zoning_preference: 0.3 # Doesn't like zoning
```

---

## 🎮 **Phase 4: Enhanced Animation & Visual Systems**
*Priority: MEDIUM | Timeline: 2-3 weeks*

### **4.1 Frame-Perfect Animation Control**
**Goal**: Professional animation timing with per-frame data

**Features:**
- [ ] **Per-frame position offsets** (solve sprite alignment issues)
- [ ] **Frame-specific collision boxes** (hitboxes that change per frame)
- [ ] **Animation events** (sound, effects, state changes on specific frames)
- [ ] **Dynamic physics properties** (friction, bounce per frame)
- [ ] **AI animation analysis** (frame advantage calculation)

### **4.2 Advanced Visual Systems**
**Goal**: Professional visual effects and feedback

**Systems:**
- [ ] **Hit spark system** with different effects per attack type
- [ ] **Screen shake** with intensity scaling
- [ ] **Slow motion effects** for dramatic moments
- [ ] **Color flashing** for invincibility and hit confirmation
- [ ] **Particle effects** for special moves

---

## 🤖 **Phase 5: AI Integration & Training**
*Priority: LOW | Timeline: 4-6 weeks*

### **5.1 AI Controller Implementation**
**Goal**: Multiple AI approaches with standardized interface

**AI Models:**
- [ ] **Rule-Based AI**: Behavior trees with character-specific strategies
- [ ] **ML-Based AI**: Neural network for advanced decision making
- [ ] **Hybrid AI**: Combination of rules and machine learning
- [ ] **Difficulty Scaling**: AI that adapts to player skill level

### **5.2 AI Training Pipeline**
**Goal**: Infrastructure for AI development and improvement

**Training Systems:**
- [ ] **Game State Recording**: Capture all game states for training data
- [ ] **Replay Analysis**: AI learns from high-level play
- [ ] **Self-Play Training**: AI improves by playing against itself
- [ ] **Behavior Evaluation**: Metrics for AI performance and personality

### **5.3 Advanced AI Features**
**Goal**: Professional-grade AI opponents

**Features:**
- [ ] **Adaptive Difficulty**: AI adjusts to player skill in real-time
- [ ] **Personality Preservation**: AI maintains character-specific behavior
- [ ] **Learning from Player**: AI adapts to player patterns
- [ ] **Tournament Mode**: AI that plays like professional players

---

## 🏆 **Phase 6: Polish and Professional Features**
*Priority: LOW | Timeline: 3-4 weeks*

### **6.1 User Interface**
**Goal**: Professional game interface

**Systems:**
- [ ] **Character select screen** with AI difficulty selection
- [ ] **Training mode UI** with frame data display and AI sparring
- [ ] **Replay system** for match analysis and AI training
- [ ] **AI behavior editor** for customizing AI personalities

### **6.2 Content Expansion**
**Goal**: Additional characters and stages

**Additional Characters:**
- [ ] **Chun-Li**: Charge character with different AI patterns
- [ ] **Makoto**: Rush-down character with aggressive AI
- [ ] **Ryu**: Balanced Shoto for AI training baseline

**Stage System:**
- [ ] **Multiple stages** with AI-aware stage positioning
- [ ] **Stage-specific AI behavior** (corner awareness, stage hazards)

---

## 📊 **Success Metrics**

### **Technical Excellence:**
- [ ] **Zero runtime data validation errors** with Pydantic
- [ ] **100% test coverage** for core systems and AI components
- [ ] **Sub-16ms frame time** (60 FPS locked) with AI processing
- [ ] **Memory usage < 150MB** during gameplay with AI active
- [ ] **Type safety** with mypy validation across all modules

### **Fighting Game Quality:**
- [ ] **Frame-perfect input response** (1-frame input lag max)
- [ ] **Accurate hitbox collision** (pixel-perfect with event-driven system)
- [ ] **Consistent frame data** across all characters and moves
- [ ] **Professional-level game feel** with proper hitstop, screen shake, etc.
- [ ] **Balanced AI opponents** that feel human-like

### **Architecture Quality:**
- [ ] **Multi-character scalability** proven with Akuma and Ken
- [ ] **AI integration** working with multiple AI models
- [ ] **Data inheritance** system validated across character archetypes
- [ ] **Component architecture** enabling easy feature addition
- [ ] **Extensible action system** supporting new mechanics

### **AI Performance:**
- [ ] **Adaptive difficulty** that matches player skill level
- [ ] **Character personality preservation** in AI behavior
- [ ] **Training pipeline** producing improving AI models
- [ ] **Real-time decision making** under 16ms per frame

---

## 🛠️ **Development Guidelines**

### **Code Standards:**
- **Type hints everywhere** - No untyped code, full mypy compliance
- **Pydantic validation** - All data must be validated at runtime
- **Protocol-based interfaces** - Extensible, testable architecture
- **Component composition** - Modular, reusable components
- **Comprehensive testing** - Unit, integration, and AI behavior tests

### **Data Standards:**
- **YAML + Pydantic** - All configuration with runtime validation
- **Character inheritance** - Shared data through archetype system
- **AI-ready metadata** - All data includes AI decision-making information
- **Schema versioning** - Track and migrate data schema changes
- **Consistent naming** - snake_case files, PascalCase classes, clear hierarchies

### **AI Standards:**
- **Standardized interfaces** - All AI models use same GameState input
- **Personality preservation** - AI behavior matches character archetype
- **Training data collection** - All games recorded for AI improvement
- **Ethical AI** - Fair, balanced opponents that enhance player experience

### **Testing Strategy:**
- **Unit tests** for all business logic and AI components
- **Integration tests** for system interactions and data flow
- **Performance tests** for frame timing with AI active
- **AI behavior tests** for personality and difficulty validation
- **Data validation tests** for all Pydantic schemas
- **Visual regression tests** for animations and effects

---

## 🎯 **Implementation Strategy Based on SF3 Research**

### **✅ What to KEEP (Foundation is Solid)**
- **Project Structure**: `/src/street_fighter_3rd/` organization is superior to SF3's monolithic C files
- **YAML Data Approach**: More maintainable than hardcoded C arrays
- **Modern Python Patterns**: Type hints, clean imports, professional practices
- **Asset Pipeline**: `/tools/sprite_extraction/` working with real SF3 sprites
- **Pygame Foundation**: Excellent choice for 2D fighting game development

### **🗑️ What to SCRAP (Inaccurate to SF3)**
- **Current collision system** - Too basic, missing SF3's 32-slot hit queue complexity
- **Flat state management** - SF3 uses 8-level hierarchy (`routine_no[0-7]`)
- **Basic input handling** - Missing SF3's buffer, validation, and pattern matching
- **Single hitbox per frame** - SF3 has attack/body/hand hitboxes per frame
- **Hardcoded frame data** - Doesn't match authentic SF3 values from Baston ESN3S
- **No parry system** - Core SF3 mechanic completely missing
- **No damage scaling** - Essential for authentic combo mechanics

### **🛡️ Error Prevention Strategy**
1. **Implement authentic mechanics FIRST** - Build SF3 foundation before modern Python wrappers
2. **Validate against SF3 behavior continuously** - Test every system against known SF3 data
3. **Use authentic frame data from Day 1** - Import from Baston ESN3S immediately
4. **Don't build on wrong mechanics** - Avoid complex systems on inaccurate foundation

## 🎯 **Immediate Next Steps (Phase 0: Authentic SF3 Foundation)**

### **Week 1: Core SF3 Systems**

**Day 1-2: SF3 Data Structures**
```python
# /src/systems/sf3_core.py - Exact replica of SF3's WORK structure
class SF3WorkStructure:
    position_x: float
    position_y: float  
    position_z: float
    next_x: float      # SF3's position prediction
    next_y: float
    next_z: float
    routine_no: List[int] = Field(min_items=8, max_items=8)  # 8-level state
    vitality: int
    direction: int
    hit_range: int
```

**Day 3-4: 32-Slot Hit Queue System**
```python
# /src/systems/sf3_collision.py - Exact replica of HITCHECK.c
class SF3CollisionSystem:
    def __init__(self):
        self.hit_status = [HitStatus() for _ in range(32)]  # HS hs[32]
        self.hit_queue_input = 0  # hpq_in
        
    def hit_check_main_process(self):
        """Exact replica of SF3's collision processing"""
        if self.hit_queue_input > 1:
            if self.catch_check_flag:
                self.catch_hit_check()  # Throws processed FIRST
            self.attack_hit_check()     # Then normal attacks
```

**Day 5-7: 8-Level State Machine**
```python
# /src/systems/sf3_state.py - Exact replica of PLMAIN.c
class SF3StateManager:
    def player_move(self, wk: PlayerWork, input_data: int):
        """Exact replica of SF3's Player_move()"""
        # Store old states for rollback
        for i in range(8):
            wk.old_rno[i] = wk.routine_no[i]
        
        # Execute state function like SF3
        self.plmain_lv_00[wk.routine_no[0]](wk)
```

### **Week 2: Authentic Akuma Implementation**

**Authentic SF3 Frame Data Integration:**
```yaml
# /data/characters/akuma/sf3_authentic.yaml
standing_medium_punch:
  startup: 5     # Authentic SF3 value from Baston ESN3S
  active: 3      # Corrected from our wrong 4
  recovery: 10   # Corrected from our wrong 9
  damage: 115    # Authentic SF3 damage
  stun: 7        # Authentic SF3 stun
  hitboxes:
    attack: [{ offset_x: 50, offset_y: -65, width: 60, height: 40 }]
    body: [{ offset_x: 0, offset_y: -80, width: 40, height: 80 }]
    hand: [{ offset_x: 30, offset_y: -65, width: 25, height: 25 }]
```

**SF3 Systems Integration:**
- [ ] **Parry system** with 7-frame window and guard direction
- [ ] **Damage scaling** with authentic SF3 combo scaling [100,90,80,70,60,50,40,30,20,10]
- [ ] **Position rollback** system with next_pos prediction
- [ ] **Multiple hitbox types** (attack/body/hand) per frame

### **Week 3: Modern Python Integration**

**Pydantic Wrappers Around Authentic Systems:**
```python
# /src/schemas/sf3_schemas.py - Type-safe wrappers
class SF3CollisionManager(BaseModel):
    """Pydantic wrapper around authentic SF3 collision system"""
    collision_system: SF3CollisionSystem
    
    def validate_hit_queue_size(self):
        assert len(self.collision_system.hit_status) == 32
```

### **Success Criteria (Phase 0 Complete When):**
- ✅ **Akuma's standing medium punch** has exact SF3 timing (5/3/10 frames)
- ✅ **Parry system** works with 7-frame window
- ✅ **Damage scaling** matches SF3's authentic formula
- ✅ **Multiple hitboxes** per frame (attack/body/hand)
- ✅ **State machine** uses 8-level hierarchy
- ✅ **Position system** has next_pos prediction
- ✅ **32-slot hit queue** processes collisions with SF3 priority

### **Quality Gates:**
```python
# Every system must pass SF3 authenticity tests
def test_sf3_authenticity():
    assert akuma.standing_mp.startup == 5  # Baston ESN3S value
    assert parry_system.window == 7        # SF3 authentic
    assert len(collision.hit_status) == 32 # SF3 hit queue size
    assert damage_scaling == [100,90,80,70,60,50,40,30,20,10]  # SF3 scaling
```

---

## 🚀 **Project Transformation Summary**

**From Hobby Project To Definitive SF3:3S Recreation:**

### **Before (Current State):**
- Inaccurate frame data and mechanics
- Basic collision system missing SF3 complexity
- No parry system or damage scaling
- Single character with positioning issues
- No authentic fighting game behavior

### **After (Target State):**
- **100% Authentic SF3:3S Recreation** using official Capcom source code
- **32-Slot Hit Queue System** with priority-based collision processing
- **8-Level State Machine** matching SF3's routine hierarchy exactly
- **Frame-Perfect Parry System** with 7-frame window and guard direction
- **Authentic Damage Scaling** with SF3's exact combo scaling formula
- **Position Rollback System** for pixel-perfect collision accuracy
- **Built-in AI Integration** using SF3's cpu_algorithm patterns
- **Multiple Hitbox Types** (attack/body/hand) per frame like SF3
- **Professional Input System** with validation and pattern matching
- **Modern Python Architecture** with type safety and comprehensive testing

**This roadmap transforms our project into:**

### **🏆 The Definitive SF3:3S Experience**
- **Capcom-Level Accuracy**: Using actual SF3 source code algorithms
- **Enhanced Features**: AI, networking, training mode beyond original
- **Modern Architecture**: Type-safe Python with professional practices
- **Community Resource**: Open-source reference for fighting game development
- **Preservation Project**: Keeping SF3:3S alive for future generations

### **🎯 Competitive Advantages**
- **Authentic Mechanics**: Only recreation using official source code
- **AI Integration**: Next-generation opponents with personality preservation
- **Extensible Design**: Easy to add characters, stages, and features
- **Network Ready**: Built for online play and tournaments
- **Educational Value**: Teaching resource for fighting game development

### **🚀 Impact on Fighting Game Community**
- **Tournament Viable**: Frame-perfect accuracy for competitive play
- **Modding Platform**: Extensible architecture for community content
- **Training Tool**: Advanced training mode with frame data display
- **Preservation**: Ensuring SF3:3S remains playable forever
- **Innovation**: Pushing boundaries of what fan projects can achieve

---

*"We're not just recreating SF3:3S - we're creating the DEFINITIVE version that combines Capcom's legendary gameplay with modern technology and AI. This will be the gold standard for fighting game recreations!"* 🥋✨🔥🚀

## 📚 **Key Resources**

### **SF3:3S Decompilation Source Files**
- **Main Repository**: [crowded-street/3s-decomp](https://github.com/crowded-street/3s-decomp)
- **Status**: Game code fully decompiled (740+ commits)

**🔥 Critical Source Files:**
- **[HITCHECK.c](https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/HITCHECK.c)** - Complete collision detection system
  - `hit_check_main_process()` - Main collision loop
  - `attack_hit_check()` - Attack vs defense collision
  - `catch_hit_check()` - Throw/grab mechanics
  - `set_struck_status()` - Hit confirmation and damage
  - `set_caught_status()` - Throw confirmation and positioning

- **[PLMAIN.c](https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/PLMAIN.c)** - Character state management
  - `Player_move()` - Main character update loop
  - `player_mv_0000()` - Character initialization
  - `player_mv_1000()` - Character appearance/intro
  - 8-level routine system (`routine_no[0-7]`)

- **[CMD_MAIN.c](https://github.com/crowded-street/3s-decomp/blob/main/src/anniversary/sf33rd/Source/Game/CMD_MAIN.c)** - Input command detection
  - Input buffer system with pattern matching
  - Motion input detection (QCF, DP, charge moves)
  - Frame-perfect input leniency

**📁 Directory Structure:**
- **[Source/Game/](https://github.com/crowded-street/3s-decomp/tree/main/src/anniversary/sf33rd/Source/Game)** - Main game logic
- **[include/](https://github.com/crowded-street/3s-decomp/tree/main/include)** - Header files and data structures
- **[docs/](https://github.com/crowded-street/3s-decomp/tree/main/docs)** - Build instructions and documentation

**🛠️ Data Structure Headers:**
- **[workuser.h](https://github.com/crowded-street/3s-decomp/blob/main/include/sf33rd/Source/Game/workuser.h)** - WORK and PLW structures
- Character pattern files (PLPAT*.c) - Character-specific move data

### **Frame Data Database**
- **Baston ESN3S**: https://baston.esn3s.com/
  - **Akuma/Gouki**: https://baston.esn3s.com/index.php?id=14
  - **Complete Database**: All SF3:3S characters with frame data
  - **Hitbox Visualizations**: Frame-by-frame collision box display
  - **Move Properties**: Startup, active, recovery, advantage, damage, stun

### **Professional Fighting Game References**
- **Reencor Project**: [Ranguel/Reencor](https://github.com/Ranguel/Reencor)
  - **[main.py](https://github.com/Ranguel/Reencor/blob/main/main.py)** - Game architecture example
  - **[Input_device.py](https://github.com/Ranguel/Reencor/blob/main/Util/Input_device.py)** - Multi-mode input system
  - **[OpenGL_Renderer.py](https://github.com/Ranguel/Reencor/blob/main/Util/OpenGL_Renderer.py)** - Hardware-accelerated rendering
  - **[Game_Screens.py](https://github.com/Ranguel/Reencor/blob/main/Util/Game_Screens.py)** - Screen management system

### **Community Resources**
- **Discord**: Crowded Street server
  - **Channel**: #3s-decomp (dedicated decompilation discussion)
  - **Contributors**: 15+ active contributors
- **Documentation**: 
  - **[Decompiling Guide](https://github.com/crowded-street/3s-decomp/blob/main/docs/decompiling.md)**
  - **[Build Instructions](https://github.com/crowded-street/3s-decomp/tree/main/docs)**
- **Progress Tracking**: [CRI Progress](https://github.com/crowded-street/3s-decomp/blob/main/cri-progress.md)

### **📖 Our Documentation**
- **[SF3 Source Code Navigation Guide](docs/SF3_SOURCE_NAVIGATION_GUIDE.md)** - Complete guide for exploring SF3 source code without C knowledge
  - **For Non-Programmers**: How to read and understand SF3's collision, state, and input systems
  - **Practical Examples**: Step-by-step walkthrough of how a single attack works
  - **Quick Reference**: Direct links to the most important source files
  - **Learning Path**: Priority order for studying different game systems

### **Sprite Resources**
- **JustNoPoint**: Original SF3 sprite source
  - **Akuma Sprites**: Available from justnopoint.com
  - **Effects**: Hit sparks, visual effects
- **Alternative Sources**:
  - **Ryu SF3**: https://www.nowak.ca/zweifuss/all/02_Ryu.zip
  - **Ken SF3**: https://www.nowak.ca/zweifuss/all/11_Ken.zip
  - **Effects**: https://www.justnopoint.com/zweifuss/all/22_Ingame%20Effects.zip