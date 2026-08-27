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


def _rec(f, anim, boxes, anim_frame=21952):
    # anim_frame is a running cel id in the real dump, NOT a frame index; the
    # ingest counts a move's frames from the start of each contiguous anim run.
    return {"f": f, "pos_x": 100, "pos_y": 0, "flip": 1, "posture": 0,
            "anim": anim, "anim_frame": anim_frame, "boxes": boxes}


ATTACK = {"type": "attack", "left": -60, "width": 32, "bottom": 32, "height": 32}
EXT = {"type": "ext_vulnerability", "left": -54, "width": 22, "bottom": 84, "height": 18}
BODY = {"type": "vulnerability", "left": 0, "width": 50, "bottom": 0, "height": 84}


def _move_records():
    return [
        # run 1: two frames of 1e88
        _rec(1, "1e88", [ATTACK, EXT, BODY]),
        _rec(2, "1e88", []),
        _rec(3, "0000", []),
        # run 2 (a second pass of the same move): frame 0 seen again -> dedupe
        _rec(4, "1e88", [ATTACK], anim_frame=21952),
    ]


def test_reconstruct_groups_and_dedupes():
    mv = ingest.reconstruct_moves(_move_records())
    assert set(mv) == {"1e88", "0000"}
    frames = mv["1e88"]["frames"]
    assert len(frames) == 2  # frame 0 and 1 (dense)
    # frame 0 deduped: attack + ext_vuln + vuln = 3 unique boxes
    assert len(frames[0]["boxes"]) == 3


def test_reconstruct_counts_frames_from_anim_change_not_anim_frame():
    # cel ids run 21952, 21952, 21953 ... in the real dump; the box on the
    # third record of the run must land on index 2 regardless of the cel id.
    recs = [_rec(1, "1908", [], 21952), _rec(2, "1908", [], 21952), _rec(3, "1908", [EXT], 21953)]
    mv = ingest.reconstruct_moves(recs)
    assert len(mv["1908"]["frames"]) == 3
    assert mv["1908"]["frames"][2]["boxes"] and not mv["1908"]["frames"][0]["boxes"]


def test_remap_keeps_attack_and_chosen_vhb_only():
    mv = ingest.reconstruct_moves(_move_records())
    remapped = ingest.remap_box_types(mv, vhb_source="ext_vulnerability")
    boxes = remapped["1e88"]["frames"][0]["boxes"]
    types = sorted(b["type"] for b in boxes)
    # ext_vulnerability -> "vulnerability"; plain "vulnerability" dropped
    assert types == ["attack", "vulnerability"]
    vuln = next(b for b in boxes if b["type"] == "vulnerability")
    assert (vuln["left"], vuln["width"], vuln["bottom"], vuln["height"]) == (-54, 22, 84, 18)


def _framedata_active_at_5():
    # framedata with an active frame (has attack) at index 5, empty frames before, one after
    return {"1e88": {"frames": [{"boxes": []} for _ in range(5)] + [{"boxes": [dict(ATTACK)]}, {"boxes": []}]}}


def test_merge_only_annotates_active_frames(tmp_path):
    import json
    fpath = tmp_path / "fd.json"
    fpath.write_text(json.dumps(_framedata_active_at_5()))
    # a 7-frame run: ext_vuln on the active frame (index 5) and the recovery frame (index 6)
    recs = [_rec(1 + i, "1e88", []) for i in range(5)]
    recs.append(_rec(6, "1e88", [ATTACK, EXT]))
    recs.append(_rec(7, "1e88", [EXT]))
    mv = ingest.reconstruct_moves(recs)
    out = tmp_path / "out.json"
    summary = ingest.merge_into_framedata(mv, str(fpath), str(out))
    assert summary["vuln_boxes_added"] == 1
    assert summary["annotated"] == ["1e88"] and summary["misaligned"] == []
    assert summary["vuln_frames_dropped_non_active"] == 1   # the recovery-frame v_hb is reported, not silently lost
    enriched = json.loads(out.read_text())
    frame5 = enriched["1e88"]["frames"][5]["boxes"]
    assert any(b["type"] == "vulnerability" for b in frame5)
    assert not enriched["1e88"]["frames"][6]["boxes"]


def test_merge_skips_a_move_whose_attack_boxes_do_not_line_up(tmp_path):
    import json
    fpath = tmp_path / "fd.json"
    fpath.write_text(json.dumps(_framedata_active_at_5()))
    # attack box shows up on index 3 in the capture (frame counting off by 2)
    recs = [_rec(1 + i, "1e88", []) for i in range(3)] + [_rec(4, "1e88", [ATTACK, EXT])]
    mv = ingest.reconstruct_moves(recs)
    out = tmp_path / "out.json"
    summary = ingest.merge_into_framedata(mv, str(fpath), str(out))
    assert summary["misaligned"] == ["1e88"] and summary["vuln_boxes_added"] == 0
    enriched = json.loads(out.read_text())
    assert enriched == _framedata_active_at_5()


def test_reconstruct_does_not_advance_frames_while_frozen_by_hitstop():
    # a connect on index 2 with 3 frames of attacker hitstop: the cel holds for
    # the frozen records and the next cel must land on index 3, not 6
    def frz(f, boxes, freeze):
        r = _rec(f, "1438", boxes)
        r["c1"] = {"freeze": freeze}
        return r
    recs = [frz(1, [], 0), frz(2, [], 0), frz(3, [ATTACK], 3), frz(4, [ATTACK], 2), frz(5, [ATTACK], 1),
            frz(6, [ATTACK], 0), frz(7, [EXT], 0)]
    mv = ingest.reconstruct_moves(recs)
    frames = mv["1438"]["frames"]
    assert len(frames) == 4
    assert [b["type"] for b in frames[2]["boxes"]] == ["attack"] and [b["type"] for b in frames[3]["boxes"]] == ["ext_vulnerability"]


def test_reconstruct_attacking_only_drops_runs_of_the_move_that_never_show_an_attack_box():
    recs = [_rec(1, "84f8", []), _rec(2, "84f8", [EXT]),          # run without any attack box
            _rec(3, "0000", []),
            _rec(4, "84f8", []), _rec(5, "84f8", [ATTACK]),        # the move proper
            _rec(6, "0000", []),
            _rec(7, "8800", [BODY]), _rec(8, "8800", [BODY])]      # idle: no attack anywhere -> kept
    mv = ingest.reconstruct_moves(recs, attacking_only=True)
    assert not any(b["type"] == "ext_vulnerability" for b in mv["84f8"]["frames"][1]["boxes"])
    assert mv["8800"]["frames"][0]["boxes"]
    assert any(b["type"] == "ext_vulnerability" for b in ingest.reconstruct_moves(recs)["84f8"]["frames"][1]["boxes"])


def test_dumps_framedata_matches_the_vendored_layout():
    sample = (
        '{\n  "1e88":{\n    "hit_frames":[{\n        "min":5,\n        "max":9\n      }],\n'
        '    "frames":[{\n        "boxes":[],\n        "movement":[0,0]\n      },{\n'
        '        "boxes":[{\n            "type":"attack",\n            "left":-60\n          }],\n'
        '        "movement":[2,0]\n      }]\n  }\n}'
    )
    assert ingest.dumps_framedata(ingest.loads_framedata(sample)) == sample
    assert ingest.dumps_framedata(ingest.loads_framedata('{"a":[-0,0]}')) == '{\n  "a":[-0,0]\n}'
