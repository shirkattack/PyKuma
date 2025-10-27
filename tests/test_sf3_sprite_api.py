#!/usr/bin/env python3
"""
Test SF3SpriteManager API

Quick test to understand the correct API for SF3SpriteManager
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_sf3_sprite_manager():
    """Test SF3SpriteManager API"""
    try:
        print("🧪 Testing SF3SpriteManager API...")
        
        # Import SF3SpriteManager
        from street_fighter_3rd.graphics.sprite_manager import SF3SpriteManager
        print("✅ SF3SpriteManager import successful")
        
        # Create manager
        manager = SF3SpriteManager("tools/sprite_extraction")
        print("✅ SF3SpriteManager creation successful")
        
        # Check available methods
        methods = [method for method in dir(manager) if not method.startswith('_')]
        print(f"📋 Available methods: {methods}")
        
        # Test loading character
        print("\n🎨 Testing character loading...")
        result = manager.load_character("akuma")
        print(f"Load result: {result}")
        
        # Check loaded characters
        print(f"Loaded characters: {manager.loaded_characters}")
        
        # Test getting animations
        print("\n🎭 Testing animation access...")
        animations = manager.get_character_animations("akuma")
        print(f"Available animations: {list(animations.keys()) if animations else 'None'}")
        
        if animations:
            # Test getting specific animation
            stance_anim = manager.get_character_animation("akuma", "stance")
            print(f"Stance animation: {stance_anim}")
            
            if stance_anim and stance_anim.frames:
                print(f"Stance frames: {len(stance_anim.frames)}")
                first_frame = stance_anim.frames[0]
                print(f"First frame: {first_frame}")
                if hasattr(first_frame, 'surface') and first_frame.surface:
                    print(f"Frame surface size: {first_frame.surface.get_size()}")
        
        print("🎉 SF3SpriteManager API test complete!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sf3_sprite_manager()
    if success:
        print("\n🚀 API test PASSED - Ready for integration!")
    else:
        print("\n💥 API test FAILED - Need to check implementation")
