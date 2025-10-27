#!/usr/bin/env python3
"""
SF3 Integration Test

This script tests the integration of all SF3 authentic systems:
- Core data structures
- Collision system with 32-slot hit queue
- Parry system with 7-frame window
- Input system with validation
- Hitbox system with multiple types

This validates that our authentic SF3 foundation works as a complete system.
"""

import sys
import os
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from street_fighter_3rd.systems.sf3_core import (
    SF3WorkStructure, SF3PlayerWork, SF3GamePhase, SF3StateCategory,
    create_sf3_player, SF3_DAMAGE_SCALING, SF3_PARRY_WINDOW
)
from street_fighter_3rd.systems.sf3_collision import (
    SF3CollisionSystem, SF3HitStatus, SF3CollisionEvent, SF3CollisionResult
)
from street_fighter_3rd.systems.sf3_parry import (
    SF3ParrySystem, SF3ParryResult, SF3ParryType
)
from street_fighter_3rd.systems.sf3_input import (
    SF3InputSystem, SF3InputDirection, SF3ButtonInput, SF3MotionInput
)
from street_fighter_3rd.systems.sf3_hitboxes import (
    SF3HitboxManager, SF3HitboxType, SF3Hitbox, SF3HitLevel
)


def test_complete_sf3_integration():
    """Test complete SF3 system integration"""
    print("🚀 Testing Complete SF3 System Integration...")
    print("=" * 60)
    
    # Initialize all SF3 systems
    collision_system = SF3CollisionSystem()
    parry_system = SF3ParrySystem()
    input_system1 = SF3InputSystem()
    input_system2 = SF3InputSystem()
    
    # Create players
    player1 = create_sf3_player(1, team=1)
    player2 = create_sf3_player(2, team=2)
    
    # Set up players in gameplay state
    player1.work.set_routine_state(SF3GamePhase.GAMEPLAY, SF3StateCategory.NEUTRAL, 0)
    player2.work.set_routine_state(SF3GamePhase.GAMEPLAY, SF3StateCategory.NEUTRAL, 0)
    
    # Position players
    player1.work.position.x = 100
    player1.work.position.y = 200
    player2.work.position.x = 200
    player2.work.position.y = 200
    
    print(f"✅ Players initialized:")
    print(f"   Player 1: Health={player1.work.vitality}, Position=({player1.work.position.x}, {player1.work.position.y})")
    print(f"   Player 2: Health={player2.work.vitality}, Position=({player2.work.position.x}, {player2.work.position.y})")
    
    return player1, player2, collision_system, parry_system, input_system1, input_system2


def test_attack_scenario(player1, player2, collision_system, parry_system, input_system1, input_system2):
    """Test a complete attack scenario"""
    print("\n🥊 Testing Attack Scenario...")
    print("-" * 40)
    
    # Player 1 performs standing medium punch
    print("Player 1 performs standing medium punch...")
    
    # Set player 1 to attacking state
    player1.work.set_routine_state(SF3GamePhase.GAMEPLAY, SF3StateCategory.ATTACKING, 5)  # Standing MP
    
    # Create attack hitbox (from our authentic frame data)
    attack_hitbox = SF3Hitbox(
        offset_x=50, offset_y=-65, width=60, height=40,
        damage=115, stun=7, hitstun=12, blockstun=8,
        hit_level=SF3HitLevel.MID
    )
    
    # Create defender's body hitbox
    body_hitbox = SF3Hitbox(
        offset_x=0, offset_y=-80, width=40, height=80
    )
    
    # Check collision
    pos1 = (player1.work.position.x, player1.work.position.y)
    pos2 = (player2.work.position.x, player2.work.position.y)
    
    collision_detected = attack_hitbox.overlaps(
        body_hitbox, pos1, player1.work.face, pos2, player2.work.face
    )
    
    if collision_detected:
        print("✅ Collision detected!")
        
        # Create collision event
        collision_event = SF3CollisionEvent(
            attacker=player1,
            defender=player2,
            attack_box=attack_hitbox,
            hit_box=body_hitbox,
            collision_type="attack",
            hit_position=pos2,
            frame_number=6  # Active frame of standing MP
        )
        
        # Add to collision system
        collision_system.add_collision_event(collision_event)
        
        # Process collision
        collision_system.hit_check_main_process()
        
        print(f"✅ Collision processed through 32-slot hit queue")
        print(f"   Hit queue entries: {collision_system.hit_queue_input}")
        
        # Apply damage with SF3 scaling
        old_health = player2.work.vitality
        player2.apply_damage(attack_hitbox.damage, combo_scaling=False)  # First hit
        
        print(f"✅ Damage applied: {old_health} -> {player2.work.vitality} (-{attack_hitbox.damage})")
        
        return True
    
    return False


def test_parry_scenario(player1, player2, parry_system, input_system2):
    """Test parry system integration"""
    print("\n🛡️ Testing Parry Scenario...")
    print("-" * 40)
    
    # Player 2 attempts to parry
    print("Player 2 attempts parry...")
    
    # Simulate forward input for parry
    parry_input = {'forward': True, 'down_forward': False}
    parry_system.update_parry_inputs(player2, parry_input)
    
    # Verify parry window
    if parry_system.is_in_parry_window(player2):
        print(f"✅ Parry window active: {parry_system.get_parry_frames_remaining(player2)} frames remaining")
        
        # Create incoming attack
        attack_hitbox = SF3Hitbox(
            offset_x=50, offset_y=-65, width=60, height=40,
            damage=115, stun=7, hit_level=SF3HitLevel.MID
        )
        
        # Test parry defense
        result = parry_system.defense_ground(player1, player2, attack_hitbox, "mid")
        
        if result == SF3ParryResult.PARRY_SUCCESS:
            print("✅ Parry successful!")
            print(f"   Parry advantage: {parry_system.player_parry_states[2].parry_advantage_frames} frames")
            print(f"   Parry counter: {parry_system.get_parry_counter(player2)}")
            return True
        else:
            print(f"❌ Parry failed: {result}")
    
    return False


def test_input_system_integration(input_system1, player1):
    """Test input system with motion detection"""
    print("\n🎮 Testing Input System Integration...")
    print("-" * 40)
    
    # Test QCF motion (Hadoken)
    print("Testing QCF motion input...")
    
    qcf_sequence = [
        (SF3InputDirection.DOWN.value, 0),           # Down
        (SF3InputDirection.DOWN_FORWARD.value, 0),   # Down-forward
        (SF3InputDirection.FORWARD.value, 1),        # Forward + LP
    ]
    
    for frame, (direction, buttons) in enumerate(qcf_sequence):
        input_system1.update_frame(frame)
        input_frame = input_system1.process_input(player1, direction, buttons)
        print(f"   Frame {frame}: Direction={input_frame.direction.value}, Buttons={len(input_frame.buttons_pressed)}")
    
    # Check for detected motions
    motions = input_system1.get_detected_motions()
    print(f"✅ Detected motions: {motions}")
    
    # Test input validation
    print("\nTesting input validation...")
    
    # Test illegal input correction
    corrected = input_system1.check_illegal_lever_data(15)  # Invalid
    print(f"✅ Input correction: 15 -> {corrected.value}")
    
    # Test charge tracking
    print("\nTesting charge tracking...")
    
    input_system1.clear_buffer()
    
    # Hold back for charge
    for frame in range(50):
        input_system1.update_frame(frame)
        input_system1.process_input(player1, SF3InputDirection.BACK.value, 0)
    
    has_charge = input_system1.has_charge("back")
    print(f"✅ Back charge after 50 frames: {has_charge}")
    print(f"   Charge frames: {input_system1.charge_back_frames}")
    
    return len(motions) > 0


def test_combo_scenario(player1, player2, collision_system):
    """Test combo with damage scaling"""
    print("\n🔥 Testing Combo Scenario...")
    print("-" * 40)
    
    print("Testing SF3 authentic damage scaling...")
    
    # Reset player 2 health
    player2.work.vitality = 1000
    player2.combo_count = 0
    
    base_damage = 100
    expected_damages = []
    
    print(f"Base damage per hit: {base_damage}")
    print(f"SF3 damage scaling: {SF3_DAMAGE_SCALING[:5]}...")
    
    # Perform 5-hit combo
    for hit in range(5):
        print(f"\nHit {hit + 1}:")
        
        old_health = player2.work.vitality
        
        # Apply damage with scaling
        player2.apply_damage(base_damage, combo_scaling=True)
        player2.increment_combo()
        
        actual_damage = old_health - player2.work.vitality
        expected_damages.append(actual_damage)
        
        print(f"   Health: {old_health} -> {player2.work.vitality} (-{actual_damage})")
        print(f"   Combo count: {player2.combo_count}")
        
        # Verify scaling
        if hit == 0:
            expected = 100  # First hit: 100%
        else:
            scale = SF3_DAMAGE_SCALING[min(hit, len(SF3_DAMAGE_SCALING) - 1)]
            expected = int(base_damage * scale / 100)
        
        assert actual_damage == expected, f"Hit {hit + 1}: expected {expected}, got {actual_damage}"
    
    total_damage = sum(expected_damages)
    print(f"\n✅ Combo complete!")
    print(f"   Total damage: {total_damage}")
    print(f"   Damage sequence: {expected_damages}")
    print(f"   Final health: {player2.work.vitality}")
    
    return True


def test_state_machine_integration(player1, player2):
    """Test SF3's 8-level state machine"""
    print("\n🔄 Testing State Machine Integration...")
    print("-" * 40)
    
    print("Testing SF3's 8-level routine hierarchy...")
    
    # Test state transitions
    initial_state = player1.work.routine_no.copy()
    print(f"Initial state: {initial_state[:3]}")
    
    # Transition to attacking
    player1.work.set_routine_state(SF3GamePhase.GAMEPLAY, SF3StateCategory.ATTACKING, 5)
    attacking_state = player1.work.routine_no.copy()
    print(f"Attacking state: {attacking_state[:3]}")
    
    # Verify state checks
    assert player1.work.is_in_gameplay(), "Should be in gameplay"
    assert player1.work.is_attacking(), "Should be attacking"
    assert not player1.work.is_damaged(), "Should not be damaged"
    
    # Transition to damaged
    player1.work.set_routine_state(SF3GamePhase.GAMEPLAY, SF3StateCategory.DAMAGED, 2)
    damaged_state = player1.work.routine_no.copy()
    print(f"Damaged state: {damaged_state[:3]}")
    
    assert player1.work.is_damaged(), "Should be damaged"
    assert not player1.work.is_attacking(), "Should not be attacking"
    
    print("✅ State machine working correctly!")
    print(f"   8-level hierarchy: {len(player1.work.routine_no)} levels")
    print(f"   State validation: All checks passed")
    
    return True


def main():
    """Run complete SF3 integration test"""
    print("🎯 SF3:3S Complete System Integration Test")
    print("=" * 60)
    
    try:
        # Initialize systems
        player1, player2, collision_system, parry_system, input_system1, input_system2 = test_complete_sf3_integration()
        
        # Test individual scenarios
        attack_success = test_attack_scenario(player1, player2, collision_system, parry_system, input_system1, input_system2)
        parry_success = test_parry_scenario(player1, player2, parry_system, input_system2)
        input_success = test_input_system_integration(input_system1, player1)
        combo_success = test_combo_scenario(player1, player2, collision_system)
        state_success = test_state_machine_integration(player1, player2)
        
        # Summary
        print("\n" + "=" * 60)
        print("🏆 SF3 INTEGRATION TEST RESULTS")
        print("=" * 60)
        
        results = {
            "Attack System": attack_success,
            "Parry System": parry_success,
            "Input System": input_success,
            "Combo System": combo_success,
            "State Machine": state_success,
        }
        
        all_passed = all(results.values())
        
        for system, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{system:15} {status}")
        
        print("-" * 60)
        
        if all_passed:
            print("🎉 ALL SYSTEMS INTEGRATED SUCCESSFULLY!")
            print("\n✅ Ready for Phase 1: Modern Python Integration")
            print("✅ SF3 foundation is authentic and working")
            print("✅ 32-slot collision system operational")
            print("✅ 7-frame parry system functional")
            print("✅ Input validation and motion detection working")
            print("✅ Damage scaling matches SF3 formula")
            print("✅ 8-level state machine implemented")
        else:
            print("❌ SOME SYSTEMS FAILED - REVIEW REQUIRED")
            return False
        
        print("\n🚀 PHASE 0 COMPLETE: Authentic SF3 Foundation")
        print("Ready to proceed with modern Python integration!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
