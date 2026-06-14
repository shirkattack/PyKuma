"""
Tests for the SF3 collision system components and the adapter wiring.
"""

from street_fighter_3rd.systems.sf3_collision import SF3CollisionSystem
from street_fighter_3rd.systems.sf3_core import SF3PlayerWork
from street_fighter_3rd.systems.sf3_hitboxes import SF3HitboxManager
from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter


def test_imports():
    """All SF3 collision system components are importable and constructible."""
    assert SF3CollisionSystem is not None
    assert SF3PlayerWork is not None
    assert SF3HitboxManager is not None
    assert SF3CollisionAdapter is not None

    # Each component must construct without arguments (manager needs a name)
    assert isinstance(SF3CollisionSystem(), SF3CollisionSystem)
    assert isinstance(SF3PlayerWork(), SF3PlayerWork)
    assert isinstance(SF3HitboxManager("test"), SF3HitboxManager)


def test_sf3_collision_system():
    """Basic SF3CollisionSystem methods work and track frame state."""
    collision_system = SF3CollisionSystem()

    collision_system.update_frame(1)
    assert collision_system.current_frame == 1, "update_frame must set the current frame"

    collision_system.enable_throw_checking(True)

    # With no queued collision events, processing must leave the queue empty
    collision_system.hit_check_main_process()
    assert collision_system.hit_queue_input == 0, "hit queue must be empty after processing"


def test_sf3_adapter():
    """SF3CollisionAdapter initializes persistent per-player state."""
    adapter = SF3CollisionAdapter()

    assert adapter.frame_counter == 0
    assert set(adapter.player_works.keys()) == {1, 2}, (
        "adapter must keep persistent player works for both players"
    )
    assert set(adapter.hitbox_managers.keys()) == {1, 2}

    # tick() advances the SF3 core exactly one frame
    adapter.tick()
    assert adapter.frame_counter == 1
    assert adapter.sf3_system.current_frame == 1
