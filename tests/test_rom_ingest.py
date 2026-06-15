"""Tests for tools/rom_extract/ingest.py — the ROM-dump ingest (no emulator).

Validates the reshaping logic against synthetic dumper output so the tooling is
trustworthy before the user runs the real capture.
"""

import importlib.util
from pathlib import Path

import pytest

# Load ingest.py (it lives under tools/, not an installed package).
_SPEC = importlib.util.spec_from_file_location(
    "rom_ingest", Path(__file__).resolve().parents[1] / "tools" / "rom_extract" / "ingest.py")
ingest = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ingest)


def _move_records():
    return [
        {"f": 1, "pos_x": 100, "pos_y": 0, "flip": 1, "posture": 0,
         "anim": "1e88", "anim_frame": 0, "boxes": [
             {"type": "attack", "left": -60, "width": 32, "bottom": 32, "height": 32},
             {"type": "ext_vulnerability", "left": -54, "width": 22, "bottom": 84, "height": 18},
             {"type": "vulnerability", "left": 0, "width": 50, "bottom": 0, "height": 84}]},
        {"f": 2, "pos_x": 100, "pos_y": 0, "flip": 1, "posture": 0,
         "anim": "1e88", "anim_frame": 0, "boxes": [  # same frame again -> dedupe
             {"type": "attack", "left": -60, "width": 32, "bottom": 32, "height": 32}]},
        {"f": 3, "pos_x": 100, "pos_y": 0, "flip": 1, "posture": 0,
         "anim": "1e88", "anim_frame": 1, "boxes": []},
    ]


def test_reconstruct_groups_and_dedupes():
    mv = ingest.reconstruct_moves(_move_records())
    assert set(mv) == {"1e88"}
    frames = mv["1e88"]["frames"]
    assert len(frames) == 2  # frame 0 and 1 (dense)
    # frame 0 deduped: attack + ext_vuln + vuln = 3 unique boxes
    assert len(frames[0]["boxes"]) == 3


def test_remap_keeps_attack_and_chosen_vhb_only():
    mv = ingest.reconstruct_moves(_move_records())
    remapped = ingest.remap_box_types(mv, vhb_source="ext_vulnerability")
    boxes = remapped["1e88"]["frames"][0]["boxes"]
    types = sorted(b["type"] for b in boxes)
    # ext_vulnerability -> "vulnerability"; plain "vulnerability" dropped
    assert types == ["attack", "vulnerability"]
    vuln = next(b for b in boxes if b["type"] == "vulnerability")
    assert (vuln["left"], vuln["width"], vuln["bottom"], vuln["height"]) == (-54, 22, 84, 18)


def test_merge_only_annotates_active_frames(tmp_path):
    # framedata with an active frame (has attack) at index 5 and empty frames before
    framedata = {"1e88": {"frames": [{"boxes": []} for _ in range(5)] + [
        {"boxes": [{"type": "attack", "left": -60, "width": 32, "bottom": 32, "height": 32}]}]}}
    fpath = tmp_path / "fd.json"
    fpath.write_text(__import__("json").dumps(framedata))
    # dump puts the ext_vuln on anim_frame 5
    recs = [{"f": 1, "pos_x": 0, "pos_y": 0, "flip": 1, "posture": 0,
             "anim": "1e88", "anim_frame": 5, "boxes": [
                 {"type": "attack", "left": -60, "width": 32, "bottom": 32, "height": 32},
                 {"type": "ext_vulnerability", "left": -54, "width": 22, "bottom": 84, "height": 18}]}]
    mv = ingest.reconstruct_moves(recs)
    out = tmp_path / "out.json"
    summary = ingest.merge_into_framedata(mv, str(fpath), str(out))
    assert summary["vuln_boxes_added"] == 1
    enriched = __import__("json").loads(out.read_text())
    frame5 = enriched["1e88"]["frames"][5]["boxes"]
    assert any(b["type"] == "vulnerability" for b in frame5)


def test_derive_physics_detects_jump_and_baseline():
    recs = []
    yseq = [0, 0, 8, 14, 18, 20, 18, 14, 8, 0, 0]  # symmetric arc, baseline 0
    for i, y in enumerate(yseq):
        recs.append({"f": i, "pos_x": 200 + 2 * i, "pos_y": y, "flip": 1,
                     "posture": 0, "anim": "ffff", "anim_frame": i, "boxes": []})
    phys = ingest.derive_physics(recs)
    assert phys["ground_baseline_y"] == 0
    assert phys["jumps"], "should detect one jump"
    j = phys["jumps"][0]
    assert j["apex_height"] == 20
    assert j["gravity"] is not None


def test_derive_physics_classifies_walk_vs_dash():
    # a slow sustained walk (speed 3, 30 frames) then a fast short dash (speed 9, 8 frames)
    recs = []
    x = 0
    for i in range(30):       # walk
        recs.append({"f": i, "pos_x": x, "pos_y": 0, "anim": "w", "anim_frame": i, "boxes": []})
        x += 3
    for i in range(5):        # neutral gap
        recs.append({"f": 100 + i, "pos_x": x, "pos_y": 0, "anim": "n", "anim_frame": i, "boxes": []})
    for i in range(8):        # dash
        recs.append({"f": 200 + i, "pos_x": x, "pos_y": 0, "anim": "d", "anim_frame": i, "boxes": []})
        x += 9
    phys = ingest.derive_physics(recs)
    assert phys["walk_speed_px_per_frame"] is not None
    assert phys["dashes"], "should detect a dash run"
    assert phys["dashes"][0]["peak_speed"] >= 5
