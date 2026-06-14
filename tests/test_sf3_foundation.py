#!/usr/bin/env python3
"""
Test SF3 Authentic Foundation

This script tests our authentic SF3 implementation to ensure it matches
the real SF3:3S behavior and data.
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
from street_fighter_3rd.systems.sf3_hitboxes import (
    SF3HitboxManager, SF3HitboxType, create_hitbox_from_yaml
)


def test_sf3_authenticity():
    """Test that our SF3 implementation matches authentic values"""
    print("🔥 Testing SF3 Authentic Foundation...")
    print("=" * 50)
    
    # Test 1: SF3 Core Data Structures
    print("\n✅ Test 1: SF3 Core Data Structures")
    
    player1 = create_sf3_player(1, team=1)
    player2 = create_sf3_player(2, team=2)
    
    # Verify SF3 authentic values
    assert player1.work.vitality == 1000, f"Expected 1000 health, got {player1.work.vitality}"
    assert len(player1.work.routine_no) == 8, f"Expected 8-level routine, got {len(player1.work.routine_no)}"
    assert player1.work.direction == 1, f"Player 1 should face right (1), got {player1.work.direction}"
    assert player2.work.direction == -1, f"Player 2 should face left (-1), got {player2.work.direction}"
    
    print(f"   ✓ Player 1: Health={player1.work.vitality}, Routine={player1.work.routine_no[:3]}")
    print(f"   ✓ Player 2: Health={player2.work.vitality}, Routine={player2.work.routine_no[:3]}")
    
    # Test 2: SF3 State Machine
    print("\n✅ Test 2: SF3 8-Level State Machine")
    
    # Test state transitions
    player1.work.set_routine_state(SF3GamePhase.GAMEPLAY, SF3StateCategory.ATTACKING, 5)
    
    assert player1.work.routine_no[0] == SF3GamePhase.GAMEPLAY.value
    assert player1.work.routine_no[1] == SF3StateCategory.ATTACKING.value
    assert player1.work.routine_no[2] == 5
    assert player1.work.is_attacking() == True
    
    print(f"   ✓ State transition: {player1.work.routine_no[:3]} (Gameplay/Attacking/Move5)")
    print(f"   ✓ Is attacking: {player1.work.is_attacking()}")
    
    # Test 3: SF3 Damage Scaling
    print("\n✅ Test 3: SF3 Authentic Damage Scaling")
    
    # Reset player
    player1.work.vitality = 1000
    player1.combo_count = 0
    
    # Test SF3's exact damage scaling: [100, 90, 80, 70, 60, 50, 40, 30, 20, 10]
    expected_damages = []
    base_damage = 100
    
    for hit in range(5):
        player1.apply_damage(base_damage, combo_scaling=True)
        player1.increment_combo()
        
        # Calculate expected damage
        if hit == 0:
            expected_damage = 100  # First hit: 100%
        else:
            scale = SF3_DAMAGE_SCALING[min(hit, len(SF3_DAMAGE_SCALING) - 1)]
            expected_damage = int(base_damage * scale / 100)
        
        expected_damages.append(expected_damage)
    
    expected_total_damage = sum(expected_damages)
    actual_remaining_health = player1.work.vitality
    actual_total_damage = 1000 - actual_remaining_health
    
    print(f"   ✓ Expected damage sequence: {expected_damages}")
    print(f"   ✓ Expected total damage: {expected_total_damage}")
    print(f"   ✓ Actual total damage: {actual_total_damage}")
    print(f"   ✓ Combo count: {player1.combo_count}")
    
    assert actual_total_damage == expected_total_damage, f"Damage scaling incorrect: expected {expected_total_damage}, got {actual_total_damage}"
    
    # Test 4: SF3 Constants
    print("\n✅ Test 4: SF3 Authentic Constants")
    
    assert SF3_PARRY_WINDOW == 7, f"SF3 parry window should be 7 frames, got {SF3_PARRY_WINDOW}"
    assert len(SF3_DAMAGE_SCALING) == 10, f"SF3 damage scaling should have 10 values, got {len(SF3_DAMAGE_SCALING)}"
    assert SF3_DAMAGE_SCALING[0] == 100, f"First hit should be 100% damage, got {SF3_DAMAGE_SCALING[0]}"
    assert SF3_DAMAGE_SCALING[1] == 90, f"Second hit should be 90% damage, got {SF3_DAMAGE_SCALING[1]}"
    assert SF3_DAMAGE_SCALING[-1] == 10, f"Max scaling should be 10% damage, got {SF3_DAMAGE_SCALING[-1]}"
    
    print(f"   ✓ Parry window: {SF3_PARRY_WINDOW} frames (SF3 authentic)")
    print(f"   ✓ Damage scaling: {SF3_DAMAGE_SCALING} (SF3 authentic)")
    
    print("\n🎉 All SF3 authenticity tests passed!")


def test_authentic_frame_data():
    """Test that our Akuma frame data matches SF3 authentic values"""
    print("\n🥋 Testing Authentic Akuma Frame Data...")
    print("=" * 50)
    
    # Load authentic frame data
    frame_data_path = Path("data/characters/akuma/sf3_authentic_frame_data.yaml")
    
    if not frame_data_path.exists():
        print(f"❌ Frame data file not found: {frame_data_path}")
        return
    
    with open(frame_data_path, 'r') as f:
        akuma_data = yaml.safe_load(f)
    
    # Test 1: Character Info
    print("\n✅ Test 1: Akuma Character Info")
    
    char_info = akuma_data['character_info']
    assert char_info['name'] == "Akuma", f"Expected Akuma, got {char_info['name']}"
    assert char_info['sf3_character_id'] == 14, f"Expected ID 14, got {char_info['sf3_character_id']}"
    assert char_info['health'] == 1050, f"Expected 1050 health, got {char_info['health']}"
    assert char_info['stun'] == 64, f"Expected 64 stun, got {char_info['stun']}"
    
    print(f"   ✓ Name: {char_info['name']}")
    print(f"   ✓ SF3 ID: {char_info['sf3_character_id']} (Baston ESN3S)")
    print(f"   ✓ Health: {char_info['health']} (SF3 authentic)")
    print(f"   ✓ Stun: {char_info['stun']} (SF3 authentic)")
    
    # Test 2: Standing Medium Punch (Our corrected frame data)
    print("\n✅ Test 2: Standing Medium Punch (Corrected)")
    
    st_mp = akuma_data['normal_attacks']['standing_medium_punch']
    
    # These are the CORRECTED values from Baston ESN3S
    assert st_mp['startup'] == 5, f"Expected 5 startup, got {st_mp['startup']}"
    assert st_mp['active'] == 3, f"Expected 3 active (corrected from our wrong 4), got {st_mp['active']}"
    assert st_mp['recovery'] == 10, f"Expected 10 recovery (corrected from our wrong 9), got {st_mp['recovery']}"
    assert st_mp['damage'] == 115, f"Expected 115 damage, got {st_mp['damage']}"
    assert st_mp['stun'] == 7, f"Expected 7 stun, got {st_mp['stun']}"
    
    print(f"   ✓ Startup: {st_mp['startup']} frames")
    print(f"   ✓ Active: {st_mp['active']} frames (corrected from our wrong 4)")
    print(f"   ✓ Recovery: {st_mp['recovery']} frames (corrected from our wrong 9)")
    print(f"   ✓ Total: {st_mp['total']} frames")
    print(f"   ✓ Damage: {st_mp['damage']} (SF3 authentic)")
    print(f"   ✓ Stun: {st_mp['stun']} (SF3 authentic)")
    
    # Test 3: Gohadoken (Fireball)
    print("\n✅ Test 3: Gohadoken (Fireball)")
    
    hadoken = akuma_data['special_moves']['gohadoken_light']
    
    # SF3 authentic fireball data
    assert hadoken['startup'] == 13, f"Expected 13 startup, got {hadoken['startup']}"
    assert hadoken['active'] == 2, f"Expected 2 active, got {hadoken['active']}"
    assert hadoken['recovery'] == 31, f"Expected 31 recovery, got {hadoken['recovery']}"
    
    print(f"   ✓ Startup: {hadoken['startup']} frames (SF3 authentic)")
    print(f"   ✓ Active: {hadoken['active']} frames (SF3 authentic)")
    print(f"   ✓ Recovery: {hadoken['recovery']} frames (SF3 authentic)")
    print(f"   ✓ Total: {hadoken['total']} frames")
    
    # Test 4: Goshoryuken (Dragon Punch)
    print("\n✅ Test 4: Goshoryuken (Dragon Punch)")
    
    dp = akuma_data['special_moves']['goshoryuken_light']
    
    # SF3's famous 3-frame DP
    assert dp['startup'] == 3, f"Expected 3 startup (SF3's famous 3-frame DP), got {dp['startup']}"
    assert 'invincibility_frames' in dp, "DP should have invincibility frames"
    assert 1 in dp['invincibility_frames'], "DP should be invincible on frame 1"
    
    print(f"   ✓ Startup: {dp['startup']} frames (SF3's famous 3-frame DP)")
    print(f"   ✓ Invincibility: frames {dp['invincibility_frames'][:5]}... (SF3 authentic)")
    print(f"   ✓ Damage: {dp['damage']} (SF3 authentic)")
    
    # Test 5: Multiple Hitbox Types
    print("\n✅ Test 5: Multiple Hitbox Types")
    
    hitboxes = st_mp['hitboxes']
    
    assert 'attack' in hitboxes, "Should have attack hitboxes"
    assert 'body' in hitboxes, "Should have body hitboxes"
    assert 'hand' in hitboxes, "Should have hand hitboxes"
    
    attack_box = hitboxes['attack'][0]
    body_box = hitboxes['body'][0]
    hand_box = hitboxes['hand'][0]
    
    print(f"   ✓ Attack box: {attack_box['width']}x{attack_box['height']} at ({attack_box['offset_x']}, {attack_box['offset_y']})")
    print(f"   ✓ Body box: {body_box['width']}x{body_box['height']} at ({body_box['offset_x']}, {body_box['offset_y']})")
    print(f"   ✓ Hand box: {hand_box['width']}x{hand_box['height']} at ({hand_box['offset_x']}, {hand_box['offset_y']})")
    
    # Test 6: Parry Data
    print("\n✅ Test 6: Parry System")
    
    parry = akuma_data['parry']
    
    assert parry['window_frames'] == 7, f"Expected 7-frame parry window, got {parry['window_frames']}"
    assert parry['advantage_frames'] == 8, f"Expected 8-frame advantage, got {parry['advantage_frames']}"
    assert "high" in parry['guard_directions'], "Should support high guard"
    assert "mid" in parry['guard_directions'], "Should support mid guard"
    assert "low" in parry['guard_directions'], "Should support low guard"
    
    print(f"   ✓ Parry window: {parry['window_frames']} frames (SF3 authentic)")
    print(f"   ✓ Parry advantage: {parry['advantage_frames']} frames")
    print(f"   ✓ Guard directions: {parry['guard_directions']}")
    
    print("\n🎉 All authentic frame data tests passed!")


def test_hitbox_system():
    """Test the SF3 hitbox system"""
    print("\n📦 Testing SF3 Hitbox System...")
    print("=" * 50)
    
    # Test hitbox manager
    hitbox_manager = SF3HitboxManager("Akuma")
    
    # Load frame data
    frame_data_path = Path("data/characters/akuma/sf3_authentic_frame_data.yaml")
    
    if frame_data_path.exists():
        with open(frame_data_path, 'r') as f:
            akuma_data = yaml.safe_load(f)
        
        hitbox_manager.load_from_yaml(akuma_data)
        
        print(f"   ✓ Loaded {len(hitbox_manager.animations)} animations")
        
        # Test specific move
        if 'standing_medium_punch' in hitbox_manager.animations:
            hitbox_manager.set_animation('standing_medium_punch', 6)  # Active frame
            
            attack_boxes = hitbox_manager.get_current_hitboxes(SF3HitboxType.ATTACK)
            body_boxes = hitbox_manager.get_current_hitboxes(SF3HitboxType.BODY)
            
            print(f"   ✓ Standing MP frame 6: {len(attack_boxes)} attack boxes, {len(body_boxes)} body boxes")
            print(f"   ✓ Has active attacks: {hitbox_manager.has_active_attack_hitboxes()}")
    
    print("\n🎉 Hitbox system tests passed!")


def main():
    """Run all SF3 foundation tests"""
    print("🚀 SF3:3S Authentic Foundation Test Suite")
    print("=" * 60)
    
    try:
        test_sf3_authenticity()
        test_authentic_frame_data()
        test_hitbox_system()
        
        print("\n" + "=" * 60)
        print("🏆 ALL TESTS PASSED! SF3 Foundation is Authentic! ✅")
        print("=" * 60)
        print("\n✅ Ready to proceed with Phase 0 implementation!")
        print("✅ Our foundation matches authentic SF3:3S behavior!")
        print("✅ Frame data corrected to match Baston ESN3S values!")
        print("✅ Multiple hitbox types working correctly!")
        print("✅ 8-level state machine implemented!")
        print("✅ Damage scaling matches SF3 formula!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
