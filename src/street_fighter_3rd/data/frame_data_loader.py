"""
Canonical frame-data loader — the single source of truth for hitbox/hurtbox data.

PRIME DIRECTIVE: we do NOT make up data. Every box lives in
``src/street_fighter_3rd/data/characters/<name>/frames.yaml``, validated through the
Pydantic schema (``schemas.sf3_schemas.CharacterFrames``) at load time so malformed
data is rejected at boot. Every move declares ``provenance`` (verified / unverified /
derived); this module logs a VERIFIED/UNVERIFIED tally on first load so fabricated
placeholders are never silently trusted.

This module is the canonical replacement for the old ``data/akuma_hitboxes.py``. It
exposes drop-in functions (``get_hitboxes`` / ``get_hurtboxes`` / ``get_move_frame_data``)
with the same shapes the collision adapter already consumes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from street_fighter_3rd.data.enums import HitType, HitEffect, CharacterState
from street_fighter_3rd.data.character_dimensions import get_default_hurtbox_for_character
from street_fighter_3rd.schemas.sf3_schemas import (
    CharacterFrames,
    Provenance,
    load_character_frames,
)
from street_fighter_3rd.util.logging_config import get_logger

log = get_logger(__name__)

# frames.yaml ships inside the package data dir, next to animations.yaml.
_CHARACTERS_DIR = Path(__file__).resolve().parent / "characters"


# --- runtime carriers (mirror the old akuma_hitboxes dataclasses exactly) ----

@dataclass
class RuntimeHitbox:
    """Active offensive box for one frame (same attributes the adapter expects)."""
    offset_x: int
    offset_y: int
    width: int
    height: int
    damage: int
    hitstun: int
    blockstun: int
    hit_type: HitType = HitType.MID


@dataclass
class RuntimeHurtbox:
    """Vulnerable box."""
    offset_x: int
    offset_y: int
    width: int
    height: int


@dataclass
class RuntimeMove:
    """A move resolved into runtime objects, keyed by CharacterState."""
    name: str
    state: CharacterState
    startup: int
    active: List[int]
    recovery: int
    on_hit: int
    on_block: int
    # (active_frames, hitbox) tuples — matches the legacy MoveFrameData.hitboxes shape.
    hitboxes: List[Tuple[List[int], RuntimeHitbox]]
    hurtboxes: List[RuntimeHurtbox]
    hit_effect: HitEffect
    provenance: Provenance


_RAW_CACHE: Dict[str, CharacterFrames] = {}
_RUNTIME_CACHE: Dict[str, Dict[CharacterState, RuntimeMove]] = {}


def _frames_path(character: str) -> Path:
    return _CHARACTERS_DIR / character / "frames.yaml"


def _log_provenance(character: str, data: CharacterFrames) -> None:
    verified, unverified = [], []
    for key, move in data.moves.items():
        (verified if move.provenance.status == "verified" else unverified).append(key)
    total = len(data.moves)
    if unverified:
        log.warning(
            "%s frame data: %d/%d VERIFIED — UNVERIFIED (placeholder, do not trust): %s",
            character, len(verified), total, sorted(unverified),
        )
    else:
        log.info("%s frame data: %d/%d VERIFIED — all moves verified", character, len(verified), total)


def get_character_frames(character: str = "akuma") -> CharacterFrames:
    """Return the validated frames.yaml for a character (cached; logs tally on first load)."""
    if character not in _RAW_CACHE:
        data = load_character_frames(_frames_path(character))
        _RAW_CACHE[character] = data
        _log_provenance(character, data)
    return _RAW_CACHE[character]


def _build_runtime(data: CharacterFrames) -> Dict[CharacterState, RuntimeMove]:
    by_state: Dict[CharacterState, RuntimeMove] = {}
    for move in data.moves.values():
        state = CharacterState[move.state]
        hitboxes: List[Tuple[List[int], RuntimeHitbox]] = []
        for group in move.hitboxes:
            for box in group.boxes:
                hitboxes.append((
                    group.frames,
                    RuntimeHitbox(
                        offset_x=box.offset_x, offset_y=box.offset_y,
                        width=box.width, height=box.height,
                        damage=box.damage, hitstun=box.hitstun, blockstun=box.blockstun,
                        hit_type=HitType[box.hit_type],
                    ),
                ))
        hurtboxes = [
            RuntimeHurtbox(h.offset_x, h.offset_y, h.width, h.height)
            for h in move.hurtboxes
        ]
        by_state[state] = RuntimeMove(
            name=move.name, state=state,
            startup=move.startup, active=move.active, recovery=move.recovery,
            on_hit=move.on_hit, on_block=move.on_block,
            hitboxes=hitboxes, hurtboxes=hurtboxes,
            hit_effect=HitEffect[move.hit_effect], provenance=move.provenance,
        )
    return by_state


def _runtime(character: str = "akuma") -> Dict[CharacterState, RuntimeMove]:
    if character not in _RUNTIME_CACHE:
        _RUNTIME_CACHE[character] = _build_runtime(get_character_frames(character))
    return _RUNTIME_CACHE[character]


# --- public API (drop-in for the old data/akuma_hitboxes.py functions) -------

def get_hitboxes(state: CharacterState, frame_number: int, character: str = "akuma") -> List[RuntimeHitbox]:
    """Active offensive boxes for a state on a given 1-indexed frame."""
    move = _runtime(character).get(state)
    if not move:
        return []
    return [hb for active_frames, hb in move.hitboxes if frame_number in active_frames]


def get_hurtboxes(state: CharacterState, character: str = "akuma") -> List[RuntimeHurtbox]:
    """Vulnerable boxes for a state, falling back to the character's default hurtbox."""
    move = _runtime(character).get(state)
    if move and move.hurtboxes:
        return move.hurtboxes
    is_crouching = state == CharacterState.CROUCHING
    ox, oy, w, h = get_default_hurtbox_for_character(character, is_crouching)
    return [RuntimeHurtbox(ox, oy, w, h)]


def get_move_frame_data(state: Optional[CharacterState], character: str = "akuma") -> Optional[RuntimeMove]:
    """Complete runtime move data for a state, or None."""
    if state is None:
        return None
    return _runtime(character).get(state)
