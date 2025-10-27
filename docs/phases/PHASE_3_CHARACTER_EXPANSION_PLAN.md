# 🥋 Phase 3: Character Expansion Plan

## 🎯 **Objective**
Transform our single-character fighting game into a **multi-character SF3:3S experience** with proper character selection, unique fighting styles, and authentic character-specific mechanics.

---

## 📋 **Phase 3 Overview**

### **Current State**
- ✅ **Akuma fully implemented** - Complete moveset, AI, sprites
- ✅ **Advanced systems working** - Training mode, AI, visual effects
- ✅ **Solid foundation** - Collision, animation, input systems
- ✅ **Ken partially implemented** - Basic character exists in demos

### **Phase 3 Goals**
- 🎯 **Complete Ken implementation** - Full Shoto character with unique properties
- 🎯 **Character selection system** - Professional character select screen
- 🎯 **Character-specific AI** - Different personalities and fighting styles
- 🎯 **Enhanced battle system** - Character vs character with proper balance
- 🎯 **Stage backgrounds** - Authentic SF3 stage visuals

---

## 🏗️ **Implementation Roadmap**

### **Week 1: Ken Character Foundation**

#### **Day 1-2: Ken Data & Animations**
**Files to create/modify:**
- `/src/street_fighter_3rd/characters/ken.py` - Complete Ken implementation
- `/data/characters/ken_animations.yaml` - Ken-specific frame data
- `/data/characters/ken_properties.yaml` - Character stats and properties

**Ken Character Specifications:**
```python
# Ken Properties (Different from Akuma)
ken_stats = {
    "health": 1200,        # Same as Akuma
    "stun": 800,          # Same as Akuma  
    "walk_speed": 1.1,    # Slightly faster than Akuma (1.0)
    "dash_speed": 2.2,    # Faster dash
    "jump_height": 85,    # Higher jump than Akuma (80)
    "archetype": "shoto", # Same fighting style family
    "ai_personality": {
        "aggression": 0.8,     # More aggressive than Akuma (0.6)
        "rushdown": 0.9,       # High rushdown preference
        "zoning": 0.3,         # Low zoning (opposite of Akuma 0.8)
        "combo_focus": 0.7,    # Moderate combo focus
        "risk_taking": 0.8     # High risk tolerance
    }
}
```

**Ken Move Differences:**
- **Hadouken**: Travels faster, less recovery
- **Shoryuken**: Higher damage, more invincibility frames
- **Tatsumaki**: Multi-hit, different trajectory
- **Unique moves**: Overhead kick, step kick variations

#### **Day 3-4: Ken Sprite Integration**
**Tasks:**
- Download Ken sprites from sprite sources
- Integrate with existing sprite system
- Test Ken animations in sprite demo
- Ensure proper sprite fallbacks

**Sprite Sources:**
- Primary: JustNoPoint Ken sprites
- Backup: Community sprite packs
- Fallback: Colored rectangles (already working)

#### **Day 5-7: Ken Combat System**
**Tasks:**
- Implement Ken-specific move properties
- Adjust hitboxes for Ken's moves
- Balance Ken vs Akuma matchup
- Test Ken in enhanced demo

---

### **Week 2: Character Selection System**

#### **Day 1-3: Character Select Screen**
**Files to create:**
- `/src/street_fighter_3rd/screens/character_select.py` - Main selection screen
- `/src/street_fighter_3rd/data/character_roster.py` - Character roster management
- `/assets/portraits/` - Character portrait images

**Character Select Features:**
```python
class CharacterSelectScreen:
    """Professional character selection screen"""
    
    def __init__(self):
        self.characters = [
            {"name": "Akuma", "portrait": "akuma_portrait.png", "available": True},
            {"name": "Ken", "portrait": "ken_portrait.png", "available": True},
            # Future characters can be added here
        ]
        self.player1_selection = None
        self.player2_selection = None
        self.selection_state = "player1_selecting"
    
    def handle_input(self, input_event):
        """Handle character selection input"""
        pass
    
    def render_selection_screen(self, screen):
        """Render character portraits and selection UI"""
        pass
```

#### **Day 4-5: Character Loading System**
**Tasks:**
- Dynamic character loading based on selection
- Character factory pattern implementation
- Memory management for multiple characters
- Integration with existing battle system

#### **Day 6-7: Enhanced Battle Flow**
**Tasks:**
- Character select → Battle → Results → Character select loop
- Proper character initialization based on selection
- Victory/defeat screens with character-specific animations

---

### **Week 3: AI Personalities & Balance**

#### **Day 1-3: Character-Specific AI**
**Files to modify:**
- `/src/street_fighter_3rd/ai/advanced_ai.py` - Add character-specific behaviors
- `/src/street_fighter_3rd/ai/character_ai_profiles.py` - AI personality definitions

**AI Personality System:**
```python
class CharacterAIProfile:
    """Character-specific AI behavior patterns"""
    
    akuma_profile = AIPersonality(
        aggression=0.6,
        defensive_style=0.7,
        zoning_preference=0.8,    # Loves fireballs
        rushdown_preference=0.3,  # Prefers distance
        combo_preference=0.6,
        special_move_usage=0.8,   # Uses specials frequently
        super_usage=0.5,
        reaction_time=4           # 4-frame reactions
    )
    
    ken_profile = AIPersonality(
        aggression=0.8,           # More aggressive
        defensive_style=0.4,      # Less defensive
        zoning_preference=0.3,    # Doesn't like distance
        rushdown_preference=0.9,  # Loves getting in close
        combo_preference=0.7,
        special_move_usage=0.6,
        super_usage=0.7,          # Uses supers more often
        reaction_time=3           # 3-frame reactions (faster)
    )
```

#### **Day 4-5: Character Balance**
**Tasks:**
- Frame data comparison between Ken and Akuma
- Damage scaling adjustments
- Move priority balancing
- Hitbox size optimization

#### **Day 6-7: Advanced AI Behaviors**
**Tasks:**
- Character-specific combo patterns
- Matchup-aware AI decision making
- Adaptive difficulty based on character choice
- AI learning from player patterns

---

### **Week 4: Polish & Stage System**

#### **Day 1-3: Stage Backgrounds**
**Files to create:**
- `/src/street_fighter_3rd/stages/` - Stage system
- `/assets/stages/` - Stage background images
- `/data/stages/stage_data.yaml` - Stage properties

**Stage Implementation:**
```python
class Stage:
    """SF3 stage with authentic backgrounds"""
    
    def __init__(self, stage_name: str):
        self.name = stage_name
        self.background_layers = []  # Parallax scrolling layers
        self.boundaries = {"left": -200, "right": 200}
        self.music_track = f"{stage_name}_theme.ogg"
    
    def render_background(self, screen, camera_x):
        """Render stage background with parallax scrolling"""
        pass
```

**Planned Stages:**
- **Gill's Stage** - Classic SF3 stage
- **Training Stage** - Simple training room
- **Generic Stage** - Fallback stage

#### **Day 4-5: Enhanced Demo Integration**
**Tasks:**
- Update all demos to use character selection
- Add stage selection to enhanced demo
- Integrate new features with existing systems
- Performance optimization for multiple characters

#### **Day 6-7: Final Polish**
**Tasks:**
- Victory quotes and character-specific win animations
- Enhanced visual effects for different characters
- Sound effects for character-specific moves
- Comprehensive testing of all systems

---

## 🎯 **Success Metrics**

### **Technical Goals**
- ✅ **2 fully functional characters** (Akuma + Ken)
- ✅ **Professional character select screen**
- ✅ **Character-specific AI personalities**
- ✅ **Balanced gameplay** between characters
- ✅ **Stage system foundation**

### **User Experience Goals**
- ✅ **Smooth character selection flow**
- ✅ **Distinct character feel** (Ken ≠ Akuma)
- ✅ **Engaging AI opponents** with different styles
- ✅ **Visual polish** matching Phase 2 quality
- ✅ **60fps performance** with multiple characters

### **Code Quality Goals**
- ✅ **Maintainable character system** (easy to add more)
- ✅ **Type-safe character data** with Pydantic validation
- ✅ **Comprehensive testing** of new features
- ✅ **Clean architecture** following established patterns

---

## 🚀 **Phase 3 Deliverables**

### **New Demos**
1. **Character Selection Demo** - Showcase selection screen
2. **Ken vs Akuma Demo** - Two-character battle showcase
3. **AI Personality Demo** - Different AI styles in action
4. **Stage Demo** - Background system showcase

### **Enhanced Existing Demos**
- **Enhanced SF3 Demo** - Now with character selection
- **Character Expansion Demo** - Updated with full Ken implementation
- **Sprite Integration Demo** - Ken sprites integrated

### **New Systems**
- **Character Factory** - Dynamic character loading
- **Selection Screen** - Professional character select
- **Stage System** - Background rendering with parallax
- **AI Profiles** - Character-specific AI behaviors

---

## 🎮 **Post-Phase 3 Vision**

After Phase 3 completion, we'll have:
- **Complete 2-character fighting game** with selection screen
- **Foundation for easy character expansion** (Ryu, Chun-Li, etc.)
- **Professional-quality user experience**
- **Tournament-viable gameplay** with balanced characters
- **Extensible architecture** for future enhancements

**This transforms our project from a tech demo into a real fighting game!** 🥋✨

---

## 📚 **Resources & References**

### **Ken Frame Data**
- **Baston ESN3S Ken Page**: https://baston.esn3s.com/index.php?id=11
- **Ken Move Properties**: Authentic SF3:3S frame data
- **Ken vs Akuma Matchup**: Community knowledge base

### **Sprite Resources**
- **Ken Sprites**: JustNoPoint and community sources
- **Stage Backgrounds**: SF3 stage rips and recreations
- **UI Elements**: Character select screen assets

### **Technical References**
- **Character Factory Pattern**: Clean character instantiation
- **AI Personality Systems**: Fighting game AI best practices
- **Stage Rendering**: Parallax scrolling techniques

---

**Phase 3 will make our SF3 recreation feel like a complete fighting game!** 🔥🚀
