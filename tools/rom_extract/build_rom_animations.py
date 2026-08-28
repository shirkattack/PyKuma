#!/usr/bin/env python3
"""Per-move animation tables from the ROM: cel sequence + durations + axis.

    uv run python tools/rom_extract/build_rom_animations.py --cels ~/akuma_cels

Joins two ROM-derived sources:
  * the frame dumps vendored under data/characters/akuma/rom_combat_sessions/
    (one record per emulated frame with each player's animation id and cel id,
    `anim` / `anim_frame`) -> for every animation id, the cel timeline of a
    WHIFFED run: [(cel, frames held), ...]. A connect freezes the attacker
    (hitstop) and stretches the run, so whiffed runs are preferred and frozen
    frames are dropped otherwise. Looping animations (stance, walks, crouch
    idle) are cut to one cycle.
  * the ripped cels (`cels.json` + `cel_<id>.png` from cel_decode.py --p1):
    each cel's bbox relative to the character's axis.

Writes data/characters/akuma/rom_animations.json (numbers only -- committed)
and copies the PNGs to assets/characters/akuma/rom_cels/ (Capcom art -- the
assets tree is git-ignored). Animation ids are labelled by role: attacks from
move_names.json (state + close/far/neutral variant), movement and reactions
from their kinematics in the dumps (KINEMATIC_ROLES below; the observed
signature -- walk speed, posture byte, airborne, blockstun -- is recorded).
The engine (characters/akuma.py) maps its animation names onto these roles
and only swaps a folder clip for a ROM clip when every cel of the sequence
was ripped.
"""

from __future__ import annotations

import argparse
import itertools
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest  # noqa: E402  (tools/rom_extract/ingest.py)

DUMPS = [
    REPO / "data/characters/akuma/rom_combat_sessions/session3_dump.jsonl.gz",
    REPO / "data/characters/akuma/rom_combat_sessions/session2_dump.jsonl.gz",
]
MOVE_NAMES = REPO / "data/characters/akuma/move_names.json"
FRAMEDATA = REPO / "data/sources/gouki_framedata.json"
OUT_JSON = REPO / "data/characters/akuma/rom_animations.json"
OUT_CELS = REPO / "assets/characters/akuma/rom_cels"

# Non-attack animation ids, identified from their kinematics in the frame
# dumps (P1's own runs, and the dummy's reactions -- both players are Akuma, so
# the ids and cels are shared). `loop` = idle/cyclic clip: cut to one cycle.
# signature: dx/frame relative to facing, ROM posture byte, airborne, blockstun.
KINEMATIC_ROLES = {
    "8800": {"role": "stance",          "loop": True,  "signature": "posture 0, no motion"},
    "8910": {"role": "walk_forward",    "loop": True,  "signature": "dx +2.4/f, posture 6"},
    "89e0": {"role": "walk_backward",   "loop": True,  "signature": "dx -1.7/f, posture 8"},
    "8ab0": {"role": "dash_forward",    "loop": False, "signature": "dx +2.4/f, posture 10, busy"},
    "8b60": {"role": "dash_backward",   "loop": False, "signature": "dx -1.9/f, posture 12, busy"},
    "8c20": {"role": "crouch_down",     "loop": False, "signature": "posture 32, 3 cels, from stand"},
    "8c90": {"role": "crouch_hold",     "loop": True,  "signature": "posture 32, held cels (idle)"},
    "8d60": {"role": "crouch_up",       "loop": False, "signature": "posture 32 -> stand"},
    "8f20": {"role": "jump_up",         "loop": False, "signature": "airborne, dx 0, posture 22"},
    "8e20": {"role": "jump_forward",    "loop": False, "signature": "airborne, dx +3.6/f, posture 20"},
    "9030": {"role": "jump_backward",   "loop": False, "signature": "airborne, dx -0.7/f, posture 24"},
    "10d0": {"role": "taunt",           "loop": False, "signature": "P1 only, posture 0, 7 cels"},
    "8210": {"role": "gohadoken",       "loop": False, "signature": "P1 fireball launch, 14 cels; hits at f24+ (the projectile)"},
    "a130": {"role": "air_gohadoken",   "loop": False, "signature": "airborne (posture 22), dx +2.3/f, busy: the air fireball"},
    # hand-off tails: what the ROM plays after a script ends (see NEUTRAL_ANIMS / build `next`)
    "6a2c": {"role": "dp_land",         "loop": False, "signature": "after 84f8 (every DP falls into 84f8's tail): landing, 4 cels"},
    "645c": {"role": "tatsu_land",      "loop": False, "signature": "after every ground/air tatsu: landing recovery, 5 cels"},
    "5c7c": {"role": "jump_attack_land", "loop": False, "signature": "after a jump normal touches down, 1 cel"},
    "5b7c": {"role": "jump_land",       "loop": False, "signature": "after a plain jump touches down, 3 cels"},
    "7684": {"role": "air_fireball_land", "loop": False, "signature": "after a130 (air fireball) touches down, 5 cels"},
    "a2ec": {"role": "hit_medium",      "loop": False, "signature": "dummy stand reel, most frequent"},
    "adfc": {"role": "crouch_hit",      "loop": False, "signature": "dummy reel, posture 32"},
    "c4b0": {"role": "launch_spin",     "loop": False, "signature": "dummy launched, posture 24 (after DP)"},
    "5cec": {"role": "lying",           "loop": True,  "signature": "dummy posture 38, long"},
    "afec": {"role": "knockdown",       "loop": False, "signature": "dummy posture 38 -> 0 (wake-up)"},
    "9fdc": {"role": "block_high",      "loop": False, "signature": "dummy blocking_id set, posture 0"},
    "a05c": {"role": "block_crouch",    "loop": False, "signature": "dummy blocking_id set, posture 32"},
}


def load_move_names(path: Path = MOVE_NAMES) -> dict:
    """rom_id -> {"state", "variant"} from move_names.json ("STATE" or "STATE:variant")."""
    names = json.loads(Path(path).read_text())
    out = {}
    for key, info in names.items():
        if not isinstance(info, dict) or "rom_id" not in info:
            continue
        state, _, variant = key.partition(":")
        out[info["rom_id"]] = {"state": state, "variant": variant or None}
    return out


# Idle / movement ids: a hand-off INTO one of these ends a chain (the move is over).
NEUTRAL_ANIMS = {"8800", "8910", "89e0", "8c20", "8c90", "8d60", "9490", "88c0", "8ab0", "8b60", "8f20", "8e20", "9030"}


def successors(records: list[dict]) -> dict[str, dict]:
    """anim -> {"anim": most common non-neutral successor, "start_cel": the cel
    the successor run begins on, "count": n} from the c1 runs. The successor's
    first cel matters because a hand-off can enter a script mid-way (MP/HP DP
    fall into 84f8 at its 5th cel)."""
    from collections import Counter, defaultdict
    runs = []
    cur = None
    for r in records:
        c = r.get("c1")
        if not c:
            continue
        if cur is None or c["anim"] != cur[0]:
            cur = [c["anim"], c["anim_frame"]]
            runs.append(cur)
    votes: dict[str, Counter] = defaultdict(Counter)
    for (a, _), (b, first_cel) in zip(runs, runs[1:]):
        if b in NEUTRAL_ANIMS or a == b:
            continue
        votes[a][(b, first_cel)] += 1
    out = {}
    for a, cnt in votes.items():
        (b, first_cel), n = cnt.most_common(1)[0]
        out[a] = {"anim": b, "start_cel": first_cel, "count": n}
    return out


def runs_by_anim(records: list[dict]) -> dict[str, list[dict]]:
    """anim -> [run, ...] over both players; a run is {"side", "cels": [cel per
    frame, unfrozen frames only], "whiff": no frame frozen, "frames": run length}."""
    out: dict[str, list[dict]] = defaultdict(list)
    for side in ("c1", "c2"):
        cur = None
        for r in records:
            c = r.get(side)
            if not c:
                continue
            if cur is None or c["anim"] != cur["anim"]:
                if cur is not None:
                    out[cur["anim"]].append(cur)
                cur = {"anim": c["anim"], "side": side, "cels": [], "frames": 0, "whiff": True}
            cur["frames"] += 1
            if c.get("freeze", 0):
                cur["whiff"] = False
            else:
                cur["cels"].append(c["anim_frame"])
        if cur is not None:
            out[cur["anim"]].append(cur)
    return out


def one_cycle(cels: list[int]) -> list[int]:
    """Shortest prefix that the per-frame cel list keeps repeating (a looping
    clip); the whole list when no period is found."""
    n = len(cels)
    for p in range(2, n // 2 + 1):
        if all(cels[i] == cels[i + p] for i in range(n - p)):
            return cels[:p]
    return cels


def cut_at_restart(cels: list[int]) -> list[int]:
    """A one-shot clip performed back to back (dash, dash, dash) is one run
    for the dump since the anim id never changes: cut where the clip's opening
    pattern (its first two cels, with their holds) starts over. A clip that
    merely revisits its first cel (a jump bob) is left alone."""
    groups = [(c, len(list(g))) for c, g in itertools.groupby(cels)]
    if len(groups) < 3:
        return cels
    k = groups[0][1] + groups[1][1]
    head = cels[:k]
    for i in range(k, len(cels) - k + 1):
        if cels[i:i + k] == head:
            return cels[:i]
    return cels


def sequence(cels: list[int]) -> list[list[int]]:
    """[[cel, frames], ...] from a per-frame cel list."""
    return [[cel, len(list(g))] for cel, g in itertools.groupby(cels)]


def pick_run(runs: list[dict], loop: bool, rom_total: int | None, typical: bool = False) -> dict | None:
    """The run to take the timeline from: a whiffed run whose length matches the
    framedata total when one is known, else the longest whiffed run, else the
    longest run with its frozen frames dropped."""
    if not runs:
        return None
    whiffs = [r for r in runs if r["whiff"] and r["cels"]]
    if rom_total and not loop:
        exact = [r for r in whiffs if len(r["cels"]) == rom_total]
        if exact:
            return max(exact, key=lambda r: r["frames"])
    pool = whiffs or [r for r in runs if r["cels"]]
    if not pool:
        return None
    if typical:
        # a tail clip (landing) is followed by whatever the player did next;
        # the typical run length is the clip, the longest run is a pause
        from collections import Counter
        n = Counter(len(r["cels"]) for r in pool).most_common(1)[0][0]
        return next(r for r in pool if len(r["cels"]) == n)
    return max(pool, key=lambda r: len(r["cels"]))


def build(records: list[dict], cels_manifest: dict, move_names: dict,
          framedata: dict | None = None, roles: dict = KINEMATIC_ROLES) -> dict:
    runs = runs_by_anim(records)
    anims = {}
    for anim, rlist in runs.items():
        role = roles.get(anim)
        named = anim in move_names or role is not None
        if not named:
            continue
        loop = bool(role and role["loop"])
        rom_total = None
        if framedata and anim in framedata and isinstance(framedata[anim], dict):
            rom_total = len(framedata[anim].get("frames", [])) or None
        run = pick_run(rlist, loop, rom_total, typical=bool(role and role["role"].endswith("_land")))
        if run is None:
            continue
        cels = run["cels"]
        if loop:
            cels = one_cycle(cels)
        elif rom_total is None:
            cels = cut_at_restart(cels)
        seq = sequence(cels)
        missing = sorted({c for c, _ in seq if str(c) not in cels_manifest})
        entry = {
            "loop": loop,
            "sequence": seq,
            "total": sum(n for _, n in seq),
            "rom_total": rom_total,
            "source": {"side": run["side"], "whiff": run["whiff"], "runs": len(rlist)},
            "complete": not missing,
            "missing_cels": missing,
        }
        if anim in move_names:
            entry.update(move_names[anim])
            if not entry["variant"]:
                # which proximity/jump variant the un-varianted record IS: the
                # sibling that exists in move_names is the other one
                siblings = {v["variant"] for v in move_names.values() if v["state"] == entry["state"] and v["variant"]}
                if "far" in siblings:
                    entry["equals_variant"] = "close"
                elif "close" in siblings:
                    entry["equals_variant"] = "far"
        if role:
            entry["role"] = role["role"]
            entry["signature"] = role["signature"]
        anims[anim] = entry
    # hand-offs between the emitted anims: next anim + the index into its
    # sequence where the run entered it. A hand-off is the ROM's, not the
    # player's next input, when the successor is a tail (not an attack script)
    # or is entered mid-script (MP/HP DP fall into 84f8's 5th cel), seen twice+.
    for a, nxt in successors(records).items():
        if a in anims and nxt["anim"] in anims and nxt["count"] >= 2:
            seq_cels = [c for c, _ in anims[nxt["anim"]]["sequence"]]
            idx = seq_cels.index(nxt["start_cel"]) if nxt["start_cel"] in seq_cels else 0
            successor_is_attack = nxt["anim"] in move_names
            if successor_is_attack and idx == 0:
                continue
            anims[a]["next"] = {"anim": nxt["anim"], "start_index": idx, "count": nxt["count"]}
    used = {c for a in anims.values() for c, _ in a["sequence"]}
    cels = {}
    for cel, info in cels_manifest.items():
        if int(cel) in used:
            cels[cel] = {k: info[k] for k in ("left", "top", "width", "height")}
    return {"anims": dict(sorted(anims.items())), "cels": dict(sorted(cels.items(), key=lambda kv: int(kv[0])))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cels", required=True, help="folder with cels.json + cel_<id>.png (cel_decode.py --p1 output)")
    ap.add_argument("--dumps", nargs="*", default=[str(p) for p in DUMPS], help="frame dumps (.jsonl or .jsonl.gz)")
    ap.add_argument("--out", default=str(OUT_JSON))
    ap.add_argument("--assets", default=str(OUT_CELS), help="where the cel PNGs are copied")
    ap.add_argument("--no-copy", action="store_true", help="don't copy the PNGs")
    args = ap.parse_args(argv)

    cels_dir = Path(args.cels).expanduser()
    manifest = json.loads((cels_dir / "cels.json").read_text())
    records = []
    for d in args.dumps:
        records.extend(ingest.load_jsonl(d))
    framedata = json.loads(FRAMEDATA.read_text()) if FRAMEDATA.exists() else None
    doc = build(records, manifest, load_move_names(), framedata)
    doc["_meta"] = {
        "source": "sfiii3nr1 memory: cel per frame from the frame dumps (whiffed runs), cel sprites/axis from "
                  "dump_cels.lua + cel_decode.py; see tools/rom_extract/README.md",
        "dumps": [Path(d).name for d in args.dumps],
        "cels_ripped": len(manifest),
        "status": "verified",
        "axis": "cel bbox left/top are px from the character's axis (between the feet), y down; "
                "sprites face right",
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")

    if not args.no_copy:
        out = Path(args.assets)
        out.mkdir(parents=True, exist_ok=True)
        n = 0
        for cel in doc["cels"]:
            src = cels_dir / f"cel_{cel}.png"
            if src.exists():
                shutil.copyfile(src, out / f"cel_{cel}.png")
                n += 1
        print(f"copied {n} cel PNGs -> {out}")

    anims = doc["anims"]
    complete = [a for a, e in anims.items() if e["complete"]]
    print(f"{len(anims)} animations, {len(complete)} complete, {len(doc['cels'])} cels used -> {args.out}")
    for a, e in anims.items():
        label = e.get("role") or f"{e.get('state')}" + (f":{e['variant']}" if e.get("variant") else "")
        flag = "" if e["complete"] else f"  MISSING {e['missing_cels']}"
        tot = f"{e['total']}" + (f"/{e['rom_total']}" if e["rom_total"] else "")
        print(f"  {a} {label:28s} {len(e['sequence']):3d} cels {tot:>7s}f {'whiff' if e['source']['whiff'] else 'unfrozen'}{flag}")


if __name__ == "__main__":
    main()
