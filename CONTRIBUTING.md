# Contributing to Street Fighter III: 3rd Strike Engine

Thank you for your interest in contributing! This is an educational, open-source fighting game engine inspired by Street Fighter III: 3rd Strike.

## Getting Started

### Prerequisites
- Python 3.11+
- [UV package manager](https://github.com/astral-sh/uv)
- Pygame 2.6+

### Setup
```bash
# Clone the repo
git clone https://github.com/yourusername/street_fighter.git
cd street_fighter

# Install dependencies with UV
uv sync

# Run the game
uv run sf3

# Run tests
uv run pytest
```

## How to Contribute

### Reporting Bugs
Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md) to report issues.

Include:
- OS and Python version
- Steps to reproduce
- Expected vs actual behavior
- Screenshots or GIFs if applicable

### Suggesting Features
Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md).

Focus on:
- **Game mechanics** (parry system, super arts, etc.)
- **Engine improvements** (better collision, animation system)
- **Developer experience** (better tooling, documentation)

### Pull Requests

#### Code Guidelines
- Follow PEP 8 style
- Add docstrings to public functions
- Keep frame rate at 60 FPS (fighting games are timing-critical!)
- Write tests for new collision/hitbox logic
- Update `docs/ROADMAP.md` if completing a milestone

#### Commit Messages
```
feat: Add Ken character with Shoryuken
fix: Correct hitbox timing on Akuma cr.MK
docs: Update frame data for Goshoryuken
test: Add integration test for parry system
```

#### Before Submitting
1. Run tests: `uv run pytest`
2. Check that the game still runs: `uv run sf3`
3. Update relevant documentation in `docs/`

## Project Structure

```
src/street_fighter_3rd/     # Core engine code
  ├── core/                  # Game loop, modes
  ├── characters/            # Character implementations
  ├── systems/               # Input, collision, animation
  └── data/                  # Frame data, constants

scripts/                     # Demo scripts
docs/                        # Technical documentation
tests/                       # Test suite
tools/                       # Asset extraction tools
```

## Areas That Need Help

See [ROADMAP.md](docs/ROADMAP.md) for current priorities:
- **Character expansion**: Ryu, Ken, Chun-Li implementations
- **Advanced mechanics**: EX moves, super arts, guard break
- **Animation system**: More robust sprite handling
- **Training mode**: Frame data display, replay recording

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful and constructive.

## Legal / IP Notice

**All code in this repository is MIT licensed.**

**Character names, sprites, animations, and likenesses are property of Capcom Co., Ltd.** This is a non-commercial fan project for educational purposes. Sprites are sourced from community archives (JustNoPoint, Zweifuss). Do not use this project for commercial purposes without replacing all Capcom-owned assets with original art.

If you want to ship a game using this engine, replace all SF3 assets with your own characters and art.

## Questions?

Open a [GitHub Discussion](../../discussions) or check out:
- `docs/TECHNICAL_NOTES.md` for engine architecture
- `docs/ROADMAP.md` for development priorities
- `scripts/README.md` for quick demos

---

Happy coding! 🥊
