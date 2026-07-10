"""Bug ticket schema — the rigid hand-off format between a human observation
("the HP does too much damage") and an AI fix (a specific field in a specific
file).

A ticket is one dimensioned claim about one move on one channel:

    move=HEAVY_PUNCH  channel=damage  observed=200  expected=180 (community)

Tickets are emitted by the Frame Lab (F9 in-game) into ``bugs/`` as YAML, the
human optionally adds a free-text ``complaint``, and an AI assistant (e.g.
Claude Code) consumes them. ``fix_hints`` route the assistant to the files
where each channel's value actually lives, including the provenance rules
(ROM-verified timing must never be hand-edited — if measured timing disagrees
with declared timing, the ENGINE is wrong, not the data).

Everything is Pydantic-validated so a malformed ticket fails loudly at write
time, matching the house rule that data errors surface at load, not mid-match.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import yaml
from pydantic import BaseModel, Field

SCHEMA_VERSION = 1

# One channel = one adjustable dimension of a move. "observation" is the
# catch-all for "something felt wrong but the diff engine found no numeric
# mismatch" — the human fills in `complaint` and the assistant investigates.
Channel = Literal[
    "startup", "active", "recovery", "total",
    "damage", "hitstun", "blockstun", "hitstop",
    "advantage_on_hit", "advantage_on_block",
    # sprite channels (phase 2): the visible motion vs the mechanical truth
    "sprite_mapping",   # wrong animation playing for the state
    "sprite_timing",    # animation length disagrees with the move's frames
    "sprite_sync",      # cels misaligned with the startup/active/recovery windows
    "sprite_fallback",  # placeholder rectangle drawn (missing art)
    "data_drift",       # stale duplicated data (animations.yaml vs ROM repo)
    "observation",
]

Scalar = Union[int, float, str, None]

# Channel -> where the value lives + the provenance ground rules. These hints
# are written into every ticket so the consuming assistant starts at the right
# file instead of grepping the repo cold.
FIX_HINTS: Dict[str, List[str]] = {
    "_timing": [
        "Timing (startup/active/recovery/total) is ROM-verified. If MEASURED "
        "timing != DECLARED timing, the ENGINE is wrong, not the data.",
        "Check: src/street_fighter_3rd/characters/character.py "
        "(_get_max_state_frames, state machine transitions).",
        "Check: src/street_fighter_3rd/systems/sf3_collision_adapter.py "
        "(_get_character_hitboxes frame indexing — state_frame+1 convention).",
        "data/characters/akuma/hitboxes.yaml is GENERATED. Never hand-edit; "
        "regenerate via tools/framedata/convert_3rd_training.py.",
    ],
    "_combat": [
        "Damage/hitstun/blockstun are community-tier (NOT ROM-verified).",
        "Declared values: data/characters/akuma/sf3_authentic_frame_data.yaml "
        "(copied into hitboxes.yaml at conversion time).",
        "Applied values: src/street_fighter_3rd/systems/sf3_collision_adapter.py "
        "(_apply_hit_to_character, _apply_block_effects). NOTE: blockstun is "
        "currently DERIVED as max(4, hitstun // 2) and does not read the "
        "declared blockstun — a known modelling gap.",
        "Scaling: src/street_fighter_3rd/systems/sf3_combo_system.py "
        "(compare raw_damage vs scaled_damage in the ticket before blaming data).",
    ],
    "hitstop": [
        "Hitstop has no ROM-declared value; the design formula is "
        "min(HITSTOP_MAX, HITSTOP_BASE + scaled_damage // HITSTOP_PER) in "
        "src/street_fighter_3rd/systems/sf3_collision_adapter.py.",
        "If observed != formula, the engine double-applied or skipped freeze. "
        "If the formula itself 'feels wrong', tune the three constants.",
    ],
    "_advantage": [
        "Frame advantage is EMERGENT (defender_free_frame - attacker_free_frame); "
        "there is no single advantage field to edit.",
        "If measured advantage != community expectation, first check the "
        "hitstun/blockstun applied (combat tier), then the attacker's recovery "
        "(timing tier). Fix the inputs, never fudge the output.",
    ],
    "_sprite": [
        "Sprite channels concern the VISIBLE track, not the mechanics. The "
        "mechanical timing (ROM) is the ruler; the animation must be fitted "
        "to it, never the other way around.",
        "State -> animation mapping: characters/akuma.py (_STATE_ANIM and the "
        "state-transition handler around it).",
        "Animation definitions (sprite lists + frame_duration): "
        "src/street_fighter_3rd/data/animations.yaml. An attack animation's "
        "game-frame length (n_sprites x frame_duration, or per-cel durations) "
        "should equal the move's ROM total so cels neither cut off nor freeze "
        "on the last pose mid-move.",
        "Playback engine: src/street_fighter_3rd/systems/animation.py "
        "(Animation/FolderAnimation.update, AnimationController).",
        "Use the ticket's repro.cel_timeline: it aligns cel changes against "
        "the measured phase per frame — the desync is visible as rows where "
        "the cel is wrong for the phase.",
        "sprite_fallback means a placeholder rectangle was drawn: sprites are "
        "not bundled (Capcom copyright); local assets come from the "
        "tools/sprite_extraction personal-use path. Missing files, not code, "
        "unless the path/mapping is wrong.",
    ],
    "data_drift": [
        "animations.yaml embeds frame_data/hitbox blocks that PREDATE the "
        "ROM-verified repository and have drifted from it. The ROM repo "
        "(data/characters/akuma/hitboxes.yaml via hitbox_repository) is "
        "canonical for timing and geometry; ARCHITECTURE.md says so.",
        "Preferred fix: delete the stale embedded block (or regenerate it "
        "from the repository) and make sure no live code reads it. Grep for "
        "readers before deleting; animations.yaml should carry sprite/timing "
        "presentation data only.",
    ],
    "observation": [
        "No numeric mismatch was detected; use `complaint` + `measured_summary` "
        "+ `repro.phase_timeline` (and `repro.cel_timeline` for sprite issues) "
        "to locate the issue.",
    ],
}


def hints_for(channel: str) -> List[str]:
    if channel in ("startup", "active", "recovery", "total"):
        return FIX_HINTS["_timing"]
    if channel in ("damage", "hitstun", "blockstun"):
        return FIX_HINTS["_combat"]
    if channel in ("advantage_on_hit", "advantage_on_block"):
        return FIX_HINTS["_advantage"]
    if channel in ("sprite_mapping", "sprite_timing", "sprite_sync", "sprite_fallback"):
        return FIX_HINTS["_sprite"]
    return FIX_HINTS.get(channel, FIX_HINTS["observation"])


class ExpectedValue(BaseModel):
    """The ground-truth side of a discrepancy, with provenance attached."""
    value: Scalar = None
    source: str = ""       # file / formula the expectation came from
    provenance: str = ""   # verified | community | engine-formula


class BugTicket(BaseModel):
    """One dimensioned claim about one move on one channel."""
    schema_version: int = SCHEMA_VERSION
    id: str
    created: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: Literal["open", "in_progress", "fixed", "wontfix"] = "open"

    move: str                      # CharacterState name, e.g. HEAVY_PUNCH
    player: int                    # who performed it (1 or 2)
    channel: Channel
    frame_range: Tuple[int, int]   # global game frames the move spanned

    observed: Scalar = None        # what the engine actually did
    expected: Optional[ExpectedValue] = None
    delta: Optional[float] = None  # observed - expected, when numeric

    # Free text for the human: what it looked/felt like. The whole point of
    # the system is that this field is now OPTIONAL colour, not the spec.
    complaint: str = "<optional: describe what you saw or felt>"

    measured_summary: Dict[str, Any] = Field(default_factory=dict)
    repro: Dict[str, Any] = Field(default_factory=dict)
    fix_hints: List[str] = Field(default_factory=list)


def write_ticket(ticket: BugTicket, out_dir: str = "bugs") -> str:
    """Write a ticket as YAML. Returns the path."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{ticket.id}.yaml")
    with open(path, "w") as f:
        yaml.safe_dump(ticket.model_dump(), f, sort_keys=False, width=100)
    return path


def load_ticket(path: str) -> BugTicket:
    """Load + validate a ticket YAML (round-trip used by tests and tooling)."""
    with open(path) as f:
        return BugTicket.model_validate(yaml.safe_load(f))
