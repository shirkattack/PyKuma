"""The community tier is GENERATED from the vendored Baston tables.

tools/framedata/baston_to_community.py must reproduce
data/characters/akuma/sf3_authentic_frame_data.yaml exactly (so nobody
hand-edits a number that the next regeneration would silently revert), and
the engine's non-hitbox damage (throws, projectiles, super reach hits) reads
from that yaml.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]


def test_community_yaml_is_regenerated_from_baston():
    r = subprocess.run([sys.executable, "tools/framedata/baston_to_community.py", "--check"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_move_row_carries_provenance_and_one_damage_scale():
    doc = yaml.safe_load((REPO / "data/characters/akuma/sf3_authentic_frame_data.yaml").read_text())
    n = doc["normal_attacks"]
    assert n["standing_heavy_punch"]["damage"] == 180 and "Far Fierce" in n["standing_heavy_punch"]["baston"]
    assert n["standing_light_punch"]["damage"] == 22          # Far Jab 3 x7.5 (was 60: 2.7x too strong)
    assert n["crouching_heavy_kick"]["block_advantage"] == -15  # was -5
    assert n["standing_heavy_punch"]["hit_advantage"] == -4     # was +1
    for section in ("normal_attacks", "special_moves", "super_arts"):
        for key, move in doc[section].items():
            assert "baston" in move, f"{section}.{key} has no provenance line"
    assert doc["super_arts"]["messatsu_gou_shoryu"]["damage"] == 495
    assert "tensho_kaireki_jin" not in doc["super_arts"]


def test_engine_damage_reads_the_community_tier():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init(); pygame.display.set_mode((1, 1))
    from street_fighter_3rd.data.community import community_damage, community_move
    assert community_damage("forward_throw", 0) == 142
    assert community_damage("gohadoken_light", 0) == 128 and community_damage("air_gohadoken", 0) == 75
    assert community_damage("shun_goku_satsu", 0) == 652
    assert community_move("nope") is None and community_damage("nope", 7) == 7
    from street_fighter_3rd.core.projectile import Gohadoken
    from street_fighter_3rd.data.enums import FacingDirection
    p = Gohadoken(0, 0, 5.0, FacingDirection.RIGHT, "light")
    assert p.damage == 128
    pygame.quit()
