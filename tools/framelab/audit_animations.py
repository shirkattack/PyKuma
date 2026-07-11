#!/usr/bin/env python3
"""Static animation audit — cross-checks the LIVE sprite track (the folder
animations Akuma actually registers in _setup_animations) against the
ROM-verified mechanical track (hitboxes.yaml via the repository) WITHOUT
running a fight.

The mechanical timing is the ruler: an attack animation's game-frame length
(sum of its per-cel holds) should equal the move's ROM total, so cels neither
get cut off nor freeze on the last pose mid-move. Since the ROM-fit pass,
Akuma computes those holds FROM the ROM totals at registration — this audit
guards that contract against regressions (a hand-tuned duration creeping back,
a folder going missing, a state mapped to an undefined animation).

animations.yaml is presentation data for the legacy numbered-sprite path and
is NOT what Akuma renders; it is only checked for reintroduced embedded
frame_data/hitbox blocks (data_drift — the ROM repository is canonical, see
ARCHITECTURE.md).

Checks, per attack state in Akuma's _STATE_ANIM:
  1. state maps to an unregistered animation  -> sprite_mapping
  2. anim game-frame length vs ROM total      -> sprite_timing
  3. folder animation's folder missing on disk -> sprite_fallback
  4. yaml embedded frame_data drift / hitbox   -> data_drift

Usage:
  python tools/framelab/audit_animations.py            # console report
  python tools/framelab/audit_animations.py --tickets  # also write bugs/*.yaml
  python tools/framelab/audit_animations.py --json out.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

import yaml  # noqa: E402

from street_fighter_3rd.data.enums import CharacterState  # noqa: E402
from street_fighter_3rd.data.akuma_hitboxes import get_move_frame_data  # noqa: E402

ANIMATIONS_YAML = os.path.join(
    REPO_ROOT, "src", "street_fighter_3rd", "data", "animations.yaml")

_ATTACK_STATES = {
    CharacterState.LIGHT_PUNCH, CharacterState.MEDIUM_PUNCH, CharacterState.HEAVY_PUNCH,
    CharacterState.LIGHT_KICK, CharacterState.MEDIUM_KICK, CharacterState.HEAVY_KICK,
    CharacterState.CROUCH_LIGHT_PUNCH, CharacterState.CROUCH_MEDIUM_PUNCH,
    CharacterState.CROUCH_HEAVY_PUNCH, CharacterState.CROUCH_LIGHT_KICK,
    CharacterState.CROUCH_MEDIUM_KICK, CharacterState.CROUCH_HEAVY_KICK,
    CharacterState.JUMP_LIGHT_PUNCH, CharacterState.JUMP_MEDIUM_PUNCH,
    CharacterState.JUMP_HEAVY_PUNCH, CharacterState.JUMP_LIGHT_KICK,
    CharacterState.JUMP_MEDIUM_KICK, CharacterState.JUMP_HEAVY_KICK,
    CharacterState.GOHADOKEN, CharacterState.GOSHORYUKEN, CharacterState.TATSUMAKI,
    CharacterState.OVERHEAD,
}

# States whose duration is animation-driven (no ROM record enforced by the
# engine); their anim length is reported informationally, never flagged.
_ANIMATION_DRIVEN = {
    CharacterState.GOHADOKEN, CharacterState.GOSHORYUKEN, CharacterState.TATSUMAKI,
}


def _live_akuma():
    """Construct the real Akuma headless — the animations it registers ARE
    the sprite track the game renders (folder clips; sprites lazy-load, so
    no assets are touched here)."""
    import pygame
    pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((320, 240))
    from street_fighter_3rd.characters.akuma import Akuma
    return Akuma(0, 0, 1)


def _anim_game_frames(anim) -> int:
    """Game-frame length of a registered animation: sum of per-cel holds."""
    return sum(fr.duration for fr in anim.frames)


def audit(character: str = "akuma", controller=None, state_anim=None) -> list:
    """Run all checks; returns a list of finding dicts (empty = clean).

    controller/state_anim are injectable for tests; by default the real
    Akuma is constructed and its live controller is audited.
    """
    if controller is None or state_anim is None:
        akuma = _live_akuma()
        controller = controller or akuma.animation_controller
        state_anim = state_anim or dict(type(akuma)._STATE_ANIM)

    findings = []

    def flag(move, channel, observed, expected, source, provenance, note=""):
        findings.append({"move": move, "channel": channel, "observed": observed,
                         "expected": expected, "source": source,
                         "provenance": provenance, "note": note})

    for state, anim_name in sorted(state_anim.items(), key=lambda kv: kv[0].name):
        if state not in _ATTACK_STATES:
            continue
        mfd = get_move_frame_data(state)
        if mfd is None:
            continue  # no ROM record mapped to this state yet — nothing to ruler against
        # ROM total, gap-aware: a multi-hit move (s.HK) runs longer than
        # startup+active+recovery because of the boxes-off gap between its
        # active windows — the animation must fill the FULL duration.
        rom_total = mfd.total or (mfd.startup + len(mfd.active) + mfd.recovery)

        anim = controller.animations.get(anim_name)
        if anim is None:
            flag(state.name, "sprite_mapping", None, anim_name,
                 "characters/akuma.py _STATE_ANIM vs _setup_animations",
                 "engine-mapping",
                 f"_STATE_ANIM maps {state.name} -> '{anim_name}' but no such "
                 "animation is registered; the renderer will fall back")
            continue

        if state not in _ANIMATION_DRIVEN:
            length = _anim_game_frames(anim)
            if length != rom_total:
                flag(state.name, "sprite_timing", length, rom_total,
                     "registered animation length vs hitboxes.yaml (ROM) total",
                     "verified",
                     f"animation '{anim_name}' plays for {length} game frames "
                     f"but the move runs {rom_total}; cels will "
                     + ("hold the last pose early" if length < rom_total
                        else "be cut off at move end"))

        folder = getattr(anim.frames[0], "folder_path", None) if anim.frames else None
        if folder and not os.path.isdir(os.path.join(REPO_ROOT, folder)):
            flag(state.name, "sprite_fallback", folder, "existing folder",
                 "assets/characters/akuma/animations", "engine",
                 f"animation '{anim_name}' points at a folder that does not "
                 "exist; every frame will draw the placeholder rectangle "
                 "(sprites are not bundled — extract via tools/sprite_extraction)")

    # animations.yaml: only the embedded-block guard remains (the numbered-
    # sprite lists there are NOT what Akuma renders).
    with open(ANIMATIONS_YAML) as f:
        doc = yaml.safe_load(f)
    yaml_anims = doc["characters"].get(character, {}).get("animations", {})
    reverse = {v: k for k, v in state_anim.items()}
    for anim_name, anim in yaml_anims.items():
        state = reverse.get(anim_name)
        move_name = state.name if state else anim_name
        fd = anim.get("frame_data") if isinstance(anim, dict) else None
        if fd:
            flag(move_name, "data_drift", "embedded frame_data block", "none",
                 "animations.yaml embedded frame_data vs ROM repository",
                 "verified",
                 "stale duplicated timing; the ROM repo is canonical — "
                 "delete or regenerate the embedded block")
        if isinstance(anim, dict) and anim.get("hitbox"):
            flag(move_name, "data_drift", "embedded hitbox block", "none",
                 "animations.yaml embedded hitbox vs ROM repository", "verified",
                 "hand-approximated boxes duplicated outside the ROM source of "
                 "record; verify nothing reads them, then remove")
    return findings


def write_tickets(findings, out_dir="bugs"):
    from street_fighter_3rd.schemas.bug_ticket import (
        BugTicket, ExpectedValue, hints_for, write_ticket)
    paths = []
    for i, f in enumerate(findings, 1):
        tid = f"audit_{f['move'].lower()}_{f['channel']}_{i:03d}"
        t = BugTicket(
            id=tid, move=f["move"], player=0, channel=f["channel"],
            frame_range=(0, 0),
            observed=f["observed"],
            expected=ExpectedValue(value=f["expected"], source=f["source"],
                                   provenance=f["provenance"]),
            delta=(float(f["observed"] - f["expected"])
                   if isinstance(f["observed"], (int, float))
                   and isinstance(f["expected"], (int, float)) else None),
            complaint="(static audit finding — no gameplay observation needed)",
            measured_summary={"note": f["note"]},
            fix_hints=hints_for(f["channel"]) + ([f["note"]] if f["note"] else []),
        )
        paths.append(write_ticket(t, out_dir))
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tickets", action="store_true",
                    help="also write one bugs/*.yaml ticket per finding")
    ap.add_argument("--json", metavar="PATH", help="write findings as JSON")
    args = ap.parse_args()

    findings = audit()
    if not findings:
        print("audit: sprite track and ROM track agree — no findings.")
        return 0

    w = max(len(f["move"]) for f in findings)
    print(f"audit: {len(findings)} finding(s)\n")
    for f in findings:
        print(f"  {f['move']:<{w}}  {f['channel']:<14} "
              f"observed={f['observed']!r:>10}  expected={f['expected']!r:>6}  "
              f"[{f['provenance']}]")
        if f["note"]:
            print(f"  {'':<{w}}  {f['note']}")
    if args.json:
        with open(args.json, "w") as fp:
            json.dump(findings, fp, indent=2)
        print(f"\nwrote {args.json}")
    if args.tickets:
        paths = write_tickets(findings)
        print(f"\nwrote {len(paths)} ticket(s) to bugs/")
    return 1


if __name__ == "__main__":
    sys.exit(main())
