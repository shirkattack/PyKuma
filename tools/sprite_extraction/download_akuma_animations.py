"""Download and extract all Akuma animations from justnopoint.com"""

import requests
from bs4 import BeautifulSoup
import os
import re
from PIL import Image
import time
from urllib.parse import urljoin

# Base URL for the GIFs
BASE_GIF_URL = "https://www.justnopoint.com/zweifuss/colorswap.php?pcolorstring=AkumaPalette.bin&pcolornum=7&pname=akuma/"

def fetch_html_content(url):
    """Fetch the HTML content from the Akuma page."""
    print(f"Fetching HTML from {url}...")
    
    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching HTML: {e}")
        return None

def extract_animation_names(html_content):
    """Extract all animation names from javascript:reveal() calls in the HTML."""
    print("Extracting animation names from HTML...")
    
    # Pattern to match javascript:reveal('animation-name')
    pattern = r"javascript:reveal\('([^']+)'\)"
    matches = re.findall(pattern, html_content)
    
    # Remove duplicates and sort
    animation_names = sorted(list(set(matches)))
    
    print(f"Found {len(animation_names)} unique animations:")
    for name in animation_names:
        print(f"  - {name}")
    
    return animation_names

def download_gif(animation_name, output_dir="akuma_gifs"):
    """Download a GIF for the given animation name."""
    # Construct the full GIF URL
    gif_filename = f"{animation_name}.gif"
    gif_url = f"{BASE_GIF_URL}{gif_filename}"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Local file path
    local_path = os.path.join(output_dir, gif_filename)
    
    print(f"Downloading {gif_filename}...")
    
    # Headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(gif_url, headers=headers)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            f.write(response.content)
        
        print(f"  ✓ Downloaded to {local_path}")
        return local_path
        
    except requests.RequestException as e:
        print(f"  ✗ Failed to download {gif_filename}: {e}")
        return None

def extract_gif_frames(gif_path, animation_name, base_output_dir="akuma_animations"):
    """Extract all frames from a GIF to individual PNG files."""
    if not os.path.exists(gif_path):
        print(f"GIF file not found: {gif_path}")
        return
    
    # Create output directory for this animation
    output_dir = os.path.join(base_output_dir, animation_name)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Extracting frames from {animation_name}.gif...")
    
    try:
        img = Image.open(gif_path)
        frame_count = 0
        
        while True:
            try:
                # Save current frame
                frame_filename = f"frame_{frame_count:03d}.png"
                output_path = os.path.join(output_dir, frame_filename)
                
                # Convert to RGBA if needed
                frame = img.convert('RGBA')
                frame.save(output_path, 'PNG')
                
                print(f"  Saved frame {frame_count} as {frame_filename}")
                
                # Move to next frame
                frame_count += 1
                img.seek(frame_count)
                
            except EOFError:
                break
        
        print(f"  ✓ Extracted {frame_count} frames to {output_dir}")
        
    except Exception as e:
        print(f"  ✗ Error extracting frames: {e}")

def main():
    """Main function to download and extract all Akuma animations."""
    # URL of the Akuma page
    akuma_url = "https://www.justnopoint.com/zweifuss/akuma/akuma.htm"
    
    print("=== Akuma Animation Downloader ===\n")
    
    # Step 1: Fetch HTML content
    html_content = fetch_html_content(akuma_url)
    if not html_content:
        print("Failed to fetch HTML content. Exiting.")
        return
    
    # Step 2: Extract animation names
    animation_names = extract_animation_names(html_content)
    if not animation_names:
        print("No animation names found. Exiting.")
        return
    
    print(f"\n=== Downloading {len(animation_names)} animations ===\n")
    
    # Step 3: Download and extract each animation
    successful_downloads = 0
    failed_downloads = 0
    
    for i, animation_name in enumerate(animation_names, 1):
        print(f"[{i}/{len(animation_names)}] Processing {animation_name}...")
        
        # Download the GIF
        gif_path = download_gif(animation_name)
        
        if gif_path:
            # Extract frames from the GIF
            extract_gif_frames(gif_path, animation_name)
            successful_downloads += 1
        else:
            failed_downloads += 1
        
        # Small delay to be respectful to the server
        time.sleep(0.5)
        print()
    
    # Summary
    print("=== Summary ===")
    print(f"Successfully processed: {successful_downloads}")
    print(f"Failed downloads: {failed_downloads}")
    print(f"Total animations: {len(animation_names)}")
    
    if successful_downloads > 0:
        print(f"\nAnimations saved to:")
        print(f"  - GIFs: ./akuma_gifs/")
        print(f"  - Extracted frames: ./akuma_animations/")

if __name__ == "__main__":
    main()
