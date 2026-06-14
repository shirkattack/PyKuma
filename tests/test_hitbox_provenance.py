"""
Provenance tests for the ROM-accurate hitbox pipeline.

These assert the NO-INVENTED-DATA invariant: every box/move carries a provenance
status, a "verified" box cannot exist without real provenance, and the eyeballed
fallbacks are gone.
"""

import pytest
from pydantic import ValidationError

from street_fighter_3rd.data.hitbox_repository import (
    HitboxRepository, Provenance, SourcedBox,
)
from street_fighter_3rd.data.akuma_hitboxes import get_move_frame_data
from street_fighter_3rd.data.enums import CharacterState
from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter

_TIERS = {"verified", "inferred", "community", "pending"}

_MAPPED_STATES = [
    CharacterState.LIGHT_PUNCH,
    CharacterState.MEDIUM_PUNCH,
    CharacterState.HEAVY_PUNCH,
    CharacterState.LIGHT_KICK,
    CharacterState.MEDIUM_KICK,
    CharacterState.HEAVY_KICK,
    CharacterState.CROUCH_HEAVY_KICK,
]


@pytest.fixture(scope="module")
def repo():
    return HitboxRepository()


def test_yaml_loads_with_provenance(repo):
    """(a) Loading succeeds; every move + attack box carries a valid status."""
    moves = list(repo.iter_moves())
    assert moves, "hitboxes.yaml must load at least one move"

    for move in moves:
        assert move.source is not None, f"{move.rom_id} missing source"
        assert move.source.status in _TIERS, f"{move.rom_id} bad source status"
        for frame in move.frames:
            for box in frame.get("attack", []):
                assert box.get("status") in _TIERS, (
                    f"{move.rom_id} attack box missing/bad status: {box}"
                )

    # Base boxes are tagged too.
    for box in repo.get_base_hurtboxes():
        assert box.status in _TIERS
    assert repo.get_pushbox().status in _TIERS
    assert repo.get_throwbox().status in _TIERS


def test_verified_requires_provenance():
    """(b) verified status with empty provenance must fail to construct."""
    # A verified Provenance needs both repo and rom_id.
    with pytest.raises(ValidationError):
        Provenance(status="verified", repo="", rom_id="")
    with pytest.raises(ValidationError):
        Provenance(status="verified", repo="x", rom_id="")

    # A box with no status at all must not load.
    with pytest.raises(ValidationError):
        SourcedBox(offset_x=0, offset_y=0, width=10, height=10, status="")

    # Sanity: a properly-sourced verified box DOES construct.
    ok = Provenance(status="verified", repo="r", rom_id="1438")
    assert ok.status == "verified"


def test_fallback_hitboxes_removed():
    """(c) The eyeballed fallback path is gone for good."""
    assert not hasattr(SF3CollisionAdapter, "_get_fallback_hitboxes")
    assert not hasattr(SF3CollisionAdapter, "_get_yaml_hitbox")


def test_mapped_states_resolve_with_damage():
    """(d) The 7 mapped states resolve with damage > 0."""
    for state in _MAPPED_STATES:
        move = get_move_frame_data(state)
        assert move is not None, f"{state.name} did not resolve"
        assert move.hitboxes, f"{state.name} has no hitboxes"
        assert move.hitboxes[0][1].damage > 0, f"{state.name} has no damage"


def test_pending_report_informational(repo, capsys):
    """(e) pending_report() runs and surfaces inferred/community items."""
    report = repo.pending_report()
    print(report)
    assert "inferred move names" in report
