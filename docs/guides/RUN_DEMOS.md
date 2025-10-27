# SF3:3S Demo Guide - Characters in Action!

## 🎮 Available Demos (Ready Now!)

### 1. **Sprite Integration Demo** (Recommended First)
```bash
uv run demo_sprite_integration.py
```
**What you'll see:**
- ✅ Authentic Akuma sprites in action
- ✅ 4 demo modes to explore
- ✅ Real SF3 animations cycling
- ✅ Side-by-side sprite vs placeholder comparison

**Controls:**
- `1-4`: Switch demo modes
- `S`: Toggle sprites on/off
- `Left/Right`: Change animations manually
- `Space`: Trigger current animation
- `A`: Toggle auto-cycle
- `D`: Debug info

### 2. **Character Expansion Demo**
```bash
uv run demo_character_expansion.py
```
**What you'll see:**
- ✅ Character selection screen
- ✅ Ken vs Akuma with different properties
- ✅ AI personality differences
- ✅ Character-specific stats

### 3. **Enhanced Features Demo**
```bash
uv run demo_enhanced_sf3.py
```
**What you'll see:**
- ✅ Training mode with frame data
- ✅ Advanced AI in action
- ✅ Visual effects and screen shake
- ✅ Network play simulation

### 4. **Foundation Test** (Technical)
```bash
uv run test_sf3_foundation.py
```
**What you'll see:**
- ✅ Authentic SF3 systems working
- ✅ Hit detection and collision
- ✅ Parry system testing

## 🎯 Best Experience Order:

1. **Start with Sprite Demo** - See authentic visuals
2. **Try Character Expansion** - See Ken vs Akuma
3. **Explore Enhanced Features** - See all systems together

## 🔧 If Sprites Don't Load:

The sprite system will gracefully fall back to colored rectangles if sprites aren't found. To ensure sprites are available:

```bash
# Check if Akuma animations exist
ls tools/sprite_extraction/akuma_animations/

# If missing, run sprite extraction
cd tools/sprite_extraction/
uv run download_akuma_animations.py
```

## 🚀 What You'll Experience:

- **Authentic SF3 Akuma sprites** from the original game
- **Smooth 60fps animations** with proper timing
- **Real fighting game mechanics** underneath
- **Professional-quality visuals** that match SF3:3S

**The characters are ready for action RIGHT NOW!** 🥋✨
