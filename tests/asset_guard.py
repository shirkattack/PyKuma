"""Skip tests that need the (deliberately untracked) Capcom sprite assets.

`assets/*` is gitignored -- only assets/README.md is in the repo -- so a CI
runner never has sprites, input icons, or hit-spark sequences. Tests that
render or load them must skip cleanly there and run for real locally.
"""

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

ANIMATIONS = "assets/characters/akuma/animations"
STANCE = f"{ANIMATIONS}/akuma-stance"
INPUT_ICONS = "assets/ui/inputs"
HITSPARKS = "assets/vfx/ingame_effects/hitsparks"


def have_assets(*rel_dirs: str) -> bool:
    return all(os.path.isdir(REPO_ROOT / d) for d in rel_dirs)


def require_assets(*rel_dirs: str):
    """`pytest.mark.skipif` for tests that need these asset directories."""
    missing = [d for d in rel_dirs if not os.path.isdir(REPO_ROOT / d)]
    return pytest.mark.skipif(bool(missing),
                              reason=f"sprite assets not present (gitignored): {', '.join(missing)}")
