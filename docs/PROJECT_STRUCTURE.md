# Project Structure

This document describes the organization of the Street Fighter III: 3rd Strike Python Edition project.

## Directory Layout

```
street_fighter/
├── src/street_fighter_3rd/        # Main source code
│   ├── core/                       # Core game systems
│   │   └── game.py                 # Main game loop and state management
│   ├── characters/                 # Character implementations
│   │   ├── character.py            # Base character class
│   │   └── akuma.py                # Akuma character
│   ├── systems/                    # Game systems
│   │   ├── input_system.py         # Input handling and motion detection
│   │   ├── collision.py            # Hitbox/hurtbox collision detection
│   │   ├── animation.py            # Sprite animation system
│   │   └── vfx.py                  # Visual effects (hit sparks, etc.)
│   └── data/                       # Data definitions
│       ├── enums.py                # Game enumerations (states, inputs, etc.)
│       ├── constants.py            # Game constants and tuning parameters
│       └── frame_data.py           # Character frame data
│
├── assets/                         # Game assets
│   ├── sprites/                    # Character sprites
│   │   └── akuma/
│   │       ├── sprite_sheets/      # Individual PNG sprites (18273-18439)
│   │       └── raw_gifs/           # Source GIF animations
│   ├── stages/                     # Stage backgrounds
│   │   └── ryu-stage.gif           # Ryu's Japanese castle stage
│   └── vfx/                        # Visual effects assets
│       └── ingame_effects/
│           └── hitsparks/          # Hit spark sprite PNGs (29361+)
│
├── tools/                          # Development tools
│   └── sprite_extraction/          # Scripts for extracting sprites from GIFs
│       ├── analyze_frames.py       # Analyze GIF frame counts
│       ├── extract_gif_to_pngs.py  # Extract GIF frames to PNGs
│       └── fix_sprite_flip.py      # Flip sprites horizontally
│
├── docs/                           # Documentation
│   ├── ANIMATION_REFERENCE.md      # Animation sprite mappings
│   ├── SPRITE_RESEARCH.md          # Sprite extraction research notes
│   ├── LIGHT_PUNCH_MAPPING.md      # Light punch frame mapping
│   └── PROJECT_STRUCTURE.md        # This file
│
├── main.py                         # Entry point
├── README.md                       # Project README
├── akuma-stance.gif                # Akuma stance animation (for README)
├── pyproject.toml                  # UV project configuration
├── uv.lock                         # UV lock file
├── .gitignore                      # Git ignore rules
├── .python-version                 # Python version specification
└── requirements.txt                # Empty (using UV)
```

## File Organization Principles

### Source Code (`src/street_fighter_3rd/`)
All game logic lives here, organized by system:
- **core**: High-level game management
- **characters**: Character-specific implementations
- **systems**: Reusable game systems (input, collision, animation, VFX)
- **data**: Data definitions, constants, enumerations

### Assets (`assets/`)
All game assets organized by type:
- **sprites**: Character sprite sheets and source files
- **stages**: Stage background images
- **vfx**: Visual effects (hit sparks, etc.)

Each asset type is further organized by character/category.

### Tools (`tools/`)
Development and build tools that aren't part of the game:
- **sprite_extraction**: Scripts for processing sprite GIFs into individual PNGs

### Documentation (`docs/`)
Technical documentation, research notes, and reference materials.

## Asset Paths in Code

### Character Sprites
```python
# Akuma character (akuma.py)
sprite_directory = "assets/sprites/akuma/sprite_sheets"
```

### Stage Backgrounds
```python
# Main game (game.py)
self.stage_background = pygame.image.load("assets/stages/ryu-stage.gif")
```

### Visual Effects
```python
# VFX system (vfx.py)
effects_dir = "assets/vfx/ingame_effects/hitsparks"
```

## Adding New Assets

### New Character
1. Create `assets/sprites/character_name/sprite_sheets/`
2. Place individual sprite PNGs (numbered sequentially)
3. Optionally: Store source GIFs in `assets/sprites/character_name/raw_gifs/`
4. Create character class in `src/street_fighter_3rd/characters/`
5. Update sprite_directory path in character `__init__`

### New Stage
1. Place stage image in `assets/stages/`
2. Update `game.py` to load the new stage

### New VFX
1. Place effect sprites in appropriate `assets/vfx/` subdirectory
2. Update `vfx.py` to reference new effect sprites

## Cleanup History

This structure was established to organize the growing codebase. Previous structure had:
- Sprite directories (`14_Akuma`, `22_Ingame effects`) in project root
- Temporary extraction scripts scattered in root
- Downloaded GIF files in root
- Documentation mixed with code

All files have been reorganized into logical directories while maintaining working paths in code.
