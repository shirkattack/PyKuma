"""Extract individual HUD components from the full HUD asset.

This script takes the full HUD mockup and extracts individual components
that can be composited in the game engine for flexible layouts.
"""

from PIL import Image
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_UI = REPO_ROOT / "assets" / "ui"
HUD_FULL = ASSETS_UI / "hud_full.png"

def extract_hud_components():
    """Extract and save individual HUD components."""

    # Load the full HUD image
    hud = Image.open(HUD_FULL)
    width, height = hud.size

    print(f"HUD dimensions: {width}x{height}")

    # Define crop regions based on the HUD layout
    # Format: (left, top, right, bottom)

    components = {
        # Left player portrait frame (including character portrait)
        "portrait_frame_left.png": (0, 180, 200, 480),

        # Right player portrait frame (including character portrait)
        "portrait_frame_right.png": (width - 200, 180, width, 480),

        # Left health bar frame with name label
        "health_bar_left.png": (190, 240, 640, 360),

        # Right health bar frame with name label
        "health_bar_right.png": (width - 640, 240, width - 190, 360),

        # Center timer/round display
        "timer_center.png": (width//2 - 140, 200, width//2 + 140, 420),

        # Left power meter frame
        "power_meter_left.png": (180, 360, 460, 420),

        # Right power meter frame
        "power_meter_right.png": (width - 460, 360, width - 180, 420),

        # 1P badge
        "player_badge_1p.png": (20, 400, 160, 450),

        # 2P badge
        "player_badge_2p.png": (width - 160, 400, width - 20, 450),

        # Full HUD bar (entire top section for simpler integration)
        "hud_bar_full.png": (0, 180, width, 480),
    }

    # Extract and save each component
    for filename, bbox in components.items():
        component = hud.crop(bbox)
        output_path = ASSETS_UI / filename
        component.save(output_path)
        print(f"Saved: {filename} ({component.size[0]}x{component.size[1]})")

    print(f"\nAll components extracted to: {ASSETS_UI}")

if __name__ == "__main__":
    extract_hud_components()
