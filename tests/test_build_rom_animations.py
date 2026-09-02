"""tools/rom_extract/build_rom_animations.py — ROM cel timelines from the frame dumps."""

import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "build_rom_animations", Path(__file__).resolve().parents[1] / "tools" / "rom_extract" / "build_rom_animations.py")
bra = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bra)


def _rec(anim, cel, freeze=0, side="c1"):
    other = "c2" if side == "c1" else "c1"
    return {"f": 0, side: {"anim": anim, "anim_frame": cel, "freeze": freeze},
            other: {"anim": "0000", "anim_frame": 0, "freeze": 0}}


def test_whiffed_run_matching_the_rom_total_is_preferred_over_a_stretched_connect():
    # run 1 connected: frozen frames stretch it; run 2 whiffed: 4 frames = ROM total
    recs = [_rec("1438", 1), _rec("1438", 2, freeze=3), _rec("1438", 2, freeze=2), _rec("1438", 2, freeze=1), _rec("1438", 2), _rec("1438", 3),
            _rec("8800", 9),
            _rec("1438", 1), _rec("1438", 2), _rec("1438", 2), _rec("1438", 3)]
    manifest = {"1": {}, "2": {}, "3": {}}
    doc = bra.build(recs, {k: {"left": 0, "top": 0, "width": 1, "height": 1} for k in manifest},
                    {"1438": {"state": "LIGHT_PUNCH", "variant": None}},
                    framedata={"1438": {"frames": [{}] * 4}}, roles={})
    a = doc["anims"]["1438"]
    assert a["sequence"] == [[1, 1], [2, 2], [3, 1]] and a["total"] == 4 == a["rom_total"]
    assert a["source"]["whiff"] is True and a["complete"] and a["state"] == "LIGHT_PUNCH"


def test_loop_is_cut_to_one_cycle_and_one_shots_at_their_restart():
    assert bra.one_cycle([1, 1, 2, 2, 3, 1, 1, 2, 2, 3, 1, 1]) == [1, 1, 2, 2, 3]
    assert bra.cut_at_restart([5, 6, 6, 7, 5, 6, 6, 7]) == [5, 6, 6, 7]
    assert bra.cut_at_restart([5, 6, 7]) == [5, 6, 7]
    assert bra.cut_at_restart([1, 1, 2, 2, 1, 1, 3, 3]) == [1, 1, 2, 2, 1, 1, 3, 3]   # a bob, not a restart
    recs = [_rec("8800", c) for c in [1, 1, 2, 2, 1, 1, 2, 2, 1]] + [_rec("8ab0", c) for c in [8, 9, 9, 8, 9, 9]]
    doc = bra.build(recs, {str(c): {"left": 0, "top": 0, "width": 1, "height": 1} for c in (1, 2, 8, 9)}, {},
                    roles={"8800": {"role": "stance", "loop": True, "signature": ""},
                           "8ab0": {"role": "dash_forward", "loop": False, "signature": ""}})
    assert doc["anims"]["8800"]["sequence"] == [[1, 2], [2, 2]] and doc["anims"]["8800"]["loop"]
    assert doc["anims"]["8ab0"]["sequence"] == [[8, 1], [9, 2]]


def test_missing_cels_are_reported_and_only_used_cels_are_emitted():
    recs = [_rec("1908", 4), _rec("1908", 5), _rec("1908", 5)]
    doc = bra.build(recs, {"4": {"left": -3, "top": -9, "width": 2, "height": 2}, "77": {"left": 0, "top": 0, "width": 1, "height": 1}},
                    {"1908": {"state": "LIGHT_KICK", "variant": None}}, roles={})
    a = doc["anims"]["1908"]
    assert a["complete"] is False and a["missing_cels"] == [5]
    assert set(doc["cels"]) == {"4"} and doc["cels"]["4"]["left"] == -3


def test_move_names_variants_parse(tmp_path):
    f = tmp_path / "mn.json"
    f.write_text(json.dumps({"_meta": {}, "LIGHT_PUNCH": {"rom_id": "1438"}, "LIGHT_PUNCH:close": {"rom_id": "13a8"}}))
    assert bra.load_move_names(f) == {"1438": {"state": "LIGHT_PUNCH", "variant": None},
                                      "13a8": {"state": "LIGHT_PUNCH", "variant": "close"}}


def test_targets_lua_lists_missing_cels_and_moves_that_were_never_performed():
    """The rip session's shopping list (--targets-lua): every cel an animation
    still needs, named by its move, plus mapped moves with no animation at all.
    dump_cels.lua reads it and ticks it off live (test_dump_cels_targets.py)."""
    doc = {"anims": {
        "1b08": {"state": "HEAVY_KICK", "missing_cels": [22441], "complete": False},
        "1728": {"state": "HEAVY_PUNCH", "variant": "close", "missing_cels": [21904, 21912],
                 "complete": False},
        "a2ec": {"role": "hit_medium", "missing_cels": [21649], "complete": False},
        "8800": {"role": "stance", "missing_cels": [], "complete": True},
    }}
    names = {"1b08": {"state": "HEAVY_KICK", "variant": None},
             "2aa0": {"state": "DIVE_KICK", "variant": None},   # no anim entry -> never performed
             "8800": {"state": "STANCE", "variant": None}}
    out = bra.targets_lua(doc, names)

    assert '[22441] = "HEAVY_KICK (1b08)"' in out
    assert '[21904] = "HEAVY_PUNCH:close (1728)"' in out       # variant is part of the label
    assert '[21649] = "hit_medium (a2ec)"' in out              # role-named clips too
    assert "8800" not in out.split("anims = {")[0]             # a complete clip is not a target
    assert f'[{0x2aa0}] = "DIVE_KICK (2aa0) -- never performed"' in out
    assert f"[{0x1b08}]" not in out.split("anims = {")[1]      # it has an anim: not a missing move
