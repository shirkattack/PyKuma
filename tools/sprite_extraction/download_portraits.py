#!/usr/bin/env python3
"""
Quick Portrait Download Script

Downloads character portraits from justnopoint.com for immediate use
in the character selection screen.
"""

import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent / "tools" / "sprite_extraction"))

try:
    from download_character_portraits import SF3PortraitDownloader
    
    print("🎨 Downloading SF3 Character Portraits...")
    print("Source: https://www.justnopoint.com/zweifuss/")
    print()
    
    downloader = SF3PortraitDownloader()
    
    # Download key characters
    key_characters = ["akuma", "ken", "ryu", "chun_li"]
    
    for character in key_characters:
        print(f"📥 Downloading {character}...")
        success = downloader.download_character_portrait(character)
        if not success:
            print(f"⚠️ Could not download {character}, will use placeholder")
    
    # Create placeholders for any missing
    print("\n🎨 Creating placeholders for missing portraits...")
    downloader.create_placeholder_portraits()
    
    # Show results
    portraits = downloader.list_downloaded_portraits()
    print(f"\n✅ Available portraits ({len(portraits)}):")
    for portrait in portraits[:10]:  # Show first 10
        print(f"   {portrait}")
    
    if len(portraits) > 10:
        print(f"   ... and {len(portraits) - 10} more")
    
    print(f"\n🎯 Portraits saved to: {downloader.output_dir}")
    print("🚀 Character selection screen will now use these portraits!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("Creating basic placeholders instead...")
    
    # Fallback: create basic placeholders
    import pygame
    pygame.init()
    
    output_dir = Path("tools/sprite_extraction/character_portraits")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    characters = {
        "akuma": ("Akuma", (120, 20, 20)),
        "ken": ("Ken", (200, 150, 50)),
        "ryu": ("Ryu", (80, 80, 120)),
        "chun_li": ("Chun-Li", (50, 100, 200))
    }
    
    for char_key, (display_name, color) in characters.items():
        portrait_file = output_dir / f"{char_key}_portrait.png"
        
        if not portrait_file.exists():
            surface = pygame.Surface((120, 160))
            surface.fill(color)
            
            font = pygame.font.Font(None, 24)
            text = font.render(display_name, True, (255, 255, 255))
            text_rect = text.get_rect(center=(60, 80))
            surface.blit(text, text_rect)
            
            pygame.image.save(surface, str(portrait_file))
            print(f"✅ Created placeholder: {portrait_file}")
    
    pygame.quit()
    print("🎯 Basic placeholders created!")

print("\n🎮 Ready to test character selection with portraits!")
print("Run: uv run demo_character_expansion.py")
