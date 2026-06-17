# PyKuma

<div align="center">

![Demo](./public/demo.gif)

**From frame data to fireballs — a love letter to 3rd Strike's mechanics, written in pure Python.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Pygame 2.6+](https://img.shields.io/badge/pygame-2.6+-green.svg)](https://www.pygame.org/)
[![Pydantic 2.5+](https://img.shields.io/badge/pydantic-2.5+-E92063.svg)](https://docs.pydantic.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[Features](#-features) • [Quick Start](#-quick-start) • [Controls](#-controls) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 🎮 About

**PyKuma** (Python + Akuma) is a faithful recreation of **Street Fighter III: 3rd Strike**, built from scratch in Python to demonstrate professional game engine architecture and fighting game mechanics. It showcases:

- **60 FPS frame-perfect gameplay** with professional input buffering
- **State machine architecture** for character behavior management
- **Frame-accurate collision detection** with hitbox/hurtbox systems
- **YAML-driven animation system** for data-driven game design
- **Complete fighting game systems**: hitstop, hitstun, blockstun, projectiles, special moves

This is a **non-commercial educational project** created to study fighting game mechanics and game engine design.

## 📌 Current Status / Known Gaps

The features below describe what's implemented; here's an honest snapshot of
what is and isn't playable at HEAD:

- ✅ **Akuma vs Akuma** is the playable matchup — both players are Akuma.
  `characters/ken.py` exists but is **experimental and not wired in** (no
  character select in the live game yet).
- ✅ **Parry is live**: tap forward (or down-forward for low) within the
  authentic 7-frame window to parry. Guard-direction nuances and red parry
  are still simplified.
- ⚠️ **Sprites are not bundled.** SF3 sprite art is Capcom's copyright and
  can't be redistributed; without local assets the game runs with placeholder
  rectangles. The sprite-extraction tooling in `tools/` is a personal-use path.
- ❌ **No charge motions, no negative edge** — deliberate omissions for now.
- ❌ No corner-pressure pushback on the attacker, no projectile-vs-projectile
  resolution yet.
- 🧭 See `ARCHITECTURE.md` for which module is canonical for each concern;
  superseded parallel implementations live in `attic/`.

## ✨ Features

### Core Fighting Game Mechanics
- ✅ **60 FPS Locked Gameplay** - Deterministic fixed-timestep (no RNG)
- ✅ **Frame-Perfect Input System** - 60-frame buffer with lenient motion detection
  (QCF, QCB, DP, RDP, double-QCF/QCB, PPP/KKK, command sequences)
- ✅ **State Machine Architecture** - Clean character state management
- ✅ **Hit/Hurtbox Collision System** - ROM-accurate hitbox geometry
- ✅ **Hit Freeze (Hitstop)** & **Hitstun/Blockstun** - frame-advantage feedback
- ✅ **Combo system** - hit-chain detection (a combo is a hitstun chain, not a timer)
  with damage scaling; juggle counter that ends infinite juggles
- ✅ **Projectile System** - Gou Hadouken (ground + air) that deals damage on contact
- ✅ **Throws, Parry, Invincibility** - LP+LK throws; 7-frame parry; i-frames honored
- ✅ **Super-Meter & Super Arts** - meter builds on hits/blocks; SA1/SA2/SA3
- ✅ **Diagnostic framework** - deterministic replays, scenario tests, ROM-golden compare

### Akuma Character
**Movement:** standing, walking, dashing (fwd/back, stops at pushbox contact),
3 jumps (neutral/fwd/back), crouching.

**Normals (18):** 6 standing, 6 crouching, 6 jumping (LP/MP/HP/LK/MK/HK each).

**Command actions:** Throw (LP+LK, fwd/back), Universal Overhead / UOH (MP+MK),
Taunt (HP+HK).

**Special Moves:**
- **Gohadoken** (fireball): QCF+P — 3 speeds; air version (Zanku Hadou) QCF+P while jumping
- **Goshoryuken** (dragon punch): DP+P
- **Tatsumaki Zankukyaku** (hurricane kick): QCB+K
- **Ashura Senku** (teleport): 623/421 + PPP or KKK — strike-invulnerable reposition
- **Hyakkishū** (demon flip): QCF+K — arcing approach (followups TBD)

**Super Arts** (cost a full meter):
- **SA1 Messatsu Gou Hadou**: 236236+P (multi-hit super fireball)
- **SA2 Messatsu Gou Shoryu**: 236236+K (launcher)
- **SA3 Kongou Kokuretsu Zan**: 214214+P (heavy hit)
- **Shun Goku Satsu** (Raging Demon): LP, LP, →, LK, HP — unblockable command grab

> Damage/timing for several specials & supers are **provisional game-feel values**,
> flagged in code pending ROM/decomp calibration — geometry remains ROM-accurate.

### Game Modes
- **Normal Mode** - Standard match **vs a deterministic CPU opponent**
- **Training Mode** - Hitbox/frame-data/input overlays, idle health regen, no timer
- **Development Mode** - Full debug suite with performance metrics
- **Versus Mode** - Local 2-player battles
- **Hitbox Viewer** - ROM-accurate hitbox/hurtbox inspector (`--hitbox-viewer`)

### Technical Features
- ✅ **UV Package Manager** - Modern Python dependency management
- ✅ **Pydantic Data Validation** - Type-safe schemas with runtime validation
- ✅ **Modular Architecture** - Separated systems (Input, Collision, Animation, VFX)
- ✅ **2-Player Support** - Keyboard controls for both players
- ✅ **Controller Support** - Joystick/hitbox support
- ✅ **Main Menu System** - Full navigation with mode selection
- ✅ **YAML-Based Animation System** - Centralized frame data and hitbox definitions
- ✅ **Debug Tools** - Hitbox visualization, frame data display, performance metrics

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- [UV package manager](https://github.com/astral-sh/uv)

### Installation

1. **Install UV** (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Clone the repository:**
```bash
git clone git@github.com:shirkattack/PyKuma.git
cd pykuma
```

3. **Install dependencies:**
```bash
uv sync
```

4. **Run the game** (entry points are defined in `pyproject.toml`):
```bash
uv run sf3            # main menu (recommended)
uv run sf3-menu       # same, explicit
uv run sf3-training   # training mode directly (overlays + regen)
uv run sf3-dev        # dev mode (full debug suite)

# Standalone ROM-accurate hitbox inspector:
uv run python src/street_fighter_3rd/main_with_menu.py --hitbox-viewer --no-menu
```

## 🕹️ Controls

Directions are written facing-relative (→ = toward the opponent). `P` = any
punch, `K` = any kick, `PPP` = all three punches, `KKK` = all three kicks.

### Keyboard layout

| | Directions | Punches (LP/MP/HP) | Kicks (LK/MK/HK) |
|---|---|---|---|
| **Player 1** | `W` up · `S` down · `A/D` back/fwd | `J` `K` `L` | `U` `I` `O` |
| **Player 2** | Arrow keys | NumPad `1` `2` `3` | NumPad `4` `5` `6` |

Double-tap → or ← to dash. Hold ← (away) to block while being attacked.

### Akuma command list (facing right)

| Move | Input |
|---|---|
| Dash forward / back | →→ / ←← |
| Throw (fwd / back) | LP+LK (hold ← for back throw) |
| Universal Overhead (UOH) | MP+MK |
| Taunt | HP+HK |
| Gohadoken (fireball) | ↓↘→ + P  *(QCF+P; air = Zanku Hadou)* |
| Goshoryuken (DP) | →↓↘ + P |
| Tatsumaki (hurricane) | ↓↙← + K |
| Ashura Senku (teleport fwd / back) | →↓↘ + PPP/KKK  /  ←↓↙ + PPP/KKK |
| Hyakkishū (demon flip) | ↓↘→ + K |
| **SA1** Messatsu Gou Hadou | ↓↘→↓↘→ + P  *(full meter)* |
| **SA2** Messatsu Gou Shoryu | ↓↘→↓↘→ + K  *(full meter)* |
| **SA3** Kongou Kokuretsu Zan | ↓↙←↓↙← + P  *(full meter)* |
| **Raging Demon** (Shun Goku Satsu) | LP, LP, →, LK, HP  *(full meter)* |
| Parry (high / low) | tap → / tap ↓ as the hit lands (7-frame window) |

### Training / debug hotkeys
- **F1** hitbox/hurtbox display · **F2** frame-data overlay · **F3** reset positions
- **R** reset health · **F10** issue report · **F11** save replay clip · **F12** snapshot
- **ESC** pause / return to menu

## 📁 Project Structure

```
pykuma/
├── src/street_fighter_3rd/     # Main engine code
│   ├── core/                   # Game loop, modes, menu, projectiles
│   ├── characters/             # Character implementations
│   ├── systems/                # Input, collision, animation, VFX
│   └── data/                   # Enums, constants, frame data
├── assets/                     # Sprites, stages, VFX
├── scripts/                    # Demo scripts and dev tools
├── tests/                      # Pytest test suite
├── docs/                       # Documentation
│   ├── ROADMAP.md             # Development roadmap
│   ├── TESTING_GUIDE.md       # Testing philosophy
│   
└── tools/                      # Sprite extraction utilities
```

## 🔬 Why Pydantic for Fighting Games?

Fighting games have **complex, interconnected data** that must be validated at runtime to prevent bugs. This project uses [Pydantic](https://docs.pydantic.dev/) for type-safe data validation throughout the engine.

### The Challenge

A single character in a fighting game has:
- **18+ normal attacks**, each with unique frame data (startup, active, recovery)
- **Multiple hitboxes per move** (attack hitboxes, body hurtboxes, hand hurtboxes)
- **Frame-accurate timing** - a single frame error breaks gameplay at 60 FPS
- **Hundreds of numeric values** - damage, stun, pushback, advantage frames, invincibility frames
- **Complex relationships** - total frames must equal startup + active + recovery
- **SF3 authenticity requirements** - parry window must be exactly 7 frames, damage scaling must match arcade values

### The Solution: Pydantic Schemas

**Before Pydantic** (error-prone):
```python
# Easy to make mistakes - no validation
akuma_punch = {
    "startup": 5,
    "active": 3,
    "recovery": 10,
    "total": 17  # BUG! Should be 18
}
```

**With Pydantic** (validated):
```python
from pydantic import BaseModel, field_validator

class FrameData(BaseModel):
    startup: int
    active: int
    recovery: int
    total: int

    @field_validator('total')
    def validate_total(cls, v, info):
        expected = info.data['startup'] + info.data['active'] + info.data['recovery']
        if v != expected:
            raise ValueError(f"Total {v} must equal {expected}")
        return v

# This catches bugs immediately:
akuma_punch = FrameData(startup=5, active=3, recovery=10, total=17)
# ❌ ValidationError: Total 17 must equal 18
```

### Real Benefits

**1. Catch Bugs Early**
- Detects invalid frame data before it causes gameplay bugs
- Validates hitbox dimensions are positive numbers
- Ensures invincibility frames are within move duration

**2. SF3 Authenticity**
```python
@field_validator('parry')
def validate_parry_config(cls, v):
    if v.get('window_frames') != 7:  # SF3 authentic value
        raise ValueError("Parry window must be 7 frames")
    return v
```

**3. Type Safety**
- IDEs provide autocomplete for all character data
- Refactoring is safe - type errors caught immediately
- Self-documenting code with field descriptions

**4. YAML Integration**
```python
# Load character data from YAML with full validation
character = CharacterData.parse_file("akuma.yaml")
# All hitboxes, frame data, and moves validated on load!
```

### Project Examples

**Character Schemas** (`src/street_fighter_3rd/schemas/sf3_schemas.py`):
- `HitboxData` - Validates hitbox dimensions, damage values, hit properties
- `FrameData` - Validates frame timing with SF3 authenticity checks
- `MoveData` - Complete move definitions with nested validation
- `CharacterData` - Full character with 18+ normals, specials, and stats

**Key Features:**
- **Runtime validation** - Catches errors when loading YAML data
- **Nested schemas** - MoveData contains FrameData which contains HitboxData
- **Custom validators** - Enforces SF3 authentic values (parry window, damage scaling)
- **AI metadata** - Utility scores and risk levels for AI decision-making

This approach makes the engine **robust, maintainable, and faithful to SF3's frame-perfect gameplay**.

## 📚 Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute to the project
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** - Community guidelines
- **[docs/ROADMAP.md](docs/ROADMAP.md)** - Development phases and milestones
- **[docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** - Testing approach and philosophy

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/street_fighter_3rd

# Run specific test
uv run pytest tests/test_collision_detection.py
```

See [tests/README.md](tests/README.md) for more details.

## 🎨 Demo Scripts

The `scripts/` directory contains various demos and developer tools:

```bash
# Full game with sprites
uv run python scripts/demo_main_game_sprites.py

# Minimal fighting demo
uv run python scripts/demo_simple_fighting.py

# Enhanced SF3 demo with parry
uv run python scripts/demo_enhanced_sf3.py

# Hitbox debugging tool
uv run python scripts/debug_hitbox.py
```

See [scripts/README.md](scripts/README.md) for full list.

## 🤝 Contributing

Contributions are welcome! This project is designed to be educational and collaborative.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Setup instructions
- Code guidelines (60 FPS requirement, PEP 8, testing)
- How to submit bug reports and feature requests
- Commit message conventions

**Quick contribution workflow:**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and test thoroughly
4. Commit with conventional commit messages
5. Push and open a Pull Request

See [.github/ISSUE_TEMPLATE/](.github/ISSUE_TEMPLATE/) for issue templates.

## 🎯 Roadmap

### ✅ Phase 1: Core Engine (COMPLETE)
- 60 FPS game loop, state machine, animation system
- Input buffer with motion detection
- Collision system with hitboxes/hurtboxes
- Main menu and multiple game modes

### ✅ Phase 2: Combat Expansion (COMPLETE)
- Full Akuma moveset: 18 normals, throws, overhead, taunt
- Specials: Gohadoken (+ air), Goshoryuken, Tatsumaki, teleport, demon flip
- Projectiles that deal damage; juggle limiting; HUD (icon input display, frame-data panel)

### ✅ Phase 3: SF3 Systems (COMPLETE)
- Parry system (7-frame window)
- Super meter + Super Arts SA1/SA2/SA3
- Raging Demon command grab
- Round-flow poses (intro / win / time-over)

### 🚧 Phase 4: Single-player & polish (IN PROGRESS)
- ✅ **CPU AI opponent** — deterministic; approaches, pokes, blocks, anti-airs,
  throws, and fireballs (Normal/Demo modes)
- Character select + a 2nd character (Ken's class already exists, unwired)
- Calibration pass: ROM/decomp-source the provisional damage/knockback/hitstun values
- Cheap gaps: give UOH real damage, wire the chip-death KO pose
- Sound & music

See [docs/ROADMAP.md](docs/ROADMAP.md) for detailed milestones.

## 🎓 Learning Resources

**Fighting Game Development:**
- [Fighting Game Glossary](https://glossary.infil.net/) - Essential FGC terminology
- [Core-A Gaming](https://www.youtube.com/channel/UCT7njg__VOy3n-SvXemDHvg) - Fighting game analysis

**SF3:3S Specific:**
- [SuperCombo Wiki](https://wiki.supercombo.gg/w/Street_Fighter_3:_3rd_Strike) - Frame data
- [Evo Moment 37](https://www.youtube.com/watch?v=JzS96auqau0) - The legendary Daigo parry

## 🎨 Asset Credits

**Sprite Assets:**
All Akuma sprites sourced from [JustNoPoint's SF3 Archive](https://www.justnopoint.com/zweifuss/akuma/akuma.htm). Huge thanks for preserving these incredible sprite rips.

**Original Game:**
Street Fighter III: 3rd Strike © **Capcom Co., Ltd.** All rights reserved.

**Stage Backgrounds:**
Stage assets from fightersgeneration.com archives.

## ⚖️ Legal

**MIT License** - See [LICENSE](LICENSE) for code licensing.

**IMPORTANT:** This is a **non-commercial educational fan project**. All Street Fighter characters, names, and assets are © Capcom Co., Ltd. This project is not affiliated with, endorsed by, or connected to Capcom.

**Asset Ownership:**
- Game code: MIT License (see LICENSE file)
- Sprites, stages, sound: © Capcom Co., Ltd.
- This project uses these assets under fair use for educational purposes only

**Do not use this project for commercial purposes.** If you're creating a commercial fighting game, create your own original assets or license official content.

## 🙏 Acknowledgments

- **Capcom** - For creating Street Fighter III: 3rd Strike
- **JustNoPoint** - For the incredible sprite archives
- **The FGC** - For keeping the legacy alive for 25+ years
- **Daigo Umehara** - For Evo Moment 37, the most hype moment in FGC history

---

<div align="center">

**"Let's fight like gentlemen."** - Dudley

**PyKuma** - Made with ↓↘→👊 by fighting game fans for fighting game fans

[Report Bug](https://github.com/shirkattack/pykuma/issues/new?template=bug_report.md) • [Request Feature](https://github.com/shirkattack/pykuma/issues/new?template=feature_request.md)

</div>
