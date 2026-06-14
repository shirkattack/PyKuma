"""Per-move vulnerability (v_hb) hurtbox tests.

The shared base hurtbox comes from the ROM idle state; per-move vulnerability
extensions (a limb that becomes hittable during a move) are seeded from Baston
(vhb_supplement.json) until the ROM extractor backfills them. These assert the
data carries provenance and that the shim layers it on top of the base.
"""

import pytest

from street_fighter_3rd.data.hitbox_repository import HitboxRepository
from street_fighter_3rd.data.akuma_hitboxes import get_akuma_hurtboxes
from street_fighter_3rd.data.enums import CharacterState

_TIERS = {"verified", "baston", "inferred", "community", "pending"}
_SEEDED = ["LIGHT_PUNCH", "LIGHT_KICK", "MEDIUM_KICK"]


@pytest.fixture(scope="module")
def repo():
    return HitboxRepository()


def test_vulnerability_boxes_have_valid_provenance(repo):
    for move in repo.iter_moves():
        for fr in move.frames:
            for raw in fr.get("vulnerability", []):
                assert raw.get("status") in _TIERS, f"{move.rom_id}: bad v_hb status {raw}"
                assert raw.get("width", 0) > 0 and raw.get("height", 0) > 0


def test_seeded_moves_have_vulnerability_on_active_frames(repo):
    for state in _SEEDED:
        move = repo.get_move_by_state(state)
        assert move is not None, f"{state} should be mapped"
        active = move.active_frames()
        assert active, f"{state} should have active frames"
        assert move.vulnerability_boxes_for_frame(active[0]), \
            f"{state} should carry a v_hb extension on its active frames"


def test_hurtboxes_layer_base_plus_vulnerability(repo):
    """Active-frame hurtboxes = base stack + the move's v_hb extension."""
    base = get_akuma_hurtboxes(CharacterState.LIGHT_PUNCH, 0)
    active = repo.get_move_by_state("LIGHT_PUNCH").active_frames()[0]
    layered = get_akuma_hurtboxes(CharacterState.LIGHT_PUNCH, active)
    assert len(layered) > len(base), \
        "active-frame hurtboxes must add the per-move vulnerability box(es)"


def test_frame_zero_is_base_only(repo):
    """frame_number=0 returns the base stack with no per-move extension."""
    base = get_akuma_hurtboxes(CharacterState.LIGHT_PUNCH, 0)
    assert len(base) == len(repo.get_base_hurtboxes())
