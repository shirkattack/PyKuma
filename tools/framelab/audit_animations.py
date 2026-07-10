#!/usr/bin/env python3
"""Static animation audit — cross-checks the sprite track (animations.yaml)
against the ROM-verified mechanical track (hitboxes.yaml via the repository)
WITHOUT running the game.

The mechanical timing is the ruler: an attack animation's game-frame length
should equal the move's ROM total, so cels neither get cut off nor freeze on
the last pose mid-move. animations.yaml also embeds legacy frame_data/hitbox
blocks that predate the ROM repository; where they've drifted, they're flagged
as data_drift (the repository is canonical — see ARCHITECTURE.md).

Checks, per attack state in Akuma's _STATE_ANIM:
  1. missing animation        -> sprite_mapping   (state maps to nothing)
  2. anim length vs ROM total -> sprite_timing    (numbered-sprite anims)
  3. embedded frame_data vs ROM timing -> data_drift (per drifted field)
  4. embedded hitbox block present     -> data_drift (stale non-ROM boxes)

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


def _state_anim_mapping() -> dict:
    """Akuma's state -> animation-name mapping (imports pygame; dummy driver)."""
    from street_fighter_3rd.characters.akuma import Akuma
    return dict(Akuma._STATE_ANIM)


def _anim_game_frames(anim: dict):
    """Declared game-frame length of a numbered-sprite animation, or None when
    it can't be computed statically (folder animations depend on files on disk)."""
    if anim.get("source") != "numbered_sprites":
        return None
    sprites = anim.get("sprites") or []
    return len(sprites) * int(anim.get("frame_duration", 1))


def audit(character: str = "akuma") -> list:
    """Run all checks; returns a list of finding dicts (empty = clean)."""
    with open(ANIMATIONS_YAML) as f:
        doc = yaml.safe_load(f)
    anims = doc["characters"][character]["animations"]
    findings = []

    def flag(move, channel, observed, expected, source, provenance, note=""):
        findings.append({"move": move, "channel": channel, "observed": observed,
                         "expected": expected, "source": source,
                         "provenance": provenance, "note": note})

    for state, anim_name in sorted(_state_anim_mapping().items(),
                                   key=lambda kv: kv[0].name):
        if state not in _ATTACK_STATES:
            continue
        mfd = get_move_frame_data(state)
        if mfd is None:
            continue  # no ROM record mapped to this state yet — nothing to ruler against
        rom_total = mfd.startup + len(mfd.active) + mfd.recovery

        anim = anims.get(anim_name)
        if anim is None:
            flag(state.name, "sprite_mapping", None, anim_name,
                 "src/street_fighter_3rd/data/animations.yaml", "engine-mapping",
                 f"_STATE_ANIM maps {state.name} -> '{anim_name}' but no such "
                 "animation is defined; the renderer will fall back")
            continue

        length = _anim_game_frames(anim)
        if length is not None and length != rom_total:
            flag(state.name, "sprite_timing", length, rom_total,
                 "animations.yaml length vs hitboxes.yaml (ROM) total", "verified",
                 f"animation '{anim_name}' plays for {length} game frames but the "
                 f"move runs {rom_total}; cels will "
                 + ("hold the last pose early" if length < rom_total
                    else "be cut off at move end"))

        fd = anim.get("frame_data")
        if fd:
            rom = {"startup": mfd.startup, "active": len(mfd.active),
                   "recovery": mfd.recovery, "total": rom_total}
            for field_name, rom_value in rom.items():
                if field_name in fd and int(fd[field_name]) != rom_value:
                    flag(state.name, "data_drift", int(fd[field_name]), rom_value,
                         f"animations.yaml embedded frame_data.{field_name} "
                         "vs ROM repository", "verified",
                         "stale duplicated timing; the ROM repo is canonical — "
                         "delete or regenerate the embedded block")
        if anim.get("hitbox"):
            flag(state.name, "data_drift", "embedded hitbox block", "none",
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
