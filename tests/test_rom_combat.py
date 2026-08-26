"""ROM-exact combat tier: capture -> ingest -> converter -> engine.

No emulator here: a synthetic capture exercises the pipeline end to end.
When a real `data/characters/akuma/rom_combat.json` exists, the last test
cross-checks it against the community (Baston) tier and reports outliers.
"""

import json
import os
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools" / "rom_extract"))
sys.path.insert(0, str(REPO / "tools" / "framedata"))

import ingest                                   # tools/rom_extract/ingest.py
import convert_3rd_training as conv             # tools/framedata/convert_3rd_training.py
from street_fighter_3rd.data.hitbox_repository import HitboxRepository, MoveRecord
from street_fighter_3rd.data.akuma_hitboxes import _hitbox_from_box


def _c(life=160, hits=0, marker=0, freeze=0, recovery=0, busy=0, blocking=0, stun_bar=0, anim="1438", af=0):
    return {"anim": anim, "anim_frame": af, "posture": 0, "pos_x": 0, "life": life, "dmg_next": 0,
            "stun_next": 0, "freeze": freeze, "recovery": recovery, "busy": busy, "blocking_id": blocking,
            "hits_received": hits, "conn_marker": marker, "input_cap": 1, "att_bonus": 8, "stun_bonus": 8,
            "def_bonus": 10, "stun_max": 64, "stun_timer": 0, "stun_bar": stun_bar}


def _connect(records, f0, anim, frame, kind, damage, stun, hitstop, stun_frames):
    """Append one connect: attacker anim/frame; defender frozen `hitstop`,
    then in stun `stun_frames`, then idle."""
    prev = records[-1]["c2"] if records else _c()
    life0, stun0, hits0 = prev["life"], prev["stun_bar"], prev["hits_received"]
    f = f0
    records.append({"f": f, "c1": _c(anim=anim, af=frame - 2), "c2": _c(life=life0, stun_bar=stun0, hits=hits0)}); f += 1
    hits = hits0 + (1 if kind == "hit" else 0)
    marker = 0 if kind == "hit" else (0xFFF1 if kind == "parry" else 0x0101)
    records.append({"f": f, "c1": _c(anim=anim, af=frame - 1, freeze=hitstop),
                    "c2": _c(life=life0, stun_bar=stun0, hits=hits, marker=marker, freeze=hitstop, busy=1)}); f += 1
    life1, stun1 = life0 - damage, stun0 + stun
    for k in range(hitstop - 1, 0, -1):
        records.append({"f": f, "c1": _c(anim=anim, af=frame - 1, freeze=k),
                        "c2": _c(life=life1, stun_bar=stun1, hits=hits, marker=marker, freeze=k, recovery=30, busy=1,
                                 blocking=(2 if kind == "block" else 0))}); f += 1
    for k in range(stun_frames):
        records.append({"f": f, "c1": _c(anim=anim, af=frame + k),
                        "c2": _c(life=life1, stun_bar=stun1, hits=hits, marker=marker, recovery=30 - k - 1, busy=1,
                                 blocking=(2 if kind == "block" else 0))}); f += 1
    for k in range(3):  # idle again
        records.append({"f": f, "c1": _c(anim="0000", af=k),
                        "c2": _c(life=life1, stun_bar=stun1, hits=hits, marker=0, recovery=30 - stun_frames)}); f += 1
    return f


@pytest.fixture
def capture():
    recs = []
    f = _connect(recs, 1, "1438", 5, "hit", damage=4, stun=3, hitstop=6, stun_frames=12)
    f = _connect(recs, f, "1438", 5, "hit", damage=4, stun=3, hitstop=6, stun_frames=12)
    f = _connect(recs, f, "1438", 5, "block", damage=0, stun=0, hitstop=6, stun_frames=10)
    f = _connect(recs, f, "1818", 9, "hit", damage=30, stun=13, hitstop=12, stun_frames=20)   # far fierce
    f = _connect(recs, f, "1b08", 6, "hit", damage=20, stun=12, hitstop=10, stun_frames=18)   # cl.HK window 1
    f = _connect(recs, f, "1b08", 17, "hit", damage=21, stun=11, hitstop=10, stun_frames=18)  # cl.HK window 2
    f = _connect(recs, f, "2008", 7, "parry", damage=0, stun=0, hitstop=6, stun_frames=0)
    return recs


def test_ingest_derives_applied_values(capture):
    d = ingest.derive_combat(capture)
    m = d["_meta"]
    assert (m["hits"], m["blocks"], m["parries"]) == (5, 1, 1) and m["vitality_max"] == 160
    assert m["att_bonus"] == 8 and m["def_bonus"] == 10
    s = ingest.summarize_combat(d)
    lp = s["moves"]["1438"]["windows"][0]
    assert lp == {"frame": 5, "damage": 4, "stun": 3, "hitstop": 6, "hitstun": 12, "blockstun": 10, "chip": 0,
                  "samples": {"hits": 2, "blocks": 1}}
    hk = s["moves"]["1b08"]["windows"]
    assert [w["frame"] for w in hk] == [6, 17] and hk[1]["damage"] == 21
    assert s["moves"]["2008"]["parries"] == 1 and s["moves"]["2008"]["windows"] == []


def test_converter_attaches_rom_tier_per_hit_window(capture):
    s = ingest.summarize_combat(ingest.derive_combat(capture))
    block = conv.rom_combat_block(s["moves"]["1b08"]["windows"], [[6, 8], [16, 20]])
    assert block["status"] == "verified" and block["damage_total"] == 41
    assert [h["window"] for h in block["hits"]] == [0, 1]
    assert block["hits"][0]["hitstun"] == 18 and block["hits"][1]["damage"] == 21
    # a frame just outside a window maps to the nearest one
    near = conv.rom_combat_block([{"frame": 9, "damage": 1, "stun": 0, "hitstop": 0, "hitstun": 0,
                                   "blockstun": None, "chip": None, "samples": {"hits": 1, "blocks": 0}}],
                                 [[6, 8], [16, 20]])
    assert near["hits"][0]["window"] == 0
    assert conv.rom_combat_block([], [[1, 2]]) is None


def _record(rom_combat=None, damage=180):
    return MoveRecord(rom_id="1818", timing={"startup": 8, "active": 5, "recovery": 25, "total": 38},
                      source={"status": "verified", "repo": "x", "commit": "y", "rom_id": "1818"},
                      frames=[{"frame": f, "attack": [{"offset_x": 42, "offset_y": -70, "width": 50, "height": 12,
                                                        "status": "verified", "rom_id": "1818"}]} for f in range(9, 14)],
                      state="HEAVY_PUNCH", hit_windows=[[9, 13]],
                      combat={"damage": damage, "hit_type": "MID", "hit_effect": "NORMAL", "hitstun": 18, "blockstun": 14,
                              "on_hit": -4, "on_block": -6},
                      rom_combat=rom_combat)


def test_engine_prefers_captured_values_over_community():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    rom = {"status": "verified", "damage_total": 30,
           "hits": [{"window": 0, "damage": 30, "stun": 13, "hitstop": 12, "hitstun": 20, "blockstun": 16, "chip": 0}]}
    with_rom = _record(rom)
    hb = _hitbox_from_box(with_rom.attack_boxes_for_frame(9)[0], with_rom, 9)
    assert (hb.damage, hb.hitstun, hb.blockstun) == (30, 20, 16)
    without = _record(None)
    hb2 = _hitbox_from_box(without.attack_boxes_for_frame(9)[0], without, 9)
    assert hb2.damage == 180 and hb2.hitstun == 26 and hb2.blockstun == 24   # community + calibration
    assert with_rom.rom_hit(5)["window"] == 0                                 # uncovered window -> last captured


def test_vitality_scale_comes_from_the_capture(tmp_path):
    doc = {"meta": {"character": "akuma", "rom_combat": {"vitality": 160, "att_bonus": 8, "def_bonus": 10}},
           "base_hurtbox": [], "moves": {}}
    p = tmp_path / "hb.yaml"; p.write_text(yaml.safe_dump(doc))
    repo = HitboxRepository(p)
    assert repo.vitality() == 160 and abs(repo.community_scale() - 160 / 1050) < 1e-9
    empty = tmp_path / "hb2.yaml"; empty.write_text(yaml.safe_dump({"meta": {}, "moves": {}}))
    repo2 = HitboxRepository(empty)
    assert repo2.vitality() is None and repo2.community_scale() == 1.0


def test_live_data_has_no_capture_yet_or_agrees_with_baston():
    """Once a real capture lands, report every move where the captured damage
    ratio to the community damage strays from the pack (a mis-keyed connect)."""
    path = REPO / "data/characters/akuma/rom_combat.json"
    if not path.exists():
        pytest.skip("no ROM combat capture yet (see tools/rom_extract/CAPTURE.md)")
    repo = HitboxRepository.instance()
    ratios = []
    for m in repo.iter_moves():
        if m.rom_combat and m.combat and m.combat.damage:
            ratios.append((m.state or m.rom_id, m.rom_combat["damage_total"] / max(1, m.combat.damage_total or m.combat.damage)))
    assert ratios, "capture present but attached to no mapped move"
    med = sorted(r for _, r in ratios)[len(ratios) // 2]
    outliers = [(k, round(r, 3)) for k, r in ratios if abs(r - med) > 0.5 * med]
    assert not outliers, f"captured/community damage ratio outliers (median {med:.3f}): {outliers}"
