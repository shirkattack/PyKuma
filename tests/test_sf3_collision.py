#!/usr/bin/env python3
"""
Simple test script to verify SF3 collision system integration
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all SF3 collision system components can be imported"""
    try:
        from street_fighter_3rd.systems.sf3_collision import SF3CollisionSystem
        print("✅ SF3CollisionSystem imported successfully")
        
        from street_fighter_3rd.systems.sf3_core import SF3PlayerWork
        print("✅ SF3PlayerWork imported successfully")
        
        from street_fighter_3rd.systems.sf3_hitboxes import SF3HitboxManager
        print("✅ SF3HitboxManager imported successfully")
        
        from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter
        print("✅ SF3CollisionAdapter imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_sf3_collision_system():
    """Test basic SF3CollisionSystem functionality"""
    try:
        from street_fighter_3rd.systems.sf3_collision import SF3CollisionSystem
        
        # Create collision system
        collision_system = SF3CollisionSystem()
        print("✅ SF3CollisionSystem created successfully")
        
        # Test basic methods
        collision_system.update_frame(1)
        collision_system.enable_throw_checking(True)
        collision_system.hit_check_main_process()
        print("✅ SF3CollisionSystem basic methods work")
        
        return True
        
    except Exception as e:
        print(f"❌ SF3CollisionSystem test failed: {e}")
        return False

def test_sf3_adapter():
    """Test SF3CollisionAdapter functionality"""
    try:
        from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter
        
        # Create adapter
        adapter = SF3CollisionAdapter()
        print("✅ SF3CollisionAdapter created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ SF3CollisionAdapter test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🥊 Testing SF3 Collision System Integration")
    print("=" * 50)
    
    success = True
    
    print("\n1. Testing imports...")
    success &= test_imports()
    
    print("\n2. Testing SF3CollisionSystem...")
    success &= test_sf3_collision_system()
    
    print("\n3. Testing SF3CollisionAdapter...")
    success &= test_sf3_adapter()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 All tests passed! SF3 collision system is ready for integration.")
    else:
        print("💥 Some tests failed. Check the errors above.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
