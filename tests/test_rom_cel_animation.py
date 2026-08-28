"""ROM cel clips: CelAnimation playback, axis placement, and how Akuma picks
them over the folder clips (data/characters/akuma/rom_animations.json).

The clip registry and the variant resolution are pure functions; the render
test uses a throwaway cel dir so it runs without the (git-ignored) assets.
"""

import json
import os
from pathlib import Path

import pygame
import pytest

from street_fighter_3rd.systems.animation import (
    CelAnimation, CelAnimationFrame, SpriteManager, AnimationController,
    cel_screen_rect, create_cel_animation,
)
from street_fighter_3rd.characters import akuma as akuma_mod
from street_fighter_3rd.characters.akuma import Akuma, rom_clip_names, resolve_variant_anim
from street_fighter_3rd.data.enums import CharacterState, FacingDirection

REPO = Path(__file__).resolve().parents[1]
CELS = {"1": {"left": -39, "top": -108, "width": 80, "height": 128},
        "2": {"left": -30, "top": -100, "width": 60, "height": 120},
        "3": {"left": 0, "top": -50, "width": 40, "height": 50}}


def test_cel_animation_holds_rom_durations_and_loops():
    anim = create_cel_animation("x", [[1, 2], [2, 3]], CELS, loop=True)
    assert isinstance(anim, CelAnimation) and anim.total_frames() == 5
    seen = []
    for _ in range(10):
        seen.append(anim.get_current_frame().cel)
        anim.update()
    assert seen == [1, 1, 2, 2, 2, 1, 1, 2, 2, 2]
    one_shot = create_cel_animation("x", [[1, 1], [3, 1]], CELS, loop=False)
    for _ in range(5):
        one_shot.update()
    assert one_shot.is_complete() and one_shot.get_current_frame().cel == 3


def test_cel_screen_rect_mirrors_about_the_axis():
    f = CelAnimationFrame("x", 1, 1, left=-39, top=-108, width=80, height=128)
    assert cel_screen_rect(f, 400, 500, facing_right=True) == (361, 392)
    # facing left: the mirrored sprite's left edge is x - (left + width) = 400 - 41
    assert cel_screen_rect(f, 400, 500, facing_right=False) == (359, 392)
    # a cel entirely in front of the axis flips to entirely behind it
    g = CelAnimationFrame("x", 2, 1, left=10, top=-20, width=30, height=20)
    assert cel_screen_rect(g, 100, 0, True)[0] == 110 and cel_screen_rect(g, 100, 0, False)[0] == 60


def _doc(**anims):
    return {"anims": anims, "cels": CELS}


def test_rom_clip_names_use_roles_states_and_variants_and_skip_incomplete():
    state_anim = {"LIGHT_PUNCH": "light_punch", "GOSHORYUKEN": "goshoryuken", "MEDIUM_PUNCH": "medium_punch"}
    doc = _doc(
        **{"8800": {"role": "stance", "loop": True, "complete": True, "sequence": [[1, 5]]},
           "8c20": {"role": "crouch_down", "loop": False, "complete": True, "sequence": [[1, 5]]},   # role the engine doesn't play
           "1438": {"state": "LIGHT_PUNCH", "variant": None, "complete": True, "sequence": [[1, 4], [2, 3]]},
           "13a8": {"state": "LIGHT_PUNCH", "variant": "close", "complete": False, "sequence": [[1, 4], [3, 3]],
                    "missing_cels": [9]},
           "84f8": {"state": "GOSHORYUKEN", "variant": "light", "complete": True, "sequence": [[2, 4]]},
           "1598": {"state": "MEDIUM_PUNCH", "variant": "far", "complete": True, "sequence": [[3, 4]]}})
    names = rom_clip_names(doc, state_anim)
    assert set(names) == {"stance", "light_punch", "light_goshoryuken", "far_medium_punch"}
    # a cel missing on disk drops the clip
    names = rom_clip_names(doc, state_anim, cel_exists=lambda c: c != 3)
    assert set(names) == {"stance", "light_punch", "light_goshoryuken"}


def test_resolve_variant_anim_prefers_rom_clips_then_folder_convention():
    rom = {"medium_punch", "far_medium_punch", "light_punch"}
    all_names = rom | {"close_medium_punch", "heavy_punch", "close_heavy_punch"}
    assert resolve_variant_anim("medium_punch", "far", rom, all_names) == "far_medium_punch"
    assert resolve_variant_anim("medium_punch", "close", rom, all_names) == "close_medium_punch"  # folder close clip beats the ROM base
    assert resolve_variant_anim("light_punch", "close", rom, all_names) == "light_punch"     # no close clip anywhere -> base
    assert resolve_variant_anim("heavy_punch", "close", rom, all_names) == "close_heavy_punch"
    assert resolve_variant_anim("heavy_punch", "far", rom, all_names) == "heavy_punch"


@pytest.fixture(scope="module")
def display():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((64, 64))
    yield
    pygame.quit()


def _fake_cels(tmp_path):
    for cel, box in CELS.items():
        surf = pygame.Surface((box["width"], box["height"]), pygame.SRCALPHA)
        surf.fill((255, 0, 0, 255))
        pygame.image.save(surf, str(tmp_path / f"cel_{cel}.png"))


def test_akuma_registers_rom_clips_and_renders_them_on_the_axis(display, tmp_path):
    _fake_cels(tmp_path)
    doc = {"anims": {"8800": {"role": "stance", "loop": True, "complete": True, "sequence": [[1, 5], [2, 5]]},
                     "1438": {"state": "LIGHT_PUNCH", "variant": None, "complete": True, "sequence": [[3, 14]]}},
           "cels": CELS}
    jpath = tmp_path / "rom_animations.json"
    jpath.write_text(json.dumps(doc))
    ak = Akuma(400, 300, 1)
    ak._rom_anim_names = set()
    ak._register_rom_animations(json_path=jpath, cel_dir=str(tmp_path))
    assert {"stance", "light_punch"} <= ak._rom_anim_names
    assert isinstance(ak.animation_controller.animations["stance"], CelAnimation)
    ak.animation_controller.play_animation("stance", force_restart=True)
    info = ak.animation_controller.get_current_frame_info()
    assert info["source"] == "rom_cels/cel_1" and info["axis"] == (-39, -108)
    # render: the cel's top-left lands at (x + left, feet_y + top) facing right ...
    screen = pygame.Surface((1200, 800), pygame.SRCALPHA)
    ak.facing = FacingDirection.RIGHT
    ak.render(screen)
    feet = ak.screen_feet_y()
    assert screen.get_at((int(400 - 39) + 1, int(feet - 108) + 1))[:3] == (255, 0, 0)
    assert screen.get_at((int(400 - 39) - 1, int(feet - 108) + 1))[3] == 0
    # ... and mirrors about the axis facing left
    screen.fill((0, 0, 0, 0))
    ak.facing = FacingDirection.LEFT
    ak.render(screen)
    assert screen.get_at((int(400 - 41) + 1, int(feet - 108) + 1))[:3] == (255, 0, 0)
    assert screen.get_at((int(400 - 41) + 80 + 1, int(feet - 108) + 1))[3] == 0


def test_fit_animation_leaves_a_rom_clip_that_already_matches_the_total(display, tmp_path):
    _fake_cels(tmp_path)
    ak = Akuma(400, 300, 1)
    anim = create_cel_animation(str(tmp_path), [[1, 4], [2, 3], [3, 7]], CELS)
    ak.animation_controller.add_animation("light_punch", anim)
    ak._fit_animation("light_punch", 14)
    assert [f.duration for f in anim.frames] == [4, 3, 7]
    ak._fit_animation("light_punch", 18)         # longer state: the last cel holds the remaining frames
    assert [f.duration for f in anim.frames] == [4, 3, 11]
    ak._fit_animation("light_punch", 5)          # shorter state: cut where the state ends, holds untouched
    assert [f.duration for f in anim.frames] == [4, 1]


def test_real_tables_if_present():
    """When the ripped cels are on this machine, every registered ROM clip's
    cels exist and the attack clips sum to their ROM totals."""
    jpath = REPO / "data/characters/akuma/rom_animations.json"
    cel_dir = REPO / "assets/characters/akuma/rom_cels"
    if not jpath.exists():
        pytest.skip("no rom_animations.json")
    doc = json.loads(jpath.read_text())
    for anim_id, e in doc["anims"].items():
        # grounded attacks: the whiff timeline never exceeds the ROM script
        # (air moves keep animating through the fall past their script)
        if e.get("rom_total") and e["complete"] and e["source"]["whiff"] and not str(e.get("state", "")).startswith("JUMP") \
                and "air" not in str(e.get("variant", "")):
            assert e["total"] <= e["rom_total"], anim_id
        for c, _ in e["sequence"]:
            if e["complete"]:
                assert str(c) in doc["cels"], (anim_id, c)
    if not cel_dir.is_dir():
        pytest.skip("cels not ripped on this machine")
    names = rom_clip_names(doc, {s.name: n for s, n in Akuma._STATE_ANIM.items()},
                           cel_exists=lambda c: (cel_dir / f"cel_{c}.png").exists())
    assert "stance" in names and "light_punch" in names


def test_rom_palette_rule_is_an_exact_pen_substitution(tmp_path, monkeypatch):
    from street_fighter_3rd.graphics import palette as pal
    d = tmp_path / "akuma"; d.mkdir()
    (d / "rom_palettes.json").write_text(json.dumps({"p1": [[0, 0, 0], [10, 20, 30], [1, 2, 3]],
                                                     "p2": [[0, 0, 0], [200, 210, 220], [1, 2, 3]]}))
    monkeypatch.setattr(pal, "_ROM_PALETTES_JSON", tmp_path)
    pal._ROM_RULE_CACHE.clear()
    rule = pal.rom_palette_rule("akuma", 2)
    assert rule((10, 20, 30, 255)) == (200, 210, 220, 255)
    assert rule((1, 2, 3, 255)) == (1, 2, 3, 255)          # same colour in both palettes
    assert rule((99, 99, 99, 255)) == (99, 99, 99, 255)    # not a palette colour: untouched
    assert pal.rom_palette_rule("akuma", 1) is None
    pal._ROM_RULE_CACHE.clear()


def test_rom_nearest_rule_maps_folder_colours_onto_the_rom_p2_palette(tmp_path, monkeypatch):
    from street_fighter_3rd.graphics import palette as pal
    d = tmp_path / "akuma"; d.mkdir()
    # pens: black outline, olive gi (-> white for P2), skin (-> lighter skin), red hair (-> same)
    (d / "rom_palettes.json").write_text(json.dumps({
        "p1": [[0, 0, 0], [57, 57, 24], [238, 172, 98], [255, 49, 16]],
        "p2": [[0, 0, 0], [205, 180, 180], [255, 189, 115], [255, 49, 16]]}))
    monkeypatch.setattr(pal, "_ROM_PALETTES_JSON", tmp_path)
    pal._NEAREST_RULE_CACHE.clear(); pal._ROM_RULE_CACHE.clear()
    rule = pal.rom_nearest_rule("akuma", 2)
    assert rule((230, 165, 95, 255)) == (255, 189, 115, 255)        # near the skin pen -> P2 skin
    assert rule((70, 60, 90, 255)) == (205, 180, 180, 255)          # zweifuss purple gi -> the ROM gi pen's P2 colour
    assert rule((250, 50, 20, 255)) == (255, 49, 16, 255)           # hair stays hair
    assert rule((0, 0, 0, 0)) == (0, 0, 0, 0)                       # transparent untouched
    assert pal.rom_nearest_rule("akuma", 1) is None
    pal._NEAREST_RULE_CACHE.clear(); pal._ROM_RULE_CACHE.clear()


def test_air_fireball_plays_the_air_clip_when_registered(display, tmp_path):
    _fake_cels(tmp_path)
    ak = Akuma(400, 300, 1)
    ak.animation_controller.add_animation("air_gohadoken", create_cel_animation(str(tmp_path), [[1, 4]], CELS))
    ak._rom_anim_names.add("air_gohadoken")
    ak.pending_projectile_air = True
    assert ak.anim_name_for(CharacterState.GOHADOKEN) == "air_gohadoken"
    ak.pending_projectile_air = False
    assert ak.anim_name_for(CharacterState.GOHADOKEN) == "gohadoken"


def test_controller_chains_to_the_next_clip_from_its_entry_cel(display, tmp_path):
    _fake_cels(tmp_path)
    ctl = AnimationController(SpriteManager(str(tmp_path)))
    script = create_cel_animation(str(tmp_path), [[1, 2]], CELS)
    tail = create_cel_animation(str(tmp_path), [[1, 3], [2, 3], [3, 3]], CELS)
    ctl.add_animation("mp_dp", script); ctl.add_animation("lp_dp", tail)
    script.next_name, script.next_start = "lp_dp", 2       # the ROM enters the tail at its 3rd cel
    ctl.play_animation("mp_dp", force_restart=True)
    seen = []
    for _ in range(6):
        seen.append((ctl.current_name, ctl.get_current_frame_info()["cel"]))
        ctl.update()
    assert seen[:2] == [("mp_dp", 1), ("mp_dp", 1)]
    assert seen[2] == ("lp_dp", 3) and ctl.current_name == "lp_dp"   # no held last cel, tail from cel 3
