#!/usr/bin/env python3
"""
Character Portrait Downloader

Downloads character portraits from justnopoint.com/zweifuss/ for use in
the character selection screen and UI elements.

This complements our existing sprite extraction tools by providing
high-quality character portraits for the selection interface.
"""

import requests
import os
from pathlib import Path
from typing import List, Dict, Optional
import time
from urllib.parse import urljoin, urlparse
import re

class SF3PortraitDownloader:
    """Downloads SF3 character portraits from justnopoint.com"""
    
    def __init__(self, output_dir: str = "character_portraits"):
        self.base_url = "https://www.justnopoint.com/zweifuss/"
        self.output_dir = Path(__file__).parent / output_dir
        self.output_dir.mkdir(exist_ok=True)
        
        # SF3:3S character mapping
        self.sf3_characters = {
            "akuma": "Akuma",
            "alex": "Alex", 
            "chun_li": "Chun-Li",
            "dudley": "Dudley",
            "elena": "Elena",
            "hugo": "Hugo",
            "ibuki": "Ibuki",
            "ken": "Ken",
            "makoto": "Makoto",
            "necro": "Necro",
            "oro": "Oro",
            "q": "Q",
            "remy": "Remy",
            "ryu": "Ryu",
            "sean": "Sean",
            "twelve": "Twelve",
            "urien": "Urien",
            "yang": "Yang",
            "yun": "Yun"
        }
        
        print(f"SF3 Portrait Downloader initialized")
        print(f"Output directory: {self.output_dir}")
    
    def download_character_portrait(self, character_name: str, portrait_type: str = "portrait") -> bool:
        """
        Download portrait for a specific character
        
        Args:
            character_name: Character name (e.g., 'akuma', 'ken')
            portrait_type: Type of portrait ('portrait', 'select', 'vs')
        """
        
        if character_name not in self.sf3_characters:
            print(f"❌ Unknown character: {character_name}")
            return False
        
        display_name = self.sf3_characters[character_name]
        
        # Common portrait filename patterns from justnopoint
        portrait_patterns = [
            f"{character_name}_portrait.png",
            f"{character_name}_select.png", 
            f"{character_name}_vs.png",
            f"{display_name}_portrait.png",
            f"{display_name}_select.png",
            f"{display_name}_vs.png",
            f"{character_name}.png",
            f"{display_name}.png"
        ]
        
        success = False
        
        for pattern in portrait_patterns:
            url = urljoin(self.base_url, pattern)
            
            try:
                print(f"Trying: {url}")
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    # Save the portrait
                    output_file = self.output_dir / f"{character_name}_{portrait_type}.png"
                    
                    with open(output_file, 'wb') as f:
                        f.write(response.content)
                    
                    print(f"✅ Downloaded {character_name} portrait: {output_file}")
                    success = True
                    break
                    
            except Exception as e:
                print(f"⚠️ Failed to download {url}: {e}")
                continue
            
            # Be respectful to the server
            time.sleep(0.5)
        
        if not success:
            print(f"❌ Could not find portrait for {character_name}")
        
        return success
    
    def download_all_portraits(self) -> Dict[str, bool]:
        """Download portraits for all SF3 characters"""
        
        results = {}
        
        print(f"🎨 Downloading portraits for {len(self.sf3_characters)} SF3 characters...")
        
        for character_name in self.sf3_characters.keys():
            print(f"\n📥 Downloading {character_name}...")
            results[character_name] = self.download_character_portrait(character_name)
            
            # Be respectful to the server
            time.sleep(1)
        
        # Summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        print(f"\n🎯 Portrait Download Summary:")
        print(f"   Successful: {successful}/{total}")
        print(f"   Failed: {total - successful}/{total}")
        
        return results
    
    def create_placeholder_portraits(self) -> None:
        """Create placeholder portraits for characters without downloaded ones"""
        
        try:
            import pygame
            pygame.init()
            
            # Portrait dimensions
            portrait_size = (120, 160)
            
            for character_name, display_name in self.sf3_characters.items():
                portrait_file = self.output_dir / f"{character_name}_portrait.png"
                
                if not portrait_file.exists():
                    print(f"Creating placeholder for {character_name}...")
                    
                    # Create colored rectangle as placeholder
                    surface = pygame.Surface(portrait_size)
                    
                    # Character-specific colors
                    colors = {
                        "akuma": (120, 20, 20),    # Dark red
                        "ken": (200, 150, 50),     # Golden
                        "ryu": (80, 80, 120),      # Blue-gray
                        "chun_li": (50, 100, 200), # Blue
                        "alex": (100, 150, 100),   # Green
                    }
                    
                    color = colors.get(character_name, (100, 100, 100))
                    surface.fill(color)
                    
                    # Add character name
                    font = pygame.font.Font(None, 24)
                    text = font.render(display_name, True, (255, 255, 255))
                    text_rect = text.get_rect(center=(portrait_size[0]//2, portrait_size[1]//2))
                    surface.blit(text, text_rect)
                    
                    # Save placeholder
                    pygame.image.save(surface, str(portrait_file))
                    print(f"✅ Created placeholder: {portrait_file}")
            
            pygame.quit()
            
        except ImportError:
            print("⚠️ Pygame not available, skipping placeholder creation")
    
    def list_downloaded_portraits(self) -> List[str]:
        """List all downloaded portrait files"""
        
        portraits = []
        
        for file in self.output_dir.glob("*.png"):
            portraits.append(file.name)
        
        return sorted(portraits)
    
    def get_portrait_path(self, character_name: str) -> Optional[Path]:
        """Get path to character portrait file"""
        
        portrait_file = self.output_dir / f"{character_name}_portrait.png"
        
        if portrait_file.exists():
            return portrait_file
        
        return None


def main():
    """Main function for standalone usage"""
    
    print("🎨 SF3:3S Character Portrait Downloader")
    print("Source: https://www.justnopoint.com/zweifuss/")
    print()
    
    downloader = SF3PortraitDownloader()
    
    # Download portraits for key characters first
    priority_characters = ["akuma", "ken", "ryu", "chun_li", "alex"]
    
    print("📥 Downloading priority characters...")
    for character in priority_characters:
        downloader.download_character_portrait(character)
        time.sleep(1)
    
    # Ask user if they want to download all
    try:
        response = input("\n🤔 Download portraits for all SF3 characters? (y/n): ").lower()
        
        if response in ['y', 'yes']:
            downloader.download_all_portraits()
        else:
            print("Skipping full download")
    
    except KeyboardInterrupt:
        print("\n⏹️ Download cancelled by user")
    
    # Create placeholders for missing portraits
    print("\n🎨 Creating placeholders for missing portraits...")
    downloader.create_placeholder_portraits()
    
    # Show results
    portraits = downloader.list_downloaded_portraits()
    print(f"\n✅ Available portraits ({len(portraits)}):")
    for portrait in portraits:
        print(f"   {portrait}")
    
    print(f"\n🎯 Portraits saved to: {downloader.output_dir}")
    print("🔗 These can now be used in the character selection screen!")


if __name__ == "__main__":
    main()
