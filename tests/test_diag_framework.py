"""Smoke tests for the new diagnostics framework (replay/montage + scenarios)."""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.scenario import run_scenario, jump_arc, jab_knockback
from tools.diagnostics.harness import render_recorded_clip, build_montage
from tools.diagnostics.compare import compare_timelines


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def test_jump_arc_rises_and_lands():
    tl = run_scenario(jump_arc())
    ys = [fr["players"][0]["pos"][1] for fr in tl]
    apex = min(ys)  # smaller y = higher
    assert apex < ys[0] - 30, "P1 should leave the ground"
    assert tl[-1]["players"][0]["grounded"], "P1 should land by the end"


def test_jab_scenario_runs_and_attacks():
    tl = run_scenario(jab_knockback())
    states = {fr["players"][0]["state"] for fr in tl}
    assert "LIGHT_PUNCH" in states, "P1 should throw the jab"


def test_montage_builds_from_scenario(tmp_path):
    out = str(tmp_path / "m.png")
    run_scenario(jump_arc(), montage_path=out, every=6)
    assert os.path.exists(out) and os.path.getsize(out) > 0


def test_render_recorded_clip_produces_tiles():
    # fabricate a tiny recorded timeline (state playback path)
    frames = [{"frame": i, "players": [
        {"state": "JUMPING", "pos": [300 + i * 5, 344 - i * 8], "facing": "R",
         "health": 1050, "anim": {"animation": "jump_forward", "frame_index": i % 5}},
        {"state": "STANDING", "pos": [560, 344], "facing": "L",
         "health": 1050, "anim": {"animation": "stance", "frame_index": 0}},
    ]} for i in range(6)]
    tiles = render_recorded_clip(frames, every=2)
    assert len(tiles) >= 3 and all("surface" in t for t in tiles)


def _tl(p2pos, p2state="STANDING", health=1050):
    return [{"frame": 0, "players": [
        {"pos": [300, 344], "state": "STANDING", "health": 1050, "hitstun": 0},
        {"pos": p2pos, "state": p2state, "health": health, "hitstun": 0}]}]


def test_compare_matches_within_tolerance():
    assert compare_timelines(_tl([360, 344]), _tl([361, 344]), pos_tol=2.0) == []


def test_compare_flags_position_and_state_diffs():
    diffs = compare_timelines(_tl([360, 344]), _tl([420, 344], p2state="HITSTUN_STANDING"),
                              pos_tol=2.0)
    assert diffs and diffs[0]["player"] == 2
    assert "pos" in diffs[0] and "state" in diffs[0]
