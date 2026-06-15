"""Single source of truth for locating game assets.

All game assets live under one canonical tree at the repo root::

    assets/
      characters/<name>/animations/   one PNG-sequence folder per move
      characters/<name>/sprite_sheets/ numbered sprite sheets (projectiles, fx)
      characters/<name>/raw_gifs/      source gifs the frames were extracted from
      stages/                          stage backgrounds
      vfx/ingame_effects/              hit sparks and other in-game effects
      intro/                           menu / intro art
      sounds/  data/                   audio + misc data

Asset paths are stored repo-relative (e.g. ``"assets/characters/akuma/..."``)
and resolved against ``ASSETS_ROOT`` / the repo root here, so the game loads the
same files no matter the working directory it is launched from.

Ownership: the contents of ``assets/`` are the project owner's licensed/paid
resources. The whole tree is gitignored. Never delete them; migrate by moving.
"""

import os
from pathlib import Path

# src/street_fighter_3rd/util/assets.py -> parents[3] == repo root.
REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETS_ROOT = REPO_ROOT / "assets"


def resolve_asset(path: str) -> str:
    """Make a repo-relative asset path absolute (CWD-independent).

    Absolute paths are returned unchanged.
    """
    return path if os.path.isabs(path) else str(REPO_ROOT / path)


def asset_path(*parts: str) -> str:
    """Absolute path to an asset under ``assets/`` from its sub-parts.

    ``asset_path("characters", "akuma", "animations")`` ->
    ``<repo>/assets/characters/akuma/animations``.
    """
    return str(ASSETS_ROOT.joinpath(*parts))
