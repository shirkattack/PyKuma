"""AI difficulty profiles — the "boss" ladder, simple to advanced.

Each tier is an :class:`AIProfile` that parameterizes the shared decision engine
(`ai_controller.AIController`). Lower tiers are reaction-limited and sloppy; higher
tiers react instantly, space tighter, poke faster, and spend meter. Advanced
capability flags (whiff_punish / combos / parry / reads_inputs) are declared here
but only some are consumed in Phase A — they light up in later phases.

Field names mirror ``schemas.sf3_schemas.AIPersonality`` so character-authored
personalities stay compatible. Everything here is data; the engine stays
deterministic (fixed-seed PRNG + frame counters, no wall-clock).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class AIProfile:
    key: str
    name: str                     # display name (HUD / menu)

    # Personality (0..1) — mirrors AIPersonality.
    aggression: float = 0.5
    defensive_style: float = 0.5
    zoning_preference: float = 0.5
    combo_preference: float = 0.5
    risk_taking: float = 0.5

    # Execution.
    reaction_frames: int = 0      # perception delay; 0 = instant. Higher = easier.
    input_accuracy: float = 1.0   # 0.5..1.0; chance a decided ATTACK input executes.

    # Spacing / pace tuning.
    spacing_scale: float = 1.0    # multiplies action ranges (>1 = acts from farther).
    act_period: int = 24          # poke cadence in frames (lower = pokes more often).

    # Capability flags (gate which tactics are available).
    anti_air: bool = True
    block: bool = True
    throw: bool = True
    zoning: bool = True           # throws fireballs from range
    use_super: bool = False       # fire a Super Art when meter is full + in range
    whiff_punish: bool = False    # Phase B
    combos: bool = False          # Phase C
    raging_demon_punish: bool = False  # Phase C/D
    parry: bool = False           # Phase B
    reads_inputs: bool = False    # Phase D (input-reading final boss)

    # Final-boss "boss syndrome" stat buffs (applied by Game when != 1.0).
    health_scale: float = 1.0
    meter_gain_scale: float = 1.0

    locked: bool = False          # not selectable until unlocked


# The ladder. Order matters for the menu + arcade-ladder progression.
PROFILES: Dict[str, AIProfile] = {
    "novice": AIProfile(
        key="novice", name="Novice",
        aggression=0.3, defensive_style=0.3, zoning_preference=0.1, risk_taking=0.2,
        reaction_frames=14, input_accuracy=0.6, spacing_scale=0.8, act_period=36,
        anti_air=False, throw=False, zoning=False, use_super=False),

    "brawler": AIProfile(   # == today's CPU (instant, accurate, balanced)
        key="brawler", name="Brawler",
        aggression=0.5, reaction_frames=0, input_accuracy=1.0, spacing_scale=1.0,
        act_period=24, use_super=False),

    "technician": AIProfile(
        key="technician", name="Technician",
        aggression=0.6, defensive_style=0.6, zoning_preference=0.6,
        reaction_frames=0, input_accuracy=0.95, spacing_scale=1.05, act_period=20,
        use_super=True, whiff_punish=True, parry=True),

    "veteran": AIProfile(
        key="veteran", name="Veteran",
        aggression=0.7, combo_preference=0.8, risk_taking=0.6,
        reaction_frames=0, input_accuracy=0.97, spacing_scale=1.1, act_period=17,
        use_super=True, whiff_punish=True, combos=True, parry=True),

    "master": AIProfile(
        key="master", name="Master",
        aggression=0.85, combo_preference=0.9, risk_taking=0.7,
        reaction_frames=0, input_accuracy=0.99, spacing_scale=1.2, act_period=14,
        use_super=True, whiff_punish=True, combos=True, parry=True,
        raging_demon_punish=True),

    "shin_akuma": AIProfile(   # input-reading final boss (Phase D); locked for now
        key="shin_akuma", name="Shin Akuma",
        aggression=1.0, combo_preference=1.0, risk_taking=0.85,
        reaction_frames=0, input_accuracy=1.0, spacing_scale=1.3, act_period=11,
        use_super=True, whiff_punish=True, combos=True, parry=True,
        raging_demon_punish=True, reads_inputs=True,
        health_scale=1.25, meter_gain_scale=1.5, locked=True),
}

DEFAULT_PROFILE = "brawler"
DEFAULT_AI_SEED = 20251217   # fixed -> deterministic AI variety across runs/replays


def get_profile(key: str) -> AIProfile:
    return PROFILES.get(key, PROFILES[DEFAULT_PROFILE])


def selectable_profiles() -> List[AIProfile]:
    """Tiers offered in the difficulty menu (locked ones excluded)."""
    return [p for p in PROFILES.values() if not p.locked]
