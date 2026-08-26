"""Read-only access to the community tier (Baston-derived damage / stun /
advantage) in data/characters/<char>/sf3_authentic_frame_data.yaml.

The engine's hitboxes/timing come from the ROM repository; the few damage
values that don't flow through a hitbox (throws, projectiles, super-art
reach hits) are read from here so every number has one source
(tools/framedata/baston_to_community.py regenerates the file).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SECTIONS = ("normal_attacks", "special_moves", "super_arts")


@lru_cache(maxsize=None)
def _load(character: str) -> Dict[str, Any]:
    path = _REPO_ROOT / "data" / "characters" / character / "sf3_authentic_frame_data.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def community_move(key: str, character: str = "akuma") -> Optional[Dict[str, Any]]:
    """The community row for a move key (searched across the move sections)."""
    doc = _load(character)
    for section in _SECTIONS:
        move = (doc.get(section) or {}).get(key)
        if isinstance(move, dict):
            return move
    return None


def _engine_scale() -> float:
    """1.0 on the community (1050) scale; vitality/1050 once a ROM combat
    capture sets the life-bar scale (see HitboxRepository.community_scale)."""
    try:
        from street_fighter_3rd.data.hitbox_repository import HitboxRepository
        return HitboxRepository.instance().community_scale()
    except Exception:  # repository unavailable (stub data sets)
        return 1.0


def community_damage(key: str, default: int, character: str = "akuma") -> int:
    """Damage for a move key on the scale the engine runs at, else `default`
    (also rescaled)."""
    move = community_move(key, character)
    if not (move and move.get("damage") is not None):
        return int(default)
    raw = int(move["damage"])
    return max(1, int(round(raw * _engine_scale()))) if raw > 0 else raw
