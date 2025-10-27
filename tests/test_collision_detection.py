#!/usr/bin/env python3
"""
Test Collision Detection

This script tests that our SF3 collision system is working:
1. YAML hitbox loading
2. Hit detection
3. Damage application
4. Combo scaling
5. VFX spawning
"""

import sys
import os
import pygame

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_yaml_hitbox_loading():
    """Test that YAML hitbox data loads correctly"""
    print("🔍 Testing YAML hitbox loading...")
    
    try:
        from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter
        from street_fighter_3rd.characters.akuma import Akuma
        from street_fighter_3rd.data.enums import CharacterState
        from street_fighter_3rd.data.constants import STAGE_FLOOR
        
        # Create test character
        character = Akuma(200, STAGE_FLOOR, player_number=1)
        character._transition_to_state(CharacterState.LIGHT_PUNCH)
        character.current_frame = 2  # Frame 3 (1-indexed) should be active
        
        # Create collision adapter
        adapter = SF3CollisionAdapter()
        
        # Test YAML hitbox loading
        hitboxes = adapter._get_character_hitboxes(character)
        
        if hitboxes:
            hitbox_data, rect = hitboxes[0]
            print(f"✅ YAML hitbox loaded:")
            print(f"   Damage: {hitbox_data.damage}")
            print(f"   Size: {hitbox_data.width}x{hitbox_data.height}")
            print(f"   Position: ({rect.x}, {rect.y})")
            print(f"   Hit type: {hitbox_data.hit_type}")
            return True
        else:
            print("❌ No hitboxes found")
            return False
            
    except Exception as e:
        print(f"❌ YAML hitbox loading failed: {e}")
        return False

def test_collision_detection():
    """Test actual collision detection between two characters"""
    print("\n🥊 Testing collision detection...")
    
    try:
        from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter
        from street_fighter_3rd.characters.akuma import Akuma
        from street_fighter_3rd.systems.vfx import VFXManager
        from street_fighter_3rd.data.enums import CharacterState
        from street_fighter_3rd.data.constants import STAGE_FLOOR
        
        # Create test characters
        attacker = Akuma(200, STAGE_FLOOR, player_number=1)
        defender = Akuma(250, STAGE_FLOOR, player_number=2)  # Close enough to hit
        
        # Set up attack
        attacker._transition_to_state(CharacterState.MEDIUM_PUNCH)
        attacker.current_frame = 4  # Frame 5 should be active (1-indexed)
        
        # Create systems
        adapter = SF3CollisionAdapter()
        vfx_manager = VFXManager()
        
        # Store initial health
        initial_health = defender.health
        
        # Test collision
        hit_occurred = adapter.check_attack_collision(attacker, defender, vfx_manager)
        
        if hit_occurred:
            print(f"✅ Collision detected!")
            print(f"   Defender health: {initial_health} → {defender.health}")
            print(f"   Damage dealt: {initial_health - defender.health}")
            
            # Check combo system
            combo_info = adapter.get_combo_info(2)  # Defender is player 2
            print(f"   Combo count: {combo_info['count']}")
            print(f"   Combo damage: {combo_info['damage']}")
            
            return True
        else:
            print("❌ No collision detected")
            return False
            
    except Exception as e:
        print(f"❌ Collision detection test failed: {e}")
        return False

def test_combo_scaling():
    """Test that combo scaling works correctly"""
    print("\n📊 Testing combo scaling...")
    
    try:
        from street_fighter_3rd.systems.sf3_combo_system import SF3ComboSystem
        
        combo_system = SF3ComboSystem()
        
        # Test multiple hits
        print("   Testing damage scaling sequence:")
        damages = []
        for i in range(5):
            scaled_damage = combo_system.register_hit(1, 2, 100, "normal")
            damages.append(scaled_damage)
            print(f"   Hit {i+1}: 100 → {scaled_damage} ({scaled_damage}%)")
        
        # Verify expected scaling
        expected = [100, 90, 80, 70, 60]
        if damages == expected:
            print("✅ Combo scaling working perfectly!")
            return True
        else:
            print(f"⚠️ Scaling unexpected: got {damages}, expected {expected}")
            return False
            
    except Exception as e:
        print(f"❌ Combo scaling test failed: {e}")
        return False

def test_game_integration():
    """Test that the game runs with collision detection"""
    print("\n🎮 Testing game integration...")
    
    try:
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        
        from street_fighter_3rd.core.game import Game
        
        # Create game
        game = Game(screen)
        
        # Verify SF3 systems are active
        if hasattr(game.collision_system, 'sf3_combo_system'):
            print("✅ Game using SF3CollisionAdapter")
        else:
            print("❌ Game not using SF3CollisionAdapter")
            return False
        
        # Test one frame update
        game.update(1/60)  # 60 FPS
        
        print("✅ Game update successful")
        
        pygame.quit()
        return True
        
    except Exception as e:
        print(f"❌ Game integration test failed: {e}")
        return False

def main():
    """Run collision detection tests"""
    print("🥊 SF3 Collision Detection Test")
    print("=" * 40)
    
    success = True
    
    success &= test_yaml_hitbox_loading()
    success &= test_collision_detection()
    success &= test_combo_scaling()
    success &= test_game_integration()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 ALL COLLISION TESTS PASSED!")
        print("\n✅ Ready for Task 3: Re-enable parry system")
        print("\n🎮 Test in-game:")
        print("   uv run src/street_fighter_3rd/main.py")
        print("   - Use J/K/L for P1 attacks")
        print("   - Use NumPad 4/5/6 for P2 attacks")
        print("   - Watch for hit sparks and combo counter!")
    else:
        print("💥 Some collision tests failed")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
