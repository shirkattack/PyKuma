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


class _NegZero(int):
    """Lua writes a negative zero as `-0`; keep it so a round trip is byte-exact."""
    def __repr__(self):
        return "-0"


def _parse_int(text: str):
    return _NegZero(0) if text == "-0" else int(text)


def loads_framedata(text: str):
    """json.loads that keeps Lua's `-0` (see dumps_framedata)."""
    return json.loads(text, parse_int=_parse_int)


def dumps_framedata(value, indent: int = 0) -> str:
    """Serialize in the exact layout of the vendored gouki_framedata.json
    (3rd_training_lua's writer: 2-space nesting, `"key":value`, arrays of
    objects as `[{ ... },{ ... }]`, scalar arrays inline) so an enriched copy
    diffs against the vendored file by the added boxes only."""
    if isinstance(value, dict):
        if not value:
            return "{}"
        pad = " " * (indent + 2)
        body = ",\n".join(f'{pad}"{k}":{dumps_framedata(v, indent + 2)}' for k, v in value.items())
        return "{\n" + body + "\n" + " " * indent + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(isinstance(v, (dict, list)) for v in value):
            return "[" + ",".join(dumps_framedata(v, indent + 2) for v in value) + "]"
        return "[" + ",".join(dumps_framedata(v, indent) for v in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, str):
        return json.dumps(value)
    return repr(value)


# ---- reconstruct moves ------------------------------------------------------

def _frame_indices(rows: List[dict], side: str = "c1") -> List[int]:
    """Move-frame index (0-based) of every record in one contiguous anim run.

    The ROM does not advance an animation while the object is frozen by
    hitstop, but the dump keeps emitting one record per emulated frame, so a
    run that connected is stretched by the freeze. A record's index is the
    number of earlier records in the run on which `side` was NOT frozen: the
    connect frame keeps the index it advanced to (its freeze counter is set on
    that same frame) and the frozen frames after it repeat that index. Records
    without combat state (older dumps) count every frame.
    """
    out, n = [], 0
    for r in rows:
        out.append(n)
        c = r.get(side) or {}
        if not c.get("freeze", 0):
            n += 1
    return out


def _box_key(b: dict) -> tuple:
    return (b["type"], b["left"], b["width"], b["bottom"], b["height"])


def reconstruct_moves(records: List[dict], attacking_only: bool = False) -> Dict[str, dict]:
    """Group per-frame records by animation id into the gouki_framedata schema.

    Returns {anim_id: {"frames": [ {"boxes": [ {type,left,bottom,width,height} ]},
    ... ]}} where the frames list is dense and 0-indexed. The dump's `anim_frame`
    is a running cel id (not an index into the move), so -- exactly like
    `derive_combat` -- a move's frame index is counted from the start of each
    contiguous run of the same anim id (consecutive `f`). When the same
    (anim, index) is seen on multiple runs, boxes are unioned (deduped).
    Frames on which the player is frozen by hitstop do not advance the index
    (`_frame_indices`). Caveat: a move that re-triggers itself with no anim
    change in between reads as one long run; `merge_into_framedata` guards
    against that by checking the attack boxes line up with the vendored
    framedata before annotating.

    attacking_only: for an anim id that shows attack boxes in at least one run,
    drop the runs that never show one -- an attack exposes its attack boxes
    whether it hits or whiffs, so such a run is the id being used for
    something else (or a read glitch), not the move.
    """
    instances = [ins for ins in _instances(records) if ins["anim"] is not None]
    if attacking_only:
        has_attack = {ins["anim"] for ins in instances if _has_attack(ins["rows"])}
        instances = [ins for ins in instances
                     if ins["anim"] not in has_attack or _has_attack(ins["rows"])]
    # anim -> frame_index -> set of boxes (deduped by geometry)
    acc: Dict[str, Dict[int, Dict[tuple, dict]]] = defaultdict(lambda: defaultdict(dict))
    for ins in instances:
        anim = ins["anim"]
        for fi, r in zip(_frame_indices(ins["rows"]), ins["rows"]):
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

    Before a move is annotated its captured attack boxes must line up, index
    for index, with the vendored framedata (same geometry on every frame where
    the capture saw an attack box). A move that fails that check is reported
    under "misaligned" and left untouched -- the frame counting is off for it
    (e.g. a move that re-triggered itself mid-run), so its v_hb can't be trusted
    to land on the right frame either.
    """
    base = loads_framedata(Path(framedata_path).read_text())
    remapped = remap_box_types(reconstructed, vhb_source)
    touched, added, dropped = 0, 0, 0
    annotated, misaligned, unknown, no_attack = [], [], [], []

    def _attacks(boxes):
        return {_box_key(b) for b in boxes if b["type"] == "attack"}

    for anim, mv in remapped.items():
        if anim not in base or "frames" not in base[anim]:
            unknown.append(anim)
            continue
        bframes = base[anim]["frames"]
        checked, ok = 0, True
        for i, fr in enumerate(mv["frames"]):
            got = _attacks(fr["boxes"])
            if not got:
                continue
            want = _attacks(bframes[i].get("boxes", [])) if i < len(bframes) else set()
            checked += 1
            if got != want:
                ok = False
                break
        if checked == 0:
            no_attack.append(anim)   # nothing to line up against (dumper saw no attack box)
            continue
        if not ok:
            misaligned.append(anim)
            continue

        move_added = 0
        for i, fr in enumerate(mv["frames"]):
            vulns = [b for b in fr["boxes"] if b["type"] == "vulnerability"]
            if not vulns:
                continue
            if i >= len(bframes):
                dropped += 1
                continue
            existing = bframes[i].setdefault("boxes", [])
            if not any(b["type"] == "attack" for b in existing):
                dropped += 1  # v_hb on a non-active frame (hitboxes.yaml carries active frames only)
                continue
            keys = {_box_key(b) for b in existing}
            for v in vulns:
                if _box_key(v) not in keys:
                    existing.append(v)
                    added += 1
                    move_added += 1
            touched += 1
        if move_added:
            annotated.append(anim)
    Path(out_path).write_text(dumps_framedata(base))
    return {"frames_touched": touched, "vuln_boxes_added": added,
            "vuln_frames_dropped_non_active": dropped, "annotated": sorted(annotated),
            "misaligned": sorted(misaligned), "no_attack_boxes": sorted(no_attack),
            "not_in_framedata": sorted(unknown), "out": out_path}


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
    # move_names.json is keyed by state ("LIGHT_KICK", "LIGHT_PUNCH:close", ...)
    # with the ROM pointer under "rom_id". A seed for a base state is checked
    # against that state AND its close/far variants, since Baston labels the
    # close/far versions separately and the seed may belong to either.
    state_to_anim = {st: info["rom_id"] for st, info in names.items()
                     if isinstance(info, dict) and info.get("rom_id")}

    def _found(anim, src):
        out = set()
        for fr in reconstructed[anim]["frames"]:
            for b in fr["boxes"]:
                if b["type"] == src:
                    out.add((b["left"], b["width"], b["bottom"], b["height"]))
        return out

    report = {}
    for state, supp in seed.items():
        if state.startswith("_"):
            continue
        seed_boxes = {(b["left"], b["width"], b["bottom"], b["height"])
                      for b in supp.get("boxes", [])}
        candidates = {st: a for st, a in state_to_anim.items()
                      if st == state or st.startswith(state + ":")}
        entry = {"seed": sorted(seed_boxes), "candidates": {}}
        for st, anim in sorted(candidates.items()):
            c = {"anim": anim, "captured": anim in reconstructed, "matches": {}}
            if anim in reconstructed:
                for src in ("vulnerability", "ext_vulnerability"):
                    found = _found(anim, src)
                    c["matches"][src] = sorted(seed_boxes & found)
                    c[f"{src}_all"] = sorted(found)
            entry["candidates"][st] = c
        entry["verdict"] = next((f"{st} ({c['anim']}) ext_vulnerability == seed"
                                 for st, c in entry["candidates"].items()
                                 if c["matches"].get("ext_vulnerability")), "no match in capture")
        report[state] = entry
    return report


# ---- combat: ROM-exact damage / stun / hitstop / hitstun -------------------

PARRY_MARKER = 0xFFF1          # received_connection_marker value for a parry
CONNECT_SETTLE_FRAMES = 12     # window after a connect in which life/stun settle
MAX_STUN_FRAMES = 240          # safety cap when the defender never goes idle


def _idle(c: dict, prev: dict) -> bool:
    """3rd_training_lua's is_idle, restricted to what the dump carries: not
    frozen, not busy, recovery not counting down, not in blockstun, can act."""
    return (c["freeze"] == 0 and (c["busy"] & 0xFF) == 0
            and c["recovery"] == prev["recovery"]
            and not (0 < c["blocking_id"] < 5)
            and c["input_cap"] > 0)


def derive_combat(records: List[dict], attacker: str = "c1", defender: str = "c2") -> dict:
    """Per attacking animation id: the connects it produced and what the ROM
    applied for each -- keyed the same way `reconstruct` keys boxes, so the
    converter can attach them to hitboxes.yaml records.

    A connect is detected on the DEFENDER exactly like 3rd_training_lua:
      hit    = total_received_hit_count increased
      block  = received_connection_marker went 0 -> non-0xFFF1 with no hit
      parry  = marker went 0 -> 0xFFF1
    For each: damage = life drop within the settle window (chip on block),
    stun = stun_bar rise, hitstop = the defender's freeze at the connect,
    stun_frames = frames from the connect until the defender is idle again,
    minus the hitstop (i.e. hitstun on hit, blockstun on block).
    """
    out: Dict[str, dict] = {}
    meta = {"vitality_max": 0, "vitality_internal_max": 0, "att_bonus": None, "def_bonus": None,
            "stun_max": None, "connects": 0, "hits": 0, "blocks": 0, "parries": 0}
    n = len(records)
    # The dump's anim_frame is a running cel id, not an index into the move:
    # count the move's frames from the attacker's animation-id change instead,
    # skipping the frames on which the attacker is frozen by hitstop (the anim
    # does not advance then) so a multi-hit move's later windows line up with
    # the framedata timeline. `records` is one contiguous capture (f is dense).
    frame_of, run_of = [0] * n, [0] * n
    start = 0
    for i in range(n + 1):
        a = records[i].get(attacker) if i < n else None
        pa = records[i - 1].get(attacker) if i else None
        if i == n or i == 0 or not a or not pa or a["anim"] != pa["anim"]:
            if i > start:
                rows = [{attacker: records[j].get(attacker)} for j in range(start, i)]
                for j, fi in zip(range(start, i), _frame_indices(rows, attacker)):
                    frame_of[j], run_of[j] = fi, start
            start = i
    # Ordinal of each connect within its run: the k-th connect of a move that
    # landed all of its hits is its k-th hit window. The attacker's own hitstop
    # (hs_me) differs from the defender's, so a later hit's *frame* cannot be
    # pinned from the defender's freeze; the converter uses (hit_index,
    # run_hits) when run_hits equals the move's window count, else the frame.
    hit_index, run_hits = {}, {}
    for i in range(1, n):
        a, d, pd = records[i].get(attacker), records[i].get(defender), records[i - 1].get(defender)
        if a and d and pd and (d["hits_received"] > pd["hits_received"]
                               or (pd["conn_marker"] == 0 and d["conn_marker"] != 0)):
            key = (a["anim"], run_of[i])
            hit_index[i] = run_hits.get(key, 0)
            run_hits[key] = hit_index[i] + 1
    for i in range(1, n):
        a, d = records[i].get(attacker), records[i].get(defender)
        pa, pd = records[i - 1].get(attacker), records[i - 1].get(defender)
        if not (a and d and pa and pd):
            continue
        # life is a byte view of the bar (wraps to 255 on KO/refill); the
        # vitality word is the real scale, capped at the 0xA0 = 160 bar.
        meta["vitality_max"] = min(160, max(meta["vitality_max"], d.get("vitality", d["life"]),
                                            a.get("vitality", a["life"])))
        meta["vitality_internal_max"] = meta["vitality_max"]
        meta["att_bonus"] = a["att_bonus"] or meta["att_bonus"]
        meta["def_bonus"] = d["def_bonus"] or meta["def_bonus"]
        meta["stun_max"] = d["stun_max"] or meta["stun_max"]
        hit = d["hits_received"] > pd["hits_received"]
        marker_rise = pd["conn_marker"] == 0 and d["conn_marker"] != 0
        parry = marker_rise and d["conn_marker"] == PARRY_MARKER and not hit
        block = marker_rise and not parry and not hit
        if not (hit or block or parry):
            continue
        kind = "hit" if hit else ("block" if block else "parry")
        meta["connects"] += 1; meta[kind + "s" if kind != "parry" else "parries"] += 1
        # attacker's move + ROM frame (1-indexed) at the connect
        anim, frame = a["anim"], frame_of[i] + 1
        # Applied damage/stun: the ROM writes dm_vital / dm_piyo on the defender
        # the frame the hit registers (exactly what it will subtract); the
        # life/stun-bar deltas over the settle window are the fallback.
        life_before, stun_before = pd["life"], pd["stun_bar"]
        life_after, stun_after = life_before, stun_before
        for j in range(i, min(n, i + CONNECT_SETTLE_FRAMES)):
            dj = records[j].get(defender)
            if dj:
                life_after = min(life_after, dj["life"]); stun_after = max(stun_after, dj["stun_bar"])
        damage = d["dmg_next"] if d["dmg_next"] else max(0, life_before - life_after)
        stun = d["stun_next"] if d["stun_next"] else max(0, stun_after - stun_before)
        hitstop = max((records[j][defender]["freeze"] for j in range(i, min(n, i + 3)) if records[j].get(defender)), default=0)
        # stun duration: connect -> defender idle again, minus hitstop. If the
        # next connect lands first (a multi-hit string) this sample can't
        # measure it -> None (the follow-up hit's own sample still can).
        # A hit that changes the defender's posture before they are idle again
        # (launched / knocked down: the ROM posture byte leaves its pre-hit
        # value) is a knockdown: the time to idle is then the whole
        # launch + lying-down + wakeup sequence, which is NOT hitstun. It is
        # kept as `down_frames` and stun_frames is left None for that sample.
        stun_frames, knockdown = None, False
        for j in range(i + 1, min(n, i + MAX_STUN_FRAMES)):
            dj, pj = records[j].get(defender), records[j - 1].get(defender)
            if not (dj and pj):
                continue
            if dj["hits_received"] > pj["hits_received"] or (pj["conn_marker"] == 0 and dj["conn_marker"] != 0):
                break
            if dj["posture"] != pd["posture"]:
                knockdown = True
            if _idle(dj, pj):
                stun_frames = (j - i) - hitstop
                break
        sample = {"f": records[i]["f"], "frame": frame, "hit_index": hit_index.get(i, 0),
                  "run_hits": run_hits.get((anim, run_of[i]), 1), "damage": damage, "stun": stun,
                  "hitstop": hitstop, "stun_frames": None if knockdown else stun_frames,
                  "knockdown": knockdown, "down_frames": stun_frames if knockdown else None,
                  "dmg_next": d["dmg_next"],
                  "dm_vital": max((records[j][defender].get("dm_vital", 0) for j in range(i, min(n, i + 3))
                                   if records[j].get(defender)), default=0),
                  "stun_next": d["stun_next"], "posture": d["posture"]}
        out.setdefault(anim, {"hits": [], "blocks": [], "parries": []})[kind + "s" if kind != "parry" else "parries"].append(sample)
    return {"_meta": meta, "moves": out}


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    return xs[len(xs) // 2] if xs else None


def merge_raw(deriveds: List[dict]) -> dict:
    """Union several `derive_combat` outputs (per-session raw samples) into one.
    A move's hit/block/parry samples from every session are concatenated, so
    `summarize_combat` then medians across all of them. Sessions capture mostly
    disjoint moves; where they overlap the extra samples just sharpen the
    median."""
    out = {"_meta": {"hits": 0, "blocks": 0, "parries": 0, "connects": 0,
                     "vitality_max": 0, "stun_max": None, "sessions": len(deriveds)}, "moves": {}}
    for d in deriveds:
        for k in ("hits", "blocks", "parries", "connects"):
            out["_meta"][k] += d["_meta"].get(k, 0)
        out["_meta"]["vitality_max"] = min(160, max(out["_meta"]["vitality_max"], d["_meta"].get("vitality_max", 0)))
        out["_meta"]["stun_max"] = out["_meta"]["stun_max"] or d["_meta"].get("stun_max")
        for anim, rec in d["moves"].items():
            m = out["moves"].setdefault(anim, {"hits": [], "blocks": [], "parries": []})
            for kind in ("hits", "blocks", "parries"):
                m[kind].extend(rec.get(kind, []))
    return out


def summarize_combat(derived: dict) -> dict:
    """Collapse samples into one value per (move, hit frame): median damage /
    stun / hitstop / hitstun (from hits) and blockstun / chip (from blocks)."""
    moves = {}
    for anim, rec in derived["moves"].items():
        # Group by frame; a sample whose frame is unknown (a repaired legacy
        # multi-hit sample) groups by its ordinal instead.
        def _key(s):
            return s["frame"] if s.get("frame") is not None else ("hit", s.get("hit_index", 0))
        by_frame: Dict[object, dict] = {}
        for s in rec["hits"]:
            by_frame.setdefault(_key(s), {"hits": [], "blocks": []})["hits"].append(s)
        for s in rec["blocks"]:
            by_frame.setdefault(_key(s), {"hits": [], "blocks": []})["blocks"].append(s)
        summary = []
        for key in sorted(by_frame, key=lambda k: (isinstance(k, tuple), k if not isinstance(k, tuple) else k[1])):
            e = by_frame[key]
            allsamples = e["hits"] + e["blocks"]
            landed = [s for s in e["hits"] if s["damage"] > 0] or e["hits"]
            summary.append({
                "frame": _median([s.get("frame") for s in allsamples]),
                "hit_index": min((s.get("hit_index", 0) for s in allsamples), default=0),
                "run_hits": max((s.get("run_hits", 1) for s in allsamples), default=1),
                "damage": _median([s["damage"] for s in landed]),
                "stun": _median([s["stun"] for s in landed]),
                "hitstop": _median([s["hitstop"] for s in e["hits"] + e["blocks"]]),
                "hitstun": _median([s["stun_frames"] for s in landed]),
                "blockstun": _median([s["stun_frames"] for s in e["blocks"]]),
                "chip": _median([s["damage"] for s in e["blocks"]]),
                "knockdown": any(s.get("knockdown") for s in e["hits"]),
                "down_frames": _median([s.get("down_frames") for s in e["hits"]]),
                "samples": {"hits": len(e["hits"]), "blocks": len(e["blocks"])},
            })
        moves[anim] = {"windows": summary, "parries": len(rec["parries"])}
    return {"_meta": derived["_meta"], "moves": moves}


def _combat_selftest() -> None:
    """Synthetic: a 3-frame connect on anim 1438 -- hit on frame 2, defender
    frozen 6 frames then in stun for 8 more, then idle."""
    def c(life=160, hits=0, marker=0, freeze=0, recovery=0, busy=0, blocking=0, stun_bar=0, anim="1438", af=0):
        return {"anim": anim, "anim_frame": af, "posture": 0, "pos_x": 0, "life": life, "vitality": 160,
                "dmg_next": 0, "dm_vital": 0, "stun_next": 0, "freeze": freeze, "recovery": recovery,
                "busy": busy, "blocking_id": blocking, "hits_received": hits, "conn_marker": marker,
                "input_cap": 1, "att_bonus": 8, "stun_bonus": 8, "def_bonus": 8, "stun_max": 64,
                "stun_timer": 0, "stun_bar": stun_bar}
    # move-frame counting starts at the anim-id change: 4 startup frames of the
    # attack anim, then the hit on move-frame 5.
    recs = [{"f": 0, "c1": c(anim="0000"), "c2": c()}]
    recs += [{"f": 1 + k, "c1": c(af=k), "c2": c()} for k in range(4)]   # startup 1..4
    recs.append({"f": 5, "c1": c(af=5, freeze=6), "c2": c(hits=1, freeze=6)})
    f = 6
    for k in range(5):      # remaining freeze (5..1)
        recs.append({"f": f, "c1": c(af=6, freeze=5 - k), "c2": c(hits=1, life=150, stun_bar=3, freeze=5 - k, recovery=20, busy=1)}); f += 1
    for k in range(8):      # hitstun counting down (defender busy)
        recs.append({"f": f, "c1": c(af=6 + k), "c2": c(hits=1, life=150, stun_bar=3, recovery=19 - k, busy=1)}); f += 1
    for k in range(2):      # idle again
        recs.append({"f": f, "c1": c(af=20 + k), "c2": c(hits=1, life=150, stun_bar=3, recovery=0)}); f += 1
    d = summarize_combat(derive_combat(recs))
    w = d["moves"]["1438"]["windows"][0]
    assert w["frame"] == 5 and w["damage"] == 10 and w["stun"] == 3 and w["hitstop"] == 6, w
    assert w["hitstun"] == 9, w   # frames from connect to idle, minus hitstop
    assert d["_meta"]["vitality_max"] == 160 and d["_meta"]["hits"] == 1
    print("combat selftest OK:", json.dumps(w))


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

    pc = sub.add_parser("combat", help="JSONL dump(s) -> rom_combat.json (ROM-exact damage/stun/hitstop/hitstun)")
    pc.add_argument("dump", nargs="+", help="one or more capture sessions; samples merge by move")
    pc.add_argument("--out", default="data/characters/akuma/rom_combat.json")
    pc.add_argument("--raw", default=None, help="also write every connect sample to this path (vendor per session)")

    pm2 = sub.add_parser("merge-combat", help="union per-session raw derivations -> rom_combat.json")
    pm2.add_argument("raw", nargs="+", help="raw sample files saved by `combat --raw`")
    pm2.add_argument("--out", default="data/characters/akuma/rom_combat.json")
    sub.add_parser("selftest", help="run the built-in self-test (no emulator)")

    args = p.parse_args(argv)
    if args.cmd == "merge-combat":
        merged = merge_raw([json.loads(Path(r).read_text()) for r in args.raw])
        summary = summarize_combat(merged)
        Path(args.out).write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
        m = summary["_meta"]
        print(f"wrote {args.out}: {len(summary['moves'])} moves from {m['sessions']} sessions, "
              f"{m['hits']} hits / {m['blocks']} blocks / {m['parries']} parries")
        return
    if args.cmd == "combat":
        # Concatenate sessions: each file's frame numbers restart, which breaks
        # a move run at every seam (no false connect -- hits_received/markers
        # reset downward). Samples from all sessions merge per move.
        records = []
        for d in args.dump:
            records.extend(load_jsonl(d))
        derived = derive_combat(records)
        derived["_meta"]["sessions"] = len(args.dump)
        summary = summarize_combat(derived)
        Path(args.out).write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
        if args.raw:
            Path(args.raw).write_text(json.dumps(derived, indent=1, sort_keys=True) + "\n")
        m = summary["_meta"]
        print(f"wrote {args.out}: {len(summary['moves'])} moves, {m['hits']} hits / {m['blocks']} blocks / "
              f"{m['parries']} parries; vitality max {m['vitality_max']}, att/def bonus {m['att_bonus']}/{m['def_bonus']}")
        return
    if args.cmd == "selftest" or args.cmd is None:
        _combat_selftest()
        _selftest(); return
    if args.cmd == "reconstruct":
        mv = reconstruct_moves(load_jsonl(args.dump))
        Path(args.out).write_text(json.dumps(mv, indent=1))
        print(f"{len(mv)} animations -> {args.out}")
    elif args.cmd == "merge":
        mv = reconstruct_moves(load_jsonl(args.dump), attacking_only=True)
        print(merge_into_framedata(mv, args.framedata, args.out, args.vhb_source))
    elif args.cmd == "physics":
        phys = derive_physics(load_jsonl(args.dump))
        Path(args.out).write_text(physics_to_yaml(phys, args.rom_id, args.repo, args.commit))
        print(f"physics -> {args.out}: {json.dumps({k: phys[k] for k in phys if not k.startswith('_')})[:300]}")
    elif args.cmd == "validate":
        mv = reconstruct_moves(load_jsonl(args.dump), attacking_only=True)
        print(json.dumps(validate_vhb(mv, args.names, args.vhb), indent=2))


if __name__ == "__main__":
    main()
