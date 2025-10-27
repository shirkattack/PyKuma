#!/usr/bin/env python3
"""
SF3:3S Sprite Integration Demo

This demo showcases Option 4: Sprite Integration features:
- Actual Akuma sprites from our extraction tools
- Animation system with authentic SF3 timing
- Sprite-based character rendering
- Animation state management
- Visual comparison with/without sprites

This demonstrates the complete sprite integration system.
"""

import pygame
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    # Import sprite integration systems
    from street_fighter_3rd.integration.sprite_integration import (
        SF3SpriteGameManager, SF3SpriteCharacterManager, create_sprite_game_manager
    )
    from street_fighter_3rd.graphics.sprite_manager import SF3SpriteManager
    from street_fighter_3rd.graphics.animation_system import SF3AnimationController
    from street_fighter_3rd.schemas.sf3_schemas import SF3GameConfig, CharacterData
    from street_fighter_3rd.systems.sf3_core import SF3_DAMAGE_SCALING, SF3_PARRY_WINDOW
    from street_fighter_3rd.effects.visual_effects import SF3EffectsManager
    
    IMPORTS_AVAILABLE = True
    
except ImportError as e:
    print(f"⚠️ Sprite integration features not available: {e}")
    IMPORTS_AVAILABLE = False


class DemoMode:
    """Demo modes"""
    SPRITE_SHOWCASE = "sprite_showcase"
    ANIMATION_TEST = "animation_test"
    COMPARISON = "comparison"
    SPRITE_BROWSER = "sprite_browser"


class SpriteIntegrationDemo:
    """
    Sprite Integration Demo
    
    Showcases the complete sprite integration system with actual Akuma
    animations, sprite management, and animation control.
    """
    
    def __init__(self):
        # Initialize pygame
        pygame.init()
        self.screen_size = (1280, 720)
        self.screen = pygame.display.set_mode(self.screen_size)
        pygame.display.set_caption("SF3:3S Sprite Integration Demo")
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.fps = 60
        
        # Demo state
        self.current_mode = DemoMode.SPRITE_SHOWCASE
        self.demo_timer = 0
        
        # Systems
        self.sprite_game_manager = None
        self.effects_manager = None
        
        # Characters
        self.akuma_manager = None
        self.player1 = None
        
        # Animation testing
        self.current_animation = "stance"
        self.animation_list = []
        self.animation_index = 0
        self.auto_cycle_animations = True
        self.animation_cycle_timer = 0
        self.animation_cycle_interval = 180  # 3 seconds at 60fps
        
        # UI
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 18)
        
        # Demo settings
        self.show_debug_info = True
        self.show_sprites = True
        self.show_hitboxes = False
    
    def initialize_systems(self):
        """Initialize all systems"""
        
        # Game config
        game_config = SF3GameConfig(
            damage_scaling=SF3_DAMAGE_SCALING,
            parry_window=SF3_PARRY_WINDOW,
            hit_queue_size=32,
            input_buffer_size=15
        )
        
        # Create sprite game manager
        self.sprite_game_manager = create_sprite_game_manager(game_config)
        
        # Effects manager
        self.effects_manager = SF3EffectsManager(self.screen_size)
        self.effects_manager.initialize_fonts()
        
        # Load Akuma character
        self._load_akuma_character()
        
        print("✅ Sprite integration demo systems initialized")
    
    def _load_akuma_character(self):
        """Load Akuma character with sprites"""
        
        # Create Akuma character data
        akuma_data = self._create_akuma_character_data()
        
        try:
            character_data = CharacterData(**akuma_data)
            
            # Add character with sprites
            self.akuma_manager = self.sprite_game_manager.add_sprite_character("akuma", character_data)
            
            # Create player
            self.player1 = self.sprite_game_manager.create_sprite_player(1, "akuma", is_cpu=False)
            
            # Position player
            self.player1.work.position.x = 400
            self.player1.work.position.y = 500
            
            # Get available animations
            self.animation_list = self.akuma_manager.get_available_animations()
            if not self.animation_list:
                # Fallback animation list
                self.animation_list = [
                    "stance", "walkf", "walkb", "jump", "block",
                    "standing_medium_punch", "crouching_medium_kick",
                    "hadoken_light", "shoryuken_light", "tatsumaki_light"
                ]
            
            print(f"✅ Akuma loaded:")
            print(f"   Sprites loaded: {self.akuma_manager.has_sprites()}")
            print(f"   Available animations: {len(self.animation_list)}")
            
        except Exception as e:
            print(f"❌ Failed to load Akuma: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_akuma_character_data(self) -> Dict:
        """Create Akuma character data"""
        return {
            "character_info": {
                "name": "Akuma",
                "sf3_character_id": 14,
                "archetype": "shoto",
                "health": 1050,
                "stun": 64,
                "walk_speed": 0.032,
                "walk_backward_speed": 0.025,
                "dash_distance": 80,
                "jump_startup": 4,
                "jump_duration": 45,
                "jump_height": 120
            },
            "normal_attacks": {
                "standing_medium_punch": {
                    "name": "standing_medium_punch",
                    "move_type": "normal",
                    "frame_data": {"startup": 5, "active": 3, "recovery": 10, "total": 18},
                    "hitboxes": {"attack": [], "body": [], "hand": []},
                    "ai_utility": 0.7
                },
                "crouching_medium_kick": {
                    "name": "crouching_medium_kick",
                    "move_type": "normal",
                    "frame_data": {"startup": 6, "active": 3, "recovery": 13, "total": 22},
                    "hitboxes": {"attack": [], "body": [], "hand": []},
                    "ai_utility": 0.6
                }
            },
            "special_moves": {
                "hadoken_light": {
                    "name": "hadoken_light",
                    "move_type": "special",
                    "frame_data": {"startup": 13, "active": 2, "recovery": 31, "total": 46},
                    "hitboxes": {"attack": [], "body": [], "projectile": []},
                    "input_command": "QCF+P",
                    "ai_utility": 0.8
                },
                "shoryuken_light": {
                    "name": "shoryuken_light",
                    "move_type": "special",
                    "frame_data": {"startup": 3, "active": 12, "recovery": 25, "total": 40},
                    "hitboxes": {"attack": [], "body": [], "hand": []},
                    "input_command": "DP+P",
                    "ai_utility": 0.7
                },
                "tatsumaki_light": {
                    "name": "tatsumaki_light",
                    "move_type": "special",
                    "frame_data": {"startup": 7, "active": 18, "recovery": 15, "total": 40},
                    "hitboxes": {"attack": [], "body": [], "hand": []},
                    "input_command": "QCB+K",
                    "ai_utility": 0.6
                }
            },
            "super_arts": {},
            "throws": {},
            "movement": {"walk_forward_speed": 0.032},
            "parry": {"window_frames": 7, "advantage_frames": 8, "guard_directions": ["high", "mid", "low"]},
            "ai_personality": {
                "aggression": 0.7,
                "defensive_style": 0.4,
                "zoning_preference": 0.8,
                "combo_preference": 0.6,
                "risk_taking": 0.5,
                "reaction_time": 5,
                "input_accuracy": 0.9,
                "pattern_recognition": 0.7
            }
        }
    
    async def run(self):
        """Main demo loop"""
        
        if not IMPORTS_AVAILABLE:
            self._show_import_error()
            return
        
        # Initialize systems
        self.initialize_systems()
        
        print("🚀 Starting Sprite Integration Demo...")
        print("Features showcased:")
        print("  - Actual Akuma sprites from extraction tools")
        print("  - Animation system with SF3 timing")
        print("  - Sprite management and caching")
        print("  - Animation state control")
        print("  - Visual comparison modes")
        
        # Main loop
        while self.running:
            events = pygame.event.get()
            await self._handle_events(events)
            await self._update()
            self._draw()
            
            # Cap framerate
            self.clock.tick(self.fps)
        
        pygame.quit()
    
    async def _handle_events(self, events):
        """Handle pygame events"""
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                
                elif event.key == pygame.K_1:
                    self.current_mode = DemoMode.SPRITE_SHOWCASE
                elif event.key == pygame.K_2:
                    self.current_mode = DemoMode.ANIMATION_TEST
                elif event.key == pygame.K_3:
                    self.current_mode = DemoMode.COMPARISON
                elif event.key == pygame.K_4:
                    self.current_mode = DemoMode.SPRITE_BROWSER
                
                elif event.key == pygame.K_d:
                    self.show_debug_info = not self.show_debug_info
                elif event.key == pygame.K_s:
                    self.show_sprites = not self.show_sprites
                elif event.key == pygame.K_h:
                    self.show_hitboxes = not self.show_hitboxes
                elif event.key == pygame.K_a:
                    self.auto_cycle_animations = not self.auto_cycle_animations
                
                # Animation controls
                elif event.key == pygame.K_LEFT:
                    self._previous_animation()
                elif event.key == pygame.K_RIGHT:
                    self._next_animation()
                elif event.key == pygame.K_SPACE:
                    self._trigger_current_animation()
    
    async def _update(self):
        """Update demo systems"""
        
        self.demo_timer += 1
        
        # Update game manager
        if self.sprite_game_manager:
            self.sprite_game_manager.update_frame()
        
        # Update effects
        if self.effects_manager:
            self.effects_manager.update()
        
        # Handle mode-specific updates
        if self.current_mode == DemoMode.ANIMATION_TEST:
            await self._update_animation_test()
        elif self.current_mode == DemoMode.SPRITE_BROWSER:
            await self._update_sprite_browser()
    
    async def _update_animation_test(self):
        """Update animation testing mode"""
        
        if self.auto_cycle_animations:
            self.animation_cycle_timer += 1
            
            if self.animation_cycle_timer >= self.animation_cycle_interval:
                self.animation_cycle_timer = 0
                self._next_animation()
                self._trigger_current_animation()
    
    async def _update_sprite_browser(self):
        """Update sprite browser mode"""
        # Auto-cycle through animations more slowly
        if self.demo_timer % 300 == 0:  # Every 5 seconds
            self._next_animation()
            self._trigger_current_animation()
    
    def _next_animation(self):
        """Switch to next animation"""
        if self.animation_list:
            self.animation_index = (self.animation_index + 1) % len(self.animation_list)
            self.current_animation = self.animation_list[self.animation_index]
    
    def _previous_animation(self):
        """Switch to previous animation"""
        if self.animation_list:
            self.animation_index = (self.animation_index - 1) % len(self.animation_list)
            self.current_animation = self.animation_list[self.animation_index]
    
    def _trigger_current_animation(self):
        """Trigger current animation"""
        if self.sprite_game_manager and self.current_animation:
            self.sprite_game_manager.force_animation(1, self.current_animation, loop=True)
    
    def _draw(self):
        """Draw demo"""
        
        # Clear screen
        self.screen.fill((20, 20, 40))
        
        # Draw stage background
        self._draw_stage_background()
        
        # Draw characters
        self._draw_characters()
        
        # Draw mode-specific elements
        if self.current_mode == DemoMode.SPRITE_SHOWCASE:
            self._draw_sprite_showcase()
        elif self.current_mode == DemoMode.ANIMATION_TEST:
            self._draw_animation_test()
        elif self.current_mode == DemoMode.COMPARISON:
            self._draw_comparison()
        elif self.current_mode == DemoMode.SPRITE_BROWSER:
            self._draw_sprite_browser()
        
        # Draw effects
        if self.effects_manager:
            self.effects_manager.draw(self.screen)
        
        # Draw UI
        self._draw_ui()
        
        # Draw debug info
        if self.show_debug_info:
            self._draw_debug_info()
        
        pygame.display.flip()
    
    def _draw_stage_background(self):
        """Draw stage background"""
        # Ground
        ground_rect = pygame.Rect(0, 550, self.screen_size[0], self.screen_size[1] - 550)
        pygame.draw.rect(self.screen, (60, 40, 20), ground_rect)
        
        # Stage line
        pygame.draw.line(self.screen, (100, 80, 60), (0, 550), (self.screen_size[0], 550), 3)
    
    def _draw_characters(self):
        """Draw characters with sprites or placeholders"""
        
        if self.sprite_game_manager and self.show_sprites:
            # Render with sprite system
            self.sprite_game_manager.render_characters(self.screen)
        elif self.player1:
            # Fallback placeholder
            char_rect = pygame.Rect(
                self.player1.work.position.x - 20,
                self.player1.work.position.y - 80,
                40, 80
            )
            pygame.draw.rect(self.screen, (100, 150, 255), char_rect)
            
            # Character name
            name_surface = self.small_font.render("Akuma (No Sprites)", True, (255, 255, 255))
            self.screen.blit(name_surface, (char_rect.x - 20, char_rect.y - 20))
    
    def _draw_sprite_showcase(self):
        """Draw sprite showcase mode"""
        
        # Showcase info
        showcase_text = "Sprite Showcase - Authentic SF3 Akuma Sprites"
        showcase_surface = self.font.render(showcase_text, True, (255, 255, 100))
        self.screen.blit(showcase_surface, (20, 100))
        
        # Sprite info
        if self.akuma_manager and self.akuma_manager.has_sprites():
            info_lines = [
                f"Sprites loaded: ✅ {len(self.animation_list)} animations",
                f"Current animation: {self.current_animation}",
                f"Source: justnopoint.com Akuma animations",
                f"Extracted frames: PNG format with transparency"
            ]
        else:
            info_lines = [
                "Sprites not loaded: ❌ Using placeholders",
                "Expected path: tools/sprite_extraction/akuma_animations/",
                "Run sprite extraction tools to load Akuma sprites"
            ]
        
        for i, line in enumerate(info_lines):
            line_surface = self.small_font.render(line, True, (200, 200, 200))
            self.screen.blit(line_surface, (20, 125 + i * 18))
    
    def _draw_animation_test(self):
        """Draw animation test mode"""
        
        test_text = "Animation Test - Cycle Through Akuma Animations"
        test_surface = self.font.render(test_text, True, (100, 255, 100))
        self.screen.blit(test_surface, (20, 100))
        
        # Animation controls
        controls = [
            f"Current: {self.current_animation} ({self.animation_index + 1}/{len(self.animation_list)})",
            f"Auto-cycle: {'ON' if self.auto_cycle_animations else 'OFF'}",
            "Left/Right: Change animation",
            "Space: Trigger animation",
            "A: Toggle auto-cycle"
        ]
        
        for i, control in enumerate(controls):
            control_surface = self.small_font.render(control, True, (200, 200, 200))
            self.screen.blit(control_surface, (20, 125 + i * 18))
    
    def _draw_comparison(self):
        """Draw comparison mode"""
        
        comparison_text = "Comparison - Sprites vs Placeholders"
        comparison_surface = self.font.render(comparison_text, True, (255, 100, 255))
        self.screen.blit(comparison_surface, (20, 100))
        
        # Draw both versions side by side
        if self.player1:
            # Sprite version (left)
            if self.sprite_game_manager and self.show_sprites:
                sprite_controller = self.sprite_game_manager.get_animation_controller(1)
                if sprite_controller:
                    sprite_controller.render(self.screen, 300, 500, facing_right=True)
            
            # Placeholder version (right)
            placeholder_rect = pygame.Rect(580, 420, 40, 80)
            pygame.draw.rect(self.screen, (255, 100, 100), placeholder_rect)
            
            # Labels
            sprite_label = self.small_font.render("With Sprites", True, (255, 255, 255))
            placeholder_label = self.small_font.render("Placeholder", True, (255, 255, 255))
            self.screen.blit(sprite_label, (270, 520))
            self.screen.blit(placeholder_label, (570, 520))
    
    def _draw_sprite_browser(self):
        """Draw sprite browser mode"""
        
        browser_text = "Sprite Browser - Browse All Akuma Animations"
        browser_surface = self.font.render(browser_text, True, (255, 255, 255))
        self.screen.blit(browser_surface, (20, 100))
        
        # Animation list
        if self.animation_list:
            list_y = 130
            for i, anim_name in enumerate(self.animation_list[:10]):  # Show first 10
                color = (255, 255, 100) if i == self.animation_index else (200, 200, 200)
                marker = "►" if i == self.animation_index else " "
                
                anim_text = f"{marker} {anim_name}"
                anim_surface = self.small_font.render(anim_text, True, color)
                self.screen.blit(anim_surface, (20, list_y + i * 16))
    
    def _draw_ui(self):
        """Draw main UI"""
        
        # Title
        title_text = "SF3:3S Sprite Integration Demo"
        title_surface = self.title_font.render(title_text, True, (255, 255, 255))
        title_rect = title_surface.get_rect()
        title_rect.centerx = self.screen_size[0] // 2
        title_rect.y = 10
        self.screen.blit(title_surface, title_rect)
        
        # Mode indicator
        mode_text = f"Mode: {self.current_mode.replace('_', ' ').title()}"
        mode_surface = self.font.render(mode_text, True, (255, 255, 100))
        self.screen.blit(mode_surface, (10, self.screen_size[1] - 120))
        
        # Controls
        controls = [
            "1-4: Switch modes",
            "S: Toggle sprites",
            "D: Toggle debug",
            "H: Toggle hitboxes",
            "ESC: Exit"
        ]
        
        for i, control in enumerate(controls):
            control_surface = self.small_font.render(control, True, (150, 150, 150))
            self.screen.blit(control_surface, (10, self.screen_size[1] - 100 + i * 15))
    
    def _draw_debug_info(self):
        """Draw debug information"""
        
        debug_info = [
            f"FPS: {self.clock.get_fps():.1f}",
            f"Frame: {self.sprite_game_manager.current_frame if self.sprite_game_manager else 0}",
            f"Demo Timer: {self.demo_timer}",
            f"Show Sprites: {self.show_sprites}",
            f"Akuma Loaded: {self.akuma_manager.has_sprites() if self.akuma_manager else False}",
            f"Animations: {len(self.animation_list)}"
        ]
        
        # Add sprite stats
        if self.sprite_game_manager:
            stats = self.sprite_game_manager.get_sprite_stats()
            debug_info.extend([
                f"Sprite Memory: {stats['sprite_manager'].get('estimated_memory_mb', 0):.1f}MB",
                f"Cache Size: {stats['sprite_manager'].get('cache_size', 0)}"
            ])
        
        # Debug panel
        debug_panel = pygame.Rect(self.screen_size[0] - 250, self.screen_size[1] - 180, 240, 170)
        pygame.draw.rect(self.screen, (0, 0, 0, 180), debug_panel)
        pygame.draw.rect(self.screen, (255, 255, 255), debug_panel, 1)
        
        for i, info in enumerate(debug_info):
            info_surface = self.small_font.render(info, True, (255, 255, 255))
            self.screen.blit(info_surface, (debug_panel.x + 5, debug_panel.y + 5 + i * 18))
    
    def _show_import_error(self):
        """Show import error screen"""
        self.screen.fill((40, 20, 20))
        
        error_text = "Sprite Integration Features Not Available"
        error_surface = self.title_font.render(error_text, True, (255, 100, 100))
        error_rect = error_surface.get_rect()
        error_rect.center = (self.screen_size[0] // 2, self.screen_size[1] // 2 - 50)
        self.screen.blit(error_surface, error_rect)
        
        help_text = "Please ensure all dependencies are installed with uv"
        help_surface = self.font.render(help_text, True, (255, 255, 255))
        help_rect = help_surface.get_rect()
        help_rect.center = (self.screen_size[0] // 2, self.screen_size[1] // 2 + 20)
        self.screen.blit(help_surface, help_rect)
        
        pygame.display.flip()
        
        # Wait for exit
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    waiting = False
            self.clock.tick(60)


async def main():
    """Main demo function"""
    demo = SpriteIntegrationDemo()
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main())
