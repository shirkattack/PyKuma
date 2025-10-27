#!/usr/bin/env python3
"""
Test Akuma Integration

Simple test to verify that Akuma can be created with SF3 sprite integration
without crashing.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_akuma_creation():
    """Test creating Akuma with SF3 sprite integration"""
    try:
        print("🧪 Testing Akuma creation with SF3 sprite integration...")
        
        # Import Akuma
        from street_fighter_3rd.characters.akuma import Akuma
        print("✅ Akuma import successful")
        
        # Create Akuma instance
        akuma = Akuma(200, 500, player_number=1)
        print("✅ Akuma creation successful")
        
        # Check sprite system status
        if hasattr(akuma, 'use_sf3_sprites'):
            if akuma.use_sf3_sprites:
                print("✅ Using SF3 sprite system")
            else:
                print("⚠️ Using fallback sprite system")
        else:
            print("⚠️ No sprite system attribute found")
        
        # Test basic methods
        akuma.update(None)
        print("✅ Akuma update successful")
        
        print("🎉 All tests passed! Akuma integration working.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_akuma_creation()
    if success:
        print("\n🚀 Integration test PASSED - Main game should work!")
    else:
        print("\n💥 Integration test FAILED - Need to fix issues")
