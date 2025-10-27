"""Akuma character implementation."""

import os
import pygame
from street_fighter_3rd.characters.character import Character
from street_fighter_3rd.data.enums import CharacterState, Button, FacingDirection
from street_fighter_3rd.systems.animation import (
    SpriteManager,
    AnimationController,
    create_simple_animation,
    create_folder_animation
)
from street_fighter_3rd.systems.animation_loader import AnimationLoader, AnimationLoadError

# Import the working sprite system
try:
    from street_fighter_3rd.graphics.sprite_manager import SF3SpriteManager
    SF3_SPRITES_AVAILABLE = True
except ImportError:
    SF3_SPRITES_AVAILABLE = False
from street_fighter_3rd.core.projectile import Gohadoken


class Akuma(Character):
    """Akuma (Gouki) - The Master of the Fist."""

    def __init__(self, x: float, y: float, player_number: int):
        """Initialize Akuma.

        Args:
            x: Starting x position
            y: Starting y position
            player_number: 1 or 2
        """
        super().__init__(x, y, player_number)

        # Akuma-specific stats (from SF3)
        self.health = 145  # Akuma has low health
        self.walk_speed = 3.2  # Slightly faster than average

        # Initialize animation system - use simple sprite loading approach
        self.use_sf3_sprites = False
        self.simple_sprites = {}
        self.animation_timer = 0
        
        # Try to load sprites using simple approach
        try:
            self._load_simple_sprites()
            if self.simple_sprites:
                self.use_sf3_sprites = True
                print(f"✅ Akuma using simple SF3 sprite system")
        except Exception as e:
            print(f"⚠️ Simple sprites failed, using fallback: {e}")
            self.use_sf3_sprites = False
        
        if not self.use_sf3_sprites:
            # Fallback to original system
            sprite_directory = "assets/sprites/akuma/sprite_sheets"
            self.sprite_manager = SpriteManager(sprite_directory)
            self.animation_controller = AnimationController(self.sprite_manager)

        # Set ground offset for consistent positioning
        self.ground_offset = 190  # From YAML configuration
        
        # Per-animation ground offsets for sprites with different layouts
        self.animation_ground_offsets = {
            # Dash animations use different sprite range (19xxx) with different layout
            "dash_forward": 190,   # Set to default
            "dash_backward": 190,  # Set to default
            # Crouch might need adjustment if it's still shifting
            "crouch_hold": 190,    # Keep same as default for now
            "crouch_transition": 190,
        }

        # Load all animations (YAML + hardcoded fallbacks)
        if not self.use_sf3_sprites:
            self._setup_animations()
            # Start with standing idle animation
            self.animation_controller.play_animation("stance")

        # Visual (placeholder - will use sprites later)
        self.color = (128, 0, 128) if player_number == 1 else (75, 0, 130)  # Purple/dark purple
        self.name = "Akuma"

        # Projectile management
        self.projectiles = []  # List of active projectiles
        self.pending_projectile_strength = None  # Store strength for spawning
    
    def _load_simple_sprites(self):
        """Load sprites using simple direct file loading"""
        from pathlib import Path
        import pygame
        
        sprite_base = Path("tools/sprite_extraction/akuma_animations")
        if not sprite_base.exists():
            print(f"⚠️ Sprite directory not found: {sprite_base}")
            return
        
        # Load key animations
        animations_to_load = {
            "akuma-stance": "akuma-stance",
            "akuma-walkf": "akuma-walkf", 
            "akuma-walkb": "akuma-walkb",
            "akuma-jump": "akuma-jump",
            "akuma-crouch": "akuma-crouch",
            "akuma-block-high": "akuma-block-high",
            "akuma-block-crouch": "akuma-block-crouch",
            # Standing attacks
            "akuma-wp": "akuma-wp",
            "akuma-mp": "akuma-mp",
            "akuma-hp": "akuma-hp",
            "akuma-wk": "akuma-wk",
            "akuma-mk": "akuma-mk",
            "akuma-hk": "akuma-hk",
            # Crouching attacks
            "akuma-crouch-wp": "akuma-crouch-wp",
            "akuma-crouch-mp": "akuma-crouch-mp",
            "akuma-crouch-hp": "akuma-crouch-hp",
            "akuma-crouch-wk": "akuma-crouch-wk",
            "akuma-crouch-mk": "akuma-crouch-mk",
            "akuma-crouch-hk": "akuma-crouch-hk",
            # Special moves
            "akuma-fireball": "akuma-fireball",
            "akuma-dp": "akuma-dp",
            "akuma-hurricane": "akuma-hurricane",
            # Dashes
            "akuma-dashf": "akuma-dashf",
            "akuma-dashb": "akuma-dashb",
        }
        
        for anim_name, folder_name in animations_to_load.items():
            folder_path = sprite_base / folder_name
            if folder_path.exists():
                frames = []
                # Load all PNG files in the folder
                for png_file in sorted(folder_path.glob("*.png")):
                    try:
                        surface = pygame.image.load(png_file).convert_alpha()
                        # Scale up for visibility
                        scaled_surface = pygame.transform.scale(surface, (surface.get_width() * 2, surface.get_height() * 2))
                        frames.append(scaled_surface)
                    except Exception as e:
                        print(f"⚠️ Could not load {png_file}: {e}")
                
                if frames:
                    self.simple_sprites[anim_name] = frames
                    print(f"✅ Loaded {anim_name}: {len(frames)} frames")
        
        print(f"🎨 Loaded {len(self.simple_sprites)} Akuma animations")

    def _setup_animations(self):
        """Set up all Akuma animations."""
        # === NEW: Load animations from YAML (proof-of-concept) ===
        print("\n=== Loading animations from YAML ===")
        try:
            loader = AnimationLoader("src/street_fighter_3rd/data/animations.yaml")
            loader.load_character_animations(self, "akuma")
            print("=== YAML loading complete ===\n")
        except AnimationLoadError as e:
            print(f"WARNING: Failed to load YAML animations: {e}")
            print("Falling back to hardcoded animations...")
        except Exception as e:
            print(f"ERROR: Unexpected error loading YAML: {e}")
            print("Falling back to hardcoded animations...")

        # === OLD: Hardcoded animations (keeping for animations not yet in YAML) ===

        # Walk backward (11 frames)
        # Using sprites 18300-18310 from akuma-walkb.gif
        walk_backward_anim = create_simple_animation(
            [18300, 18301, 18302, 18303, 18304, 18305, 18306, 18307, 18308, 18309, 18310],
            frame_duration=3,  # Hold each frame for 3 game frames (smooth walk)
            loop=True
        )
        self.animation_controller.add_animation("walk_backward", walk_backward_anim)

        # Walk backward (11 frames)
        # Using sprites 18300-18310 from akuma-walkb.gif
        walk_backward_anim = create_simple_animation(
            [18300, 18301, 18302, 18303, 18304, 18305, 18306, 18307, 18308, 18309, 18310],
            frame_duration=3,  # Hold each frame for 3 game frames (smooth walk)
            loop=True
        )
        self.animation_controller.add_animation("walk_backward", walk_backward_anim)

        # Standing Light Punch (mapped from akuma-wp GIF)
        # Frame data: 3 startup, 3 active, 6 recovery = 12 total frames
        light_punch_anim = create_simple_animation(
            [18664, 18666, 18667, 18669, 18670, 18669, 18671, 18671, 18672, 18672, 18664, 18664],
            frame_duration=1,  # Each sprite displays for 1 game frame
            loop=False
        )
        self.animation_controller.add_animation("light_punch", light_punch_anim)

        # Standing Medium Punch (sprites 18673-18682)
        # Frame data: 5 startup, 4 active, 9 recovery = 18 total frames
        medium_punch_anim = create_simple_animation(
            [18673, 18673, 18674, 18675, 18676,  # Frames 1-5 (startup)
             18677, 18678, 18679, 18680,          # Frames 6-9 (active)
             18681, 18682, 18682, 18682, 18682,   # Frames 10-14 (recovery)
             18682, 18673, 18673, 18673],         # Frames 15-18 (recovery)
            frame_duration=1,  # Each sprite displays for 1 game frame
            loop=False
        )
        self.animation_controller.add_animation("medium_punch", medium_punch_anim)

        # Standing Light Kick (sprites 18706-18712)
        # Frame data: 4 startup, 4 active, 7 recovery = 15 total frames
        light_kick_anim = create_simple_animation(
            [18706, 18706, 18707, 18708,                # Frames 1-4 (startup)
             18709, 18710, 18711, 18711,                # Frames 5-8 (active)
             18712, 18712, 18712, 18712,                # Frames 9-12 (recovery)
             18706, 18706, 18706],                      # Frames 13-15 (recovery)
            frame_duration=1,
            loop=False
        )
        self.animation_controller.add_animation("light_kick", light_kick_anim)

        # Standing Medium Kick (sprites 18696-18705)
        # Frame data: 5 startup, 5 active, 17 recovery = 27 total frames
        medium_kick_anim = create_simple_animation(
            [18696, 18696, 18697, 18697, 18698,         # Frames 1-5 (startup)
             18698, 18699, 18700, 18700, 18701,         # Frames 6-10 (active)
             18701, 18702, 18702, 18703, 18703,         # Frames 11-15 (recovery)
             18704, 18704, 18705, 18705, 18696,         # Frames 16-20 (recovery)
             18696, 18696, 18696, 18696, 18696,         # Frames 21-25 (recovery)
             18696, 18696],                             # Frames 26-27 (recovery)
            frame_duration=1,  # Each sprite displays for 1 game frame
            loop=False
        )
        self.animation_controller.add_animation("medium_kick", medium_kick_anim)

        # Standing Heavy Kick (sprites 18717-18722)
        # Frame data: 9 startup, 8 active, 25 recovery = 42 total frames
        heavy_kick_anim = create_simple_animation(
            [18717, 18717, 18717, 18717, 18717,         # Frames 1-5 (startup)
             18717, 18717, 18718, 18718,                # Frames 6-9 (startup)
             18718, 18718, 18720, 18720, 18720,         # Frames 10-14 (active)
             18720, 18720, 18720,                       # Frames 15-17 (active)
             18721, 18721, 18721, 18721,                # Frames 18-21 (recovery)
             18722, 18722, 18722, 18722, 18722,         # Frames 22-26 (recovery)
             18722, 18722, 18722, 18722, 18722,         # Frames 27-31 (recovery)
             18722, 18722, 18722, 18717, 18717,         # Frames 32-36 (recovery)
             18717, 18717, 18717, 18717, 18717,         # Frames 37-41 (recovery)
             18717],                                    # Frame 42 (recovery)
            frame_duration=1,
            loop=False
        )
        self.animation_controller.add_animation("heavy_kick", heavy_kick_anim)

        # Standing Heavy Punch / Close s.HP (sprites 18640-18649)
        # Frame data: 4 startup, 4 active, 17 recovery = 25 total frames
        # This is Akuma's signature two-hit uppercut!
        heavy_punch_anim = create_simple_animation(
            [18640, 18640, 18641, 18642,                # Frames 1-4 (startup - both arms)
             18643, 18643, 18644, 18644,                # Frames 5-8 (active - uppercut)
             18645, 18645, 18646, 18646,                # Frames 9-12 (recovery)
             18647, 18647, 18648, 18648,                # Frames 13-16 (recovery)
             18649, 18649, 18649, 18649,                # Frames 17-20 (recovery)
             18640, 18640, 18640, 18640,                # Frames 21-24 (recovery)
             18640],                                    # Frame 25 (recovery)
            frame_duration=1,  # Each sprite displays for 1 game frame
            loop=False
        )
        self.animation_controller.add_animation("heavy_punch", heavy_punch_anim)

        # Jump Up (34 frames) - Vertical jump
        # Sprites 18320-18353
        jump_up_anim = create_simple_animation(
            [18320, 18321, 18322, 18323, 18324, 18325, 18326, 18327, 18328, 18329,
             18330, 18331, 18332, 18333, 18334, 18335, 18336, 18337, 18338, 18339,
             18340, 18341, 18342, 18343, 18344, 18345, 18346, 18347, 18348, 18349,
             18350, 18351, 18352, 18353],
            frame_duration=2,  # Hold each frame for 2 game frames
            loop=False
        )
        self.animation_controller.add_animation("jump_up", jump_up_anim)

        # Jump Forward (37 frames) - Forward jump
        # Sprites 18354-18390
        jump_forward_anim = create_simple_animation(
            [18354, 18355, 18356, 18357, 18358, 18359, 18360, 18361, 18362, 18363,
             18364, 18365, 18366, 18367, 18368, 18369, 18370, 18371, 18372, 18373,
             18374, 18375, 18376, 18377, 18378, 18379, 18380, 18381, 18382, 18383,
             18384, 18385, 18386, 18387, 18388, 18389, 18390],
            frame_duration=2,
            loop=False
        )
        self.animation_controller.add_animation("jump_forward", jump_forward_anim)

        # Jump Backward (38 frames) - Backward jump
        # Sprites 18391-18428
        jump_backward_anim = create_simple_animation(
            [18391, 18392, 18393, 18394, 18395, 18396, 18397, 18398, 18399, 18400,
             18401, 18402, 18403, 18404, 18405, 18406, 18407, 18408, 18409, 18410,
             18411, 18412, 18413, 18414, 18415, 18416, 18417, 18418, 18419, 18420,
             18421, 18422, 18423, 18424, 18425, 18426, 18427, 18428],
            frame_duration=2,
            loop=False
        )
        self.animation_controller.add_animation("jump_backward", jump_backward_anim)

        # Crouching - Transition down (11 frames)
        # Sprites 18429-18439
        crouch_transition_anim = create_simple_animation(
            [18429, 18430, 18431, 18432, 18433, 18434, 18435, 18436, 18437, 18438, 18439],
            frame_duration=2,  # Quick transition
            loop=False
        )
        self.animation_controller.add_animation("crouch_transition", crouch_transition_anim)

        # Crouching - Hold pose (single frame, loops)
        # Just the final crouch frame
        crouch_hold_anim = create_simple_animation(
            [18439],  # Fully crouched pose
            frame_duration=1,
            loop=True  # Loop on this single frame
        )
        self.animation_controller.add_animation("crouch_hold", crouch_hold_anim)

        # Hitstun - Standing (recoil animation when hit by standing punches)
        # Sprites 18450-18455 show authentic standing hit reaction
        hitstun_standing_anim = create_simple_animation(
            [18450, 18451, 18452, 18453, 18454, 18455],  # Standing punch damage reaction
            frame_duration=2,  # Quick reaction for responsive feel
            loop=False
        )
        self.animation_controller.add_animation("hitstun_standing", hitstun_standing_anim)

        # Forward Dash (14 frames) - Double forward tap
        # Sprites 19439-19452
        dash_forward_anim = create_simple_animation(
            [19439, 19440, 19441, 19442, 19443, 19444, 19445, 19446, 19447, 19448,
             19449, 19450, 19451, 19452],
            frame_duration=1,  # Fast animation for dash
            loop=False
        )
        self.animation_controller.add_animation("dash_forward", dash_forward_anim)

        # Backward Dash (9 frames) - Double back tap
        # Sprites 19453-19461
        dash_backward_anim = create_simple_animation(
            [19453, 19454, 19455, 19456, 19457, 19458, 19459, 19460, 19461],
            frame_duration=1,  # Fast animation for dash
            loop=False
        )
        self.animation_controller.add_animation("dash_backward", dash_backward_anim)

        # Crouching attacks using extracted GIF animations
        # Path to extracted animations (from tools/sprite_extraction)
        anim_base_path = "tools/sprite_extraction/akuma_animations"

        # Crouching Light Punch - cr.LP
        # Frame data: 4f startup, 2f active, 5f recovery = 11 total frames (7 frames in GIF)
        crouch_lp_anim = create_folder_animation(
            f"{anim_base_path}/akuma-crouch-wp", 7, frame_duration=2, loop=False
        )
        self.animation_controller.add_animation("crouch_light_punch", crouch_lp_anim)

        # Crouching Medium Punch - cr.MP
        # Frame data: 5f startup, 3f active, 7f recovery = 15 total frames (7 frames in GIF)
        crouch_mp_anim = create_folder_animation(
            f"{anim_base_path}/akuma-crouch-mp", 7, frame_duration=2, loop=False
        )
        self.animation_controller.add_animation("crouch_medium_punch", crouch_mp_anim)

        # Crouching Heavy Punch - cr.HP
        # Frame data: 5f startup, 4f active, 19f recovery = 28 total frames (11 frames in GIF)
        crouch_hp_anim = create_folder_animation(
            f"{anim_base_path}/akuma-crouch-hp", 11, frame_duration=3, loop=False
        )
        self.animation_controller.add_animation("crouch_heavy_punch", crouch_hp_anim)

        # Crouching Light Kick - cr.LK
        # Frame data: 4f startup, 2f active, 6f recovery = 12 total frames (7 frames in GIF)
        crouch_lk_anim = create_folder_animation(
            f"{anim_base_path}/akuma-crouch-wk", 7, frame_duration=2, loop=False
        )
        self.animation_controller.add_animation("crouch_light_kick", crouch_lk_anim)

        # Crouching Medium Kick - cr.MK
        # Frame data: 6f startup, 3f active, 10f recovery = 19 total frames (11 frames in GIF)
        crouch_mk_anim = create_folder_animation(
            f"{anim_base_path}/akuma-crouch-mk", 11, frame_duration=2, loop=False
        )
        self.animation_controller.add_animation("crouch_medium_kick", crouch_mk_anim)

        # Crouching Heavy Kick - cr.HK (Sweep)
        # Frame data: 7f startup, 5f active, 17f recovery = 29 total frames (13 frames in GIF)
        crouch_hk_anim = create_folder_animation(
            f"{anim_base_path}/akuma-crouch-hk", 13, frame_duration=2, loop=False
        )
        self.animation_controller.add_animation("crouch_heavy_kick", crouch_hk_anim)

        # Jumping attacks using extracted GIF animations
        # Jump Light Punch - j.LP
        # Frame data: 4f startup, 5f active = 9 total frames (6 frames in GIF)
        jump_lp_anim = create_folder_animation(
            f"{anim_base_path}/akuma-jump-wp", 6, frame_duration=2, loop=False
        )
        self.animation_controller.add_animation("jump_light_punch", jump_lp_anim)

        # Jump Medium Punch - j.MP
        # Frame data: 5f startup, 6f active = 11 total frames (8 frames in GIF)
        jump_mp_anim = create_folder_animation(
            f"{anim_base_path}/akuma-jump-mp", 8, frame_duration=2, loop=False
        )
        self.animation_controller.add_animation("jump_medium_punch", jump_mp_anim)

        # Jump Heavy Punch - j.HP
        # Frame data: 7f startup, 5f active = 12 total frames (6 frames in GIF)
        jump_hp_anim = create_folder_animation(
            f"{anim_base_path}/akuma-jump-hp", 6, frame_duration=2, loop=False
        )
        self.animation_controller.add_animation("jump_heavy_punch", jump_hp_anim)

        # Jump Light Kick - j.LK
        # Frame data: 4f startup, 8f active = 12 total frames (12 frames in GIF)
        jump_lk_anim = create_folder_animation(
            f"{anim_base_path}/akuma-jump-wk", 12, frame_duration=1, loop=False
        )
        self.animation_controller.add_animation("jump_light_kick", jump_lk_anim)

        # Jump Medium Kick - j.MK
        # Frame data: 6f startup, 6f active = 12 total frames (6 frames in GIF)
        jump_mk_anim = create_folder_animation(
            f"{anim_base_path}/akuma-jump-mk", 6, frame_duration=2, loop=False
        )
        self.animation_controller.add_animation("jump_medium_kick", jump_mk_anim)

        # Jump Heavy Kick - j.HK
        # Frame data: 8f startup, 4f active = 12 total frames (6 frames in GIF)
        jump_hk_anim = create_folder_animation(
            f"{anim_base_path}/akuma-jump-hk", 6, frame_duration=2, loop=False
        )
        self.animation_controller.add_animation("jump_heavy_kick", jump_hk_anim)

        # Goshoryuken (Dragon Punch) - DP+P (40 frames)
        # Frame data: 3f startup, 12f active, 25f recovery = 40 total frames (20 frames in GIF)
        goshoryuken_anim = create_folder_animation(
            f"{anim_base_path}/akuma-dp", 20, frame_duration=2, loop=False
        )
        self.animation_controller.add_animation("goshoryuken", goshoryuken_anim)

        # Tatsumaki Zankukyaku (Hurricane Kick) - QCB+K (46 frames)
        # Frame data: 4f startup, 26f active, 16f recovery = 46 total frames (30 frames in GIF)
        tatsumaki_anim = create_folder_animation(
            f"{anim_base_path}/akuma-hurricane", 30, frame_duration=2, loop=False
        )
        self.animation_controller.add_animation("tatsumaki", tatsumaki_anim)

        # Gohadoken (Fireball) - QCF+P (24 frames)
        # Sprites 19024-19047
        # Frame data: 13 startup, 3 active (projectile spawns), 8 recovery = 24 total frames
        gohadoken_anim = create_simple_animation(
            [19024, 19024, 19025, 19025, 19026, 19027, 19028, 19029, 19030, 19031, 19032, 19033, 19034,  # Frames 1-13 (startup)
             19035, 19036, 19037,  # Frames 14-16 (active - spawn projectile on frame 14)
             19038, 19039, 19040, 19041, 19042, 19043, 19044, 19045],  # Frames 17-24 (recovery)
            frame_duration=1,
            loop=False
        )
        self.animation_controller.add_animation("gohadoken", gohadoken_anim)

    def _check_special_moves(self) -> bool:
        """Check for Akuma's special moves.

        Returns:
            True if a special move was triggered
        """
        if not self.input:
            return False

        # Gohadoken (236P - Quarter Circle Forward + Punch)
        if self.input.check_motion_input("QCF", Button.LIGHT_PUNCH):
            self._execute_gohadoken(Button.LIGHT_PUNCH)
            return True
        elif self.input.check_motion_input("QCF", Button.MEDIUM_PUNCH):
            self._execute_gohadoken(Button.MEDIUM_PUNCH)
            return True
        elif self.input.check_motion_input("QCF", Button.HEAVY_PUNCH):
            self._execute_gohadoken(Button.HEAVY_PUNCH)
            return True

        # Goshoryuken (623P - Dragon Punch + Punch)
        if self.input.check_motion_input("DP", Button.LIGHT_PUNCH):
            self._execute_goshoryuken(Button.LIGHT_PUNCH)
            return True
        elif self.input.check_motion_input("DP", Button.MEDIUM_PUNCH):
            self._execute_goshoryuken(Button.MEDIUM_PUNCH)
            return True
        elif self.input.check_motion_input("DP", Button.HEAVY_PUNCH):
            self._execute_goshoryuken(Button.HEAVY_PUNCH)
            return True

        # Tatsumaki Zankukyaku (214K - Quarter Circle Back + Kick)
        if self.input.check_motion_input("QCB", Button.LIGHT_KICK):
            self._execute_tatsumaki(Button.LIGHT_KICK)
            return True
        elif self.input.check_motion_input("QCB", Button.MEDIUM_KICK):
            self._execute_tatsumaki(Button.MEDIUM_KICK)
            return True
        elif self.input.check_motion_input("QCB", Button.HEAVY_KICK):
            self._execute_tatsumaki(Button.HEAVY_KICK)
            return True

        return False

    def _execute_gohadoken(self, strength: Button):
        """Execute Gohadoken (fireball).

        Args:
            strength: Punch button used (determines speed/damage)
        """
        print(f"GOHADOKEN! ({strength.name})")  # Debug

        # Mark special move executed (for cooldown tracking)
        self.last_special_frame = self.total_frames

        # Map button to strength string
        strength_map = {
            Button.LIGHT_PUNCH: "light",
            Button.MEDIUM_PUNCH: "medium",
            Button.HEAVY_PUNCH: "heavy"
        }
        self.pending_projectile_strength = strength_map.get(strength, "light")

        self._transition_to_state(CharacterState.GOHADOKEN)

    def _execute_goshoryuken(self, strength: Button):
        """Execute Goshoryuken (dragon punch).

        Args:
            strength: Punch button used (determines height/damage)
        """
        print(f"⚡ GOSHORYUKEN! ({strength.name})")  # Debug

        # Mark special move executed (for cooldown tracking)
        self.last_special_frame = self.total_frames

        # Set invincibility frames based on strength
        if strength == Button.LIGHT_PUNCH:
            self.invincibility_frames = [1, 2, 3, 4, 5, 6, 7, 8]  # 8 frames
        elif strength == Button.MEDIUM_PUNCH:
            self.invincibility_frames = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # 10 frames
        else:  # HEAVY_PUNCH
            self.invincibility_frames = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # 12 frames

        # Launch character upward (DP rises into the air)
        self.velocity_y = -18.0  # Strong upward velocity
        self.is_grounded = False

        # Store which strength was used for hitbox generation
        self.dp_strength = strength

        self._transition_to_state(CharacterState.GOSHORYUKEN)

    def _execute_tatsumaki(self, strength: Button):
        """Execute Tatsumaki Zankukyaku (hurricane kick).

        Args:
            strength: Kick button used (determines distance/hits)
        """
        print(f"🌀 TATSUMAKI! ({strength.name})")  # Debug

        # Mark special move executed (for cooldown tracking)
        self.last_special_frame = self.total_frames

        # Set horizontal speed based on strength
        if strength == Button.LIGHT_KICK:
            horizontal_speed = 5.0
            self.tatsu_hits = 3
        elif strength == Button.MEDIUM_KICK:
            horizontal_speed = 6.5
            self.tatsu_hits = 4
        else:  # HEAVY_KICK
            horizontal_speed = 8.0
            self.tatsu_hits = 5

        # Apply horizontal velocity (moves in facing direction)
        direction = 1 if self.facing == FacingDirection.RIGHT else -1
        self.velocity_x = horizontal_speed * direction

        # If in air, this is air tatsumaki (slightly different)
        if not self.is_grounded:
            print("  (AIR VERSION)")
            horizontal_speed *= 0.8  # Air version moves slower
            self.velocity_x = horizontal_speed * direction

        # Store which strength was used for hitbox generation
        self.tatsu_strength = strength
        self.tatsu_hit_count = 0  # Track how many hits have connected

        self._transition_to_state(CharacterState.TATSUMAKI)

    def update(self, opponent: 'Character'):
        """Update Akuma with animation system.

        Args:
            opponent: The opposing character
        """
        # Call parent update FIRST (this updates facing direction)
        super().update(opponent)

        # Update animation system (only for original sprite system)
        if not self.use_sf3_sprites:
            # THEN update animation controller (after facing is correct)
            self.animation_controller.update()

            # Get current animation name for debugging
            anim_name = self.animation_controller.get_current_animation_name()

            # Check if animation completed and return to stance
            # Don't auto-return for states that should hold (crouching, dashes)
            if self.animation_controller.is_animation_complete():
                # Debug: print when animation completes
                if self.state not in [CharacterState.STANDING, CharacterState.CROUCHING,
                                     CharacterState.DASH_FORWARD, CharacterState.DASH_BACKWARD]:
                    print(f"Animation '{anim_name}' complete, returning to standing from {self.state.name}")
                    self._transition_to_state(CharacterState.STANDING)
                    self.animation_controller.play_animation("stance")
                else:
                    print(f"Animation '{anim_name}' complete but holding state {self.state.name}")

        # Update projectiles
        for projectile in self.projectiles:
            projectile.update()

        # Remove inactive projectiles
        self.projectiles = [p for p in self.projectiles if p.active]

    def _transition_to_state(self, new_state: CharacterState):
        """Transition to a new state and play appropriate animation.

        Args:
            new_state: The state to transition to
        """
        # Call parent transition
        super()._transition_to_state(new_state)

        # Play corresponding animation (only for original sprite system)
        if not self.use_sf3_sprites:
            if new_state == CharacterState.STANDING:
                self.animation_controller.play_animation("stance")
            elif new_state == CharacterState.WALKING_FORWARD:
                self.animation_controller.play_animation("walk_forward")
            elif new_state == CharacterState.WALKING_BACKWARD:
                self.animation_controller.play_animation("walk_backward")
            elif new_state == CharacterState.CROUCHING:
                # Go directly to crouch hold (no transition animation in YAML yet)
                self.animation_controller.play_animation("crouch_hold")
            elif new_state == CharacterState.JUMPING:
                # Determine which jump animation to play based on stored jump direction
                # Note: InputDirection is already relative to facing (FORWARD/BACK are converted by input system)
                from street_fighter_3rd.data.enums import InputDirection

                # Jump direction is relative - UP_FORWARD means "jump toward opponent" regardless of which way you face
                if self.jump_direction == InputDirection.UP_FORWARD:
                    self.animation_controller.play_animation("jump_forward", force_restart=True)
                elif self.jump_direction == InputDirection.UP_BACK:
                    self.animation_controller.play_animation("jump_backward", force_restart=True)
                else:  # InputDirection.UP
                    self.animation_controller.play_animation("jump_up", force_restart=True)
            elif new_state == CharacterState.LIGHT_PUNCH:
                self.animation_controller.play_animation("light_punch", force_restart=True)
            elif new_state == CharacterState.MEDIUM_PUNCH:
                self.animation_controller.play_animation("medium_punch", force_restart=True)
            elif new_state == CharacterState.HEAVY_PUNCH:
                self.animation_controller.play_animation("heavy_punch", force_restart=True)
            elif new_state == CharacterState.LIGHT_KICK:
                self.animation_controller.play_animation("light_kick", force_restart=True)
            elif new_state == CharacterState.MEDIUM_KICK:
                self.animation_controller.play_animation("medium_kick", force_restart=True)
            elif new_state == CharacterState.HEAVY_KICK:
                self.animation_controller.play_animation("heavy_kick", force_restart=True)
            elif new_state == CharacterState.HITSTUN_STANDING:
                self.animation_controller.play_animation("hitstun_standing", force_restart=True)
            elif new_state == CharacterState.DASH_FORWARD:
                self.animation_controller.play_animation("dash_forward", force_restart=True)
            elif new_state == CharacterState.DASH_BACKWARD:
                self.animation_controller.play_animation("dash_backward", force_restart=True)
            elif new_state == CharacterState.GOHADOKEN:
                self.animation_controller.play_animation("gohadoken", force_restart=True)
            elif new_state == CharacterState.CROUCH_LIGHT_PUNCH:
                self.animation_controller.play_animation("crouch_light_punch", force_restart=True)
            elif new_state == CharacterState.CROUCH_MEDIUM_PUNCH:
                self.animation_controller.play_animation("crouch_medium_punch", force_restart=True)
            elif new_state == CharacterState.CROUCH_HEAVY_PUNCH:
                self.animation_controller.play_animation("crouch_heavy_punch", force_restart=True)
            elif new_state == CharacterState.CROUCH_LIGHT_KICK:
                self.animation_controller.play_animation("crouch_light_kick", force_restart=True)
            elif new_state == CharacterState.CROUCH_MEDIUM_KICK:
                self.animation_controller.play_animation("crouch_medium_kick", force_restart=True)
            elif new_state == CharacterState.CROUCH_HEAVY_KICK:
                self.animation_controller.play_animation("crouch_heavy_kick", force_restart=True)
            elif new_state == CharacterState.JUMP_LIGHT_PUNCH:
                self.animation_controller.play_animation("jump_light_punch", force_restart=True)
            elif new_state == CharacterState.JUMP_MEDIUM_PUNCH:
                self.animation_controller.play_animation("jump_medium_punch", force_restart=True)
            elif new_state == CharacterState.JUMP_HEAVY_PUNCH:
                self.animation_controller.play_animation("jump_heavy_punch", force_restart=True)
            elif new_state == CharacterState.JUMP_LIGHT_KICK:
                self.animation_controller.play_animation("jump_light_kick", force_restart=True)
            elif new_state == CharacterState.JUMP_MEDIUM_KICK:
                self.animation_controller.play_animation("jump_medium_kick", force_restart=True)
            elif new_state == CharacterState.JUMP_HEAVY_KICK:
                self.animation_controller.play_animation("jump_heavy_kick", force_restart=True)
            elif new_state == CharacterState.GOSHORYUKEN:
                self.animation_controller.play_animation("goshoryuken", force_restart=True)
            elif new_state == CharacterState.TATSUMAKI:
                self.animation_controller.play_animation("tatsumaki", force_restart=True)

    def render(self, screen: pygame.Surface):
        """Render Akuma using animation system.

        Args:
            screen: Pygame surface to render to
        """
        if self.use_sf3_sprites:
            # Use SF3 sprite system
            self._render_sf3_sprites(screen)
        else:
            # Use original sprite system
            self._render_original_sprites(screen)
    
    def _render_sf3_sprites(self, screen: pygame.Surface):
        """Render using simple sprite system."""
        # Map character state to animation name
        animation_name = self._get_sf3_animation_name()
        
        # Get sprite from simple sprite system
        sprite = None
        try:
            if animation_name in self.simple_sprites:
                frames = self.simple_sprites[animation_name]
                if frames:
                    # Simple frame cycling - use frame based on game time
                    frame_index = (self.animation_timer // 4) % len(frames)
                    sprite = frames[frame_index]
        except Exception as e:
            print(f"⚠️ Simple sprite error: {e}")
        
        if sprite:
            # Flip sprite based on facing direction
            # SF3 sprites face RIGHT by default, so flip when facing LEFT
            from street_fighter_3rd.data.enums import FacingDirection
            if self.facing == FacingDirection.LEFT:
                sprite = pygame.transform.flip(sprite, True, False)

            # Position sprite
            sprite_rect = sprite.get_rect()
            sprite_rect.centerx = int(self.x)
            sprite_rect.bottom = int(self.y)

            # Apply hit flash effect
            if self.hitflash_frames > 0:
                flash_sprite = sprite.copy()
                flash_sprite.fill((30, 30, 30), special_flags=pygame.BLEND_RGB_ADD)
                screen.blit(flash_sprite, sprite_rect)
            else:
                screen.blit(sprite, sprite_rect)
            
            # Update animation timer
            self.animation_timer += 1
        else:
            # Fallback to rectangle
            self._render_fallback_rectangle(screen)
    
    def _render_original_sprites(self, screen: pygame.Surface):
        """Render using original sprite system."""
        # Get current sprite from animation controller
        sprite = self.animation_controller.get_current_sprite()
        
        # Debug: Check if sprite is None for certain animations
        anim_name = self.animation_controller.get_current_animation_name()
        if sprite is None and anim_name in ["dash_forward", "dash_backward", "crouch_transition"]:
            print(f"WARNING: No sprite for animation '{anim_name}' - falling back to parent render")

        if sprite:
            # Flip sprite based on facing direction
            # Original sprites face LEFT, so flip when facing RIGHT
            from street_fighter_3rd.data.enums import FacingDirection
            if self.facing == FacingDirection.RIGHT:
                sprite = pygame.transform.flip(sprite, True, False)

            # Position sprite with proper ground offset
            sprite_rect = sprite.get_rect()
            sprite_rect.centerx = int(self.x)

            # Position sprite using animation-specific ground offset
            anim_name = self.animation_controller.get_current_animation_name()
            ground_offset = self.animation_ground_offsets.get(anim_name, self.ground_offset)
            sprite_rect.bottom = int(self.y) + ground_offset

            # Apply hit flash effect
            if self.hitflash_frames > 0:
                flash_sprite = sprite.copy()
                flash_sprite.fill((30, 30, 30), special_flags=pygame.BLEND_RGB_ADD)
                screen.blit(flash_sprite, sprite_rect)
            else:
                screen.blit(sprite, sprite_rect)

            # Draw state text (debug) above sprite
            font = pygame.font.Font(None, 16)
            facing_str = "RIGHT" if self.facing == FacingDirection.RIGHT else "LEFT"
            state_text = font.render(f"{self.state.name} [{facing_str}]", True, (255, 255, 255))
            screen.blit(state_text, (int(self.x - 30), sprite_rect.top - 20))
        else:
            # Fallback to parent rendering if no sprite
            super().render(screen)
    
    def _get_sf3_animation_name(self) -> str:
        """Map character state to SF3 animation name."""
        # Map current character state to actual SF3 sprite animation names
        state_to_animation = {
            CharacterState.STANDING: "akuma-stance",
            CharacterState.WALKING_FORWARD: "akuma-walkf",
            CharacterState.WALKING_BACKWARD: "akuma-walkb", 
            CharacterState.JUMPING: "akuma-jump",
            CharacterState.JUMPING_FORWARD: "akuma-jumpf",
            CharacterState.JUMPING_BACKWARD: "akuma-jumpb",
            CharacterState.AIRBORNE: "akuma-jump",
            CharacterState.CROUCHING: "akuma-crouch",
            CharacterState.BLOCKING_HIGH: "akuma-block-high",
            CharacterState.BLOCKING_LOW: "akuma-block-crouch",
            CharacterState.LIGHT_PUNCH: "akuma-wp",  # Weak punch
            CharacterState.MEDIUM_PUNCH: "akuma-mp",  # Medium punch
            CharacterState.HEAVY_PUNCH: "akuma-hp",   # Heavy punch
            CharacterState.LIGHT_KICK: "akuma-wk",    # Weak kick
            CharacterState.MEDIUM_KICK: "akuma-mk",   # Medium kick
            CharacterState.HEAVY_KICK: "akuma-hk",    # Heavy kick
            CharacterState.CROUCH_LIGHT_PUNCH: "akuma-crouch-wp",
            CharacterState.CROUCH_MEDIUM_PUNCH: "akuma-crouch-mp",
            CharacterState.CROUCH_HEAVY_PUNCH: "akuma-crouch-hp",
            CharacterState.CROUCH_LIGHT_KICK: "akuma-crouch-wk",
            CharacterState.CROUCH_MEDIUM_KICK: "akuma-crouch-mk",
            CharacterState.CROUCH_HEAVY_KICK: "akuma-crouch-hk",
            CharacterState.GOHADOKEN: "akuma-fireball",
            CharacterState.GOSHORYUKEN: "akuma-dp",  # Dragon punch
            CharacterState.TATSUMAKI: "akuma-hurricane",
            CharacterState.DASH_FORWARD: "akuma-dashf",
            CharacterState.DASH_BACKWARD: "akuma-dashb",
        }
        
        return state_to_animation.get(self.state, "akuma-stance")
    
    def _render_fallback_rectangle(self, screen: pygame.Surface):
        """Render fallback rectangle when sprites fail."""
        # Draw character as colored rectangle (fallback)
        rect = pygame.Rect(int(self.x - 30), int(self.y - 120), 60, 120)
        pygame.draw.rect(screen, self.color, rect)
        
        # Draw facing direction indicator
        from street_fighter_3rd.data.enums import FacingDirection
        eye_x = rect.centerx + (10 if self.facing == FacingDirection.RIGHT else -10)
        pygame.draw.circle(screen, (255, 255, 255), (eye_x, rect.y + 20), 5)
        
        # Draw state text
        font = pygame.font.Font(None, 16)
        facing_str = "RIGHT" if self.facing == FacingDirection.RIGHT else "LEFT"
        state_text = font.render(f"{self.state.name} [{facing_str}]", True, (255, 255, 255))
        screen.blit(state_text, (int(self.x - 30), rect.top - 20))

        # Render projectiles
        for projectile in self.projectiles:
            projectile.render(screen)

    def _update_state(self):
        """Update Akuma-specific state behavior."""
        # Call parent update first
        super()._update_state()

        # Akuma-specific state handling
        if self.state == CharacterState.GOHADOKEN:
            # Fireball animation - 24 frames total
            # Spawn projectile on frame 14 (when animation reaches active frames)
            if self.state_frame == 14 and self.pending_projectile_strength:
                # Spawn the fireball projectile
                # Speed based on strength: light=7, medium=9, heavy=11 pixels/frame
                speed_map = {"light": 7.0, "medium": 9.0, "heavy": 11.0}
                speed = speed_map.get(self.pending_projectile_strength, 7.0)

                # Adjust velocity based on facing direction
                velocity_x = speed if self.facing == FacingDirection.RIGHT else -speed

                # Spawn at character position (slightly in front, at chest height)
                spawn_x = self.x + (40 if self.facing == FacingDirection.RIGHT else -40)
                spawn_y = self.y - 60  # Chest height

                projectile = Gohadoken(spawn_x, spawn_y, velocity_x, self.facing, self.pending_projectile_strength)
                self.projectiles.append(projectile)
                self.pending_projectile_strength = None  # Clear after spawning

            if self.state_frame >= 24:  # Animation complete
                self._transition_to_state(CharacterState.STANDING)

        elif self.state == CharacterState.GOSHORYUKEN:
            # DP animation (placeholder)
            if self.state_frame >= 40:
                self._transition_to_state(CharacterState.STANDING)

        elif self.state == CharacterState.TATSUMAKI:
            # Hurricane kick animation (placeholder)
            if self.state_frame >= 45:
                self._transition_to_state(CharacterState.STANDING)
