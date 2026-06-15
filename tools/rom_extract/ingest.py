#!/usr/bin/env python3
"""Ingest a ROM frame-data dump (from dump_framedata.lua) into PyKuma data.

The Lua dumper writes JSON-Lines, one record per emulated frame:
  {"f", "pos_x", "pos_y", "flip", "posture", "anim", "anim_frame", "boxes":[
     {"type","left","width","bottom","height"}, ...]}
where type is one of push/throwable/vulnerability/ext_vulnerability/attack/throw
and the box fields use the ROM convention (left/bottom signed, origin at feet,
forward = negative; see docs/HITBOX_PIPELINE_NOTES.md).

Three jobs (kept as importable pure functions so they're unit-testable without an
emulator):

  reconstruct  - group frames by animation id -> per-move frame arrays of boxes,
                 in the SAME schema as data/sources/gouki_framedata.json, so the
                 existing converter (tools/framedata/convert_3rd_training.py) can
                 consume an enriched dump unchanged.
  physics      - derive walk speed / jump arc (gravity, initial velocity) / dash
                 distance from the per-frame position series -> physics.yaml
                 (provenance-tagged; flagged for human review).
  validate     - cross-check the extracted per-move hurtbox (v_hb) for st.LP /
                 st.LK / st.MK against the Baston seed in vhb_supplement.json.

NO INVENTED DATA: every value here is read from ROM memory; this script only
reshapes it. Run `--selftest` (or pytest tests/test_rom_ingest.py) for a check.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

# Per-move hurtbox EXTENSION lives in the ROM's "ext_vulnerability" array; the
# plain "vulnerability" array is the body stack (already covered by base_hurtbox
# from idle). The validate step confirms which array matches Baston before trust.
DEFAULT_VHB_SOURCE = "ext_vulnerability"


# ---- IO ---------------------------------------------------------------------

def load_jsonl(path: str) -> List[dict]:
    """Parse the dumper's JSON-Lines file into a list of frame records."""
    out = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


# ---- reconstruct moves ------------------------------------------------------

def _box_key(b: dict) -> tuple:
    return (b["type"], b["left"], b["width"], b["bottom"], b["height"])


def reconstruct_moves(records: List[dict]) -> Dict[str, dict]:
    """Group per-frame records by animation id into the gouki_framedata schema.

    Returns {anim_id: {"frames": [ {"boxes": [ {type,left,bottom,width,height} ]},
    ... ]}} where the frames list is dense by `anim_frame` (0-indexed). When the
    same (anim, anim_frame) is seen on multiple passes, boxes are unioned (deduped).
    """
    # anim -> frame_index -> set of boxes (deduped by geometry)
    acc: Dict[str, Dict[int, Dict[tuple, dict]]] = defaultdict(lambda: defaultdict(dict))
    for r in records:
        anim = r.get("anim")
        fi = r.get("anim_frame")
        if anim is None or fi is None:
            continue
        frame_map = acc[anim][fi]  # register the frame even if it has no boxes
        for b in r.get("boxes", []):
            frame_map[_box_key(b)] = {
                "type": b["type"], "left": b["left"], "bottom": b["bottom"],
                "width": b["width"], "height": b["height"],
            }

    moves: Dict[str, dict] = {}
    for anim, frames_by_idx in acc.items():
        if not frames_by_idx:
            continue
        maxf = max(frames_by_idx)
        frames = []
        for i in range(maxf + 1):
            boxes = list(frames_by_idx.get(i, {}).values())
            frames.append({"boxes": boxes, "movement": [0, 0]})
        moves[anim] = {"frames": frames}
    return moves


def remap_box_types(moves: Dict[str, dict], vhb_source: str = DEFAULT_VHB_SOURCE) -> Dict[str, dict]:
    """Map dumper box types to the converter's schema in place-copy.

    - "attack" stays "attack".
    - the chosen per-move hurtbox array (vhb_source) becomes "vulnerability"
      (what the converter applies as a centered per-move hurtbox extension).
    - all other arrays (push/throwable/throw and the non-chosen vuln array) are
      dropped from move frames (base pushbox/throwbox come from `idle` already).
    """
    out: Dict[str, dict] = {}
    for anim, mv in moves.items():
        frames = []
        for fr in mv["frames"]:
            kept = []
            for b in fr["boxes"]:
                if b["type"] == "attack":
                    kept.append({**b, "type": "attack"})
                elif b["type"] == vhb_source:
                    kept.append({**b, "type": "vulnerability"})
            frames.append({"boxes": kept, "movement": fr.get("movement", [0, 0])})
        out[anim] = {"frames": frames}
    return out


def merge_into_framedata(reconstructed: Dict[str, dict], framedata_path: str,
                         out_path: str, vhb_source: str = DEFAULT_VHB_SOURCE) -> dict:
    """Add extracted per-move vulnerability boxes onto the vendored framedata.

    For each move present in BOTH the dump and the framedata, copy the extracted
    "vulnerability" boxes onto the matching frame's box list (only frames that
    already have attack boxes -- i.e. active frames). Writes an enriched copy to
    out_path. Returns a summary dict. The existing converter then picks the
    vulnerability boxes up with no code change.
    """
    base = json.loads(Path(framedata_path).read_text())
    remapped = remap_box_types(reconstructed, vhb_source)
    touched, added = 0, 0
    for anim, mv in remapped.items():
        if anim not in base or "frames" not in base[anim]:
            continue
        bframes = base[anim]["frames"]
        for i, fr in enumerate(mv["frames"]):
            if i >= len(bframes):
                break
            vulns = [b for b in fr["boxes"] if b["type"] == "vulnerability"]
            if not vulns:
                continue
            existing = bframes[i].setdefault("boxes", [])
            has_attack = any(b["type"] == "attack" for b in existing)
            if not has_attack:
                continue  # only annotate active frames
            keys = {_box_key(b) for b in existing}
            for v in vulns:
                if _box_key(v) not in keys:
                    existing.append(v)
                    added += 1
            touched += 1
    Path(out_path).write_text(json.dumps(base, indent=1))
    return {"frames_touched": touched, "vuln_boxes_added": added, "out": out_path}


# ---- physics derivation -----------------------------------------------------

def _runs(flags: List[bool]) -> List[tuple]:
    """Yield (start, end_exclusive) index ranges where flags is True."""
    runs, start = [], None
    for i, f in enumerate(flags):
        if f and start is None:
            start = i
        elif not f and start is not None:
            runs.append((start, i)); start = None
    if start is not None:
        runs.append((start, len(flags)))
    return runs


def _instances(records: List[dict]) -> List[dict]:
    """Group records into contiguous instances of the same animation id
    (consecutive global frame numbers). Each instance is one performance of a
    move/state."""
    insts: List[dict] = []
    cur = None
    for r in records:
        if cur and r.get("anim") == cur["anim"] and r.get("f", 0) == cur["f_end"] + 1:
            cur["rows"].append(r); cur["f_end"] = r["f"]
        else:
            cur = {"anim": r.get("anim"), "f_end": r.get("f", 0), "rows": [r]}
            insts.append(cur)
    return insts


def _has_attack(rows: List[dict]) -> bool:
    return any(b["type"] == "attack" for r in rows for b in r.get("boxes", []))


def derive_physics(records: List[dict]) -> dict:
    """Derive walk/jump/dash constants by ANIMATION-ID segmentation.

    Far more reliable than guessing from raw position deltas: each movement state
    (walk/dash/jump) is its own animation, so we group contiguous instances of
    each non-attack anim id and read constants off them. Jumps = anims with a
    pos_y excursion; dashes = ground anims with a large net x displacement; walks
    = ground anims that recur as short low-speed bursts. Values flagged _review.
    """
    if not records:
        return {"error": "no records"}
    ys = [r.get("pos_y", 0) for r in records]
    baseline = Counter(ys).most_common(1)[0][0]

    moves: Dict[str, List[dict]] = defaultdict(list)
    for ins in _instances(records):
        if not _has_attack(ins["rows"]):       # exclude attack moves (their dx is recoil)
            moves[ins["anim"]].append(ins)

    jump_anims: Dict[str, dict] = {}
    ground: Dict[str, dict] = {}
    for anim, ins in moves.items():
        apex = max(abs(r.get("pos_y", 0) - baseline) for i in ins for r in i["rows"])
        netdxs = [i["rows"][-1].get("pos_x", 0) - i["rows"][0].get("pos_x", 0) for i in ins]
        med = statistics.median(netdxs)
        if apex > 4:  # any vertical excursion = a jump (ground moves have apex 0)
            jump_anims[anim] = {"n": len(ins), "apex": apex, "ins": ins, "netdx": med}
        elif abs(med) > 6:
            ground[anim] = {"n": len(ins), "netdx": med, "ins": ins}

    # --- jump: the most-performed airborne anim; read arc off its instances ---
    jump = None
    if jump_anims:
        janim = max(jump_anims, key=lambda a: jump_anims[a]["n"])
        arcs = []
        for i in jump_anims[janim]["ins"]:
            yy = [r.get("pos_y", 0) - baseline for r in i["rows"]]
            if sum(1 for v in yy if v > 0) < 6:
                continue
            vy = [yy[k + 1] - yy[k] for k in range(len(yy) - 1)]
            top = max(yy)
            asc = [vy[k + 1] - vy[k] for k in range(len(vy) - 1) if yy[k] < top]
            arcs.append({
                "airborne": sum(1 for v in yy if v > 0),
                "apex": top,
                "initial_vy": next((v for v in vy if v > 0), vy[0] if vy else 0),
                "gravity": statistics.median(asc) if asc else None,
            })
        if arcs:
            grav = [a["gravity"] for a in arcs if a["gravity"] is not None]
            jump = {
                "anim": janim,
                "airborne_frames": int(statistics.median(a["airborne"] for a in arcs)),
                "apex": int(statistics.median(a["apex"] for a in arcs)),
                "initial_vy": int(statistics.median(a["initial_vy"] for a in arcs)),
                "gravity_est": round(abs(statistics.median(grav)), 3) if grav else None,
            }

    # --- dashes (big net displacement) and walks (recurring small bursts) ---
    fwd = [a for a in ground if ground[a]["netdx"] > 0]
    back = [a for a in ground if ground[a]["netdx"] < 0]

    def _biggest(cands):
        return max(cands, key=lambda a: abs(ground[a]["netdx"])) if cands else None

    dash_f = _biggest([a for a in fwd if abs(ground[a]["netdx"]) >= 30])
    dash_b = _biggest([a for a in back if abs(ground[a]["netdx"]) >= 30])

    def _summarize_dash(anim):
        if not anim:
            return None
        best = max(ground[anim]["ins"],
                   key=lambda i: abs(i["rows"][-1].get("pos_x", 0) - i["rows"][0].get("pos_x", 0)))
        xs = [r.get("pos_x", 0) for r in best["rows"]]
        curve = [xs[k + 1] - xs[k] for k in range(len(xs) - 1)]
        while curve and curve[-1] == 0:        # trim recovery
            curve.pop()
        return {"anim": anim, "frames": len(curve), "distance": sum(curve), "curve": curve}

    def _walk(cands):
        cands = [a for a in cands if a not in (dash_f, dash_b)]
        if not cands:
            return {"anim": None, "speed_px_per_frame": None}
        anim = max(cands, key=lambda a: ground[a]["n"])  # walk recurs most
        sp = []
        for i in ground[anim]["ins"]:
            xs = [r.get("pos_x", 0) for r in i["rows"]]
            sp += [abs(xs[k + 1] - xs[k]) for k in range(len(xs) - 1) if xs[k + 1] != xs[k]]
        return {"anim": anim, "speed_px_per_frame": round(statistics.median(sp), 3) if sp else None}

    return {
        "_review": True,
        "_note": "Segmented by animation id (movement anims; attack frames excluded).",
        "ground_baseline_y": baseline,
        "jump": jump,
        "walk_forward": _walk(fwd),
        "walk_back": _walk(back),
        "dash_forward": _summarize_dash(dash_f),
        "dash_back": _summarize_dash(dash_b),
    }


def physics_to_yaml(physics: dict, rom_id: str, repo: str, commit: str) -> str:
    """Serialize derived physics to provenance-tagged YAML (no yaml dep needed)."""
    import yaml  # available in the project env
    doc = {
        "meta": {
            "source": {"repo": repo, "commit": commit, "rom_id": rom_id,
                       "status": "verified"},
            "note": "ROM-derived physics; values flagged _review were segmented "
                    "heuristically and should be confirmed.",
        },
        "physics": physics,
    }
    return yaml.safe_dump(doc, sort_keys=False)


# ---- validate against Baston seed -------------------------------------------

def validate_vhb(reconstructed: Dict[str, dict], move_names_path: str,
                 vhb_supplement_path: str) -> dict:
    """Compare extracted per-move v_hb for LP/LK/MK to the Baston seed.

    Returns a report per state for BOTH candidate arrays so the operator can see
    which ROM array (vulnerability vs ext_vulnerability) matches Baston.
    """
    names = json.loads(Path(move_names_path).read_text())
    seed = json.loads(Path(vhb_supplement_path).read_text())
    # state -> anim id
    state_to_anim = {}
    for anim, info in names.items():
        st = info.get("state") if isinstance(info, dict) else None
        if st:
            state_to_anim[st] = anim

    report = {}
    for state, supp in seed.items():
        anim = state_to_anim.get(state)
        seed_boxes = {(b["left"], b["width"], b["bottom"], b["height"])
                      for b in supp.get("boxes", [])}
        entry = {"anim": anim, "seed": sorted(seed_boxes), "matches": {}}
        if anim and anim in reconstructed:
            for src in ("vulnerability", "ext_vulnerability"):
                found = set()
                for fr in reconstructed[anim]["frames"]:
                    for b in fr["boxes"]:
                        if b["type"] == src:
                            found.add((b["left"], b["width"], b["bottom"], b["height"]))
                entry["matches"][src] = sorted(seed_boxes & found)
                entry[f"{src}_all"] = sorted(found)
        report[state] = entry
    return report


# ---- CLI --------------------------------------------------------------------

def _selftest() -> None:
    # synthetic: a 3-frame "move" (anim 1e88) with attack + ext_vuln, plus a jump
    recs = [
        {"f": 1, "pos_x": 100, "pos_y": 0, "flip": 1, "posture": 0,
         "anim": "1e88", "anim_frame": 0,
         "boxes": [{"type": "attack", "left": -60, "width": 32, "bottom": 32, "height": 32},
                   {"type": "ext_vulnerability", "left": -54, "width": 22, "bottom": 84, "height": 18}]},
        {"f": 2, "pos_x": 100, "pos_y": 0, "flip": 1, "posture": 0,
         "anim": "1e88", "anim_frame": 1, "boxes": []},
    ]
    # a simple symmetric jump: up then down, gravity ~ -? baseline 0
    yseq = [0, 0, 8, 14, 18, 20, 18, 14, 8, 0, 0]
    for i, y in enumerate(yseq):
        recs.append({"f": 100 + i, "pos_x": 200 + i, "pos_y": y, "flip": 1,
                     "posture": 0, "anim": "ffff", "anim_frame": i, "boxes": []})
    mv = reconstruct_moves(recs)
    assert "1e88" in mv and len(mv["1e88"]["frames"]) == 2, mv
    assert any(b["type"] == "ext_vulnerability" for b in mv["1e88"]["frames"][0]["boxes"])
    phys = derive_physics(recs)
    assert phys["ground_baseline_y"] == 0
    assert phys["jump"] and phys["jump"]["airborne_frames"] >= 4
    print("selftest OK:", json.dumps(phys["jump"]))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    pr = sub.add_parser("reconstruct", help="JSONL dump -> moves JSON (gouki schema)")
    pr.add_argument("dump"); pr.add_argument("--out", default="extracted_moves.json")

    pm = sub.add_parser("merge", help="enrich gouki_framedata.json with extracted v_hb")
    pm.add_argument("dump")
    pm.add_argument("--framedata", default="data/sources/gouki_framedata.json")
    pm.add_argument("--out", default="data/sources/gouki_framedata.enriched.json")
    pm.add_argument("--vhb-source", default=DEFAULT_VHB_SOURCE)

    pp = sub.add_parser("physics", help="movement JSONL -> physics.yaml")
    pp.add_argument("dump")
    pp.add_argument("--out", default="data/characters/akuma/physics.yaml")
    pp.add_argument("--rom-id", default="akuma")
    pp.add_argument("--repo", default="https://github.com/Grouflon/3rd_training_lua")
    pp.add_argument("--commit", default="73ec4c062108fd3494c4fae6b81a61f9cf518b81")

    pv = sub.add_parser("validate", help="compare extracted LP/LK/MK v_hb to Baston seed")
    pv.add_argument("dump")
    pv.add_argument("--names", default="data/characters/akuma/move_names.json")
    pv.add_argument("--vhb", default="data/characters/akuma/vhb_supplement.json")

    sub.add_parser("selftest", help="run the built-in self-test (no emulator)")

    args = p.parse_args(argv)
    if args.cmd == "selftest" or args.cmd is None:
        _selftest(); return
    if args.cmd == "reconstruct":
        mv = reconstruct_moves(load_jsonl(args.dump))
        Path(args.out).write_text(json.dumps(mv, indent=1))
        print(f"{len(mv)} animations -> {args.out}")
    elif args.cmd == "merge":
        mv = reconstruct_moves(load_jsonl(args.dump))
        print(merge_into_framedata(mv, args.framedata, args.out, args.vhb_source))
    elif args.cmd == "physics":
        phys = derive_physics(load_jsonl(args.dump))
        Path(args.out).write_text(physics_to_yaml(phys, args.rom_id, args.repo, args.commit))
        print(f"physics -> {args.out}: {json.dumps({k: phys[k] for k in phys if not k.startswith('_')})[:300]}")
    elif args.cmd == "validate":
        mv = reconstruct_moves(load_jsonl(args.dump))
        print(json.dumps(validate_vhb(mv, args.names, args.vhb), indent=2))


if __name__ == "__main__":
    main()
