#!/usr/bin/env python3
"""
SF3:3S Character Expansion Demo

This demo showcases Option A: Character Expansion features:
- Ken character with Shoto inheritance
- Character selection system
- Multiple character support
- Character-specific differences
- AI personality variations

This demonstrates the complete character expansion system.
"""

import pygame
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    # Import character expansion systems
    from street_fighter_3rd.characters.ken import create_ken_character
    from street_fighter_3rd.ui.character_select import SF3CharacterSelect
    from street_fighter_3rd.integration.sf3_integration import SF3CharacterManager, SF3GameManager
    from street_fighter_3rd.schemas.sf3_schemas import SF3GameConfig
    from street_fighter_3rd.systems.sf3_core import SF3_DAMAGE_SCALING, SF3_PARRY_WINDOW
    from street_fighter_3rd.effects.visual_effects import SF3EffectsManager
    from street_fighter_3rd.ai.advanced_ai import SF3AdvancedAI, GameSituation
    
    IMPORTS_AVAILABLE = True
    
except ImportError as e:
    print(f"⚠️ Character expansion features not available: {e}")
    IMPORTS_AVAILABLE = False


class DemoState:
    """Demo states"""
    CHARACTER_SELECT = "character_select"
    BATTLE = "battle"
    RESULTS = "results"


class CharacterExpansionDemo:
    """
    Character Expansion Demo
    
    Showcases the complete character expansion system with Ken vs Akuma,
    character selection, and character-specific differences.
    """
    
    def __init__(self):
        # Initialize pygame
        pygame.init()
        self.screen_size = (1280, 720)
        self.screen = pygame.display.set_mode(self.screen_size)
        pygame.display.set_caption("SF3:3S Character Expansion Demo")
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.fps = 60
        
        # Demo state
        self.state = DemoState.CHARACTER_SELECT
        self.demo_timer = 0
        
        # Systems
        self.character_select = None
        self.game_manager = None
        self.effects_manager = None
        self.ai_systems = {}
        
        # Selected characters
        self.selected_characters = {}
        self.character_managers = {}
        
        # Battle state
        self.player1 = None
        self.player2 = None
        
        # UI
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 18)
        
        # Demo settings
        self.show_debug_info = True
        self.auto_battle = True
    
    def initialize_systems(self):
        """Initialize all systems"""
        
        # Character selection
        self.character_select = SF3CharacterSelect(self.screen_size)
        self.character_select.initialize_fonts()
        self.character_select.on_selection_complete = self._on_character_selection_complete
        
        # Game manager
        game_config = SF3GameConfig(
            damage_scaling=SF3_DAMAGE_SCALING,
            parry_window=SF3_PARRY_WINDOW,
            hit_queue_size=32,
            input_buffer_size=15
        )
        self.game_manager = SF3GameManager(game_config)
        
        # Effects manager
        self.effects_manager = SF3EffectsManager(self.screen_size)
        self.effects_manager.initialize_fonts()
        
        print("✅ Character expansion demo systems initialized")
    
    def _on_character_selection_complete(self, selection_results: Dict):
        """Handle character selection completion"""
        print("🎯 Character selection complete!")
        
        self.selected_characters = {
            1: selection_results["player1_character"],
            2: selection_results["player2_character"]
        }
        
        self.character_managers = selection_results["character_managers"]
        
        # Set up battle
        self._setup_battle()
        
        # Transition to battle
        self.state = DemoState.BATTLE
    
    def _setup_battle(self):
        """Set up battle with selected characters"""
        
        # Add characters to game manager
        for player_num, char_manager in self.character_managers.items():
            char_name = self.selected_characters[player_num]
            self.game_manager.characters[char_name] = char_manager
        
        # Create players
        self.player1 = self.game_manager.create_player(
            1, self.selected_characters[1], is_cpu=False
        )
        self.player2 = self.game_manager.create_player(
            2, self.selected_characters[2], is_cpu=True
        )
        
        # Position players
        self.player1.work.position.x = 400
        self.player1.work.position.y = 500
        self.player2.work.position.x = 600
        self.player2.work.position.y = 500
        
        # Set up AI for CPU players
        for player_num, char_manager in self.character_managers.items():
            if player_num == 2:  # CPU player
                ai_personality = char_manager.character_data.ai_personality
                self.ai_systems[player_num] = SF3AdvancedAI(ai_personality, char_manager)
        
        print(f"✅ Battle setup complete:")
        print(f"   Player 1: {self.selected_characters[1]}")
        print(f"   Player 2: {self.selected_characters[2]} (CPU)")
    
    async def run(self):
        """Main demo loop"""
        
        if not IMPORTS_AVAILABLE:
            self._show_import_error()
            return
        
        # Initialize systems
        self.initialize_systems()
        
        print("🚀 Starting Character Expansion Demo...")
        print("Features showcased:")
        print("  - Ken character with Shoto inheritance")
        print("  - Character selection system")
        print("  - Character-specific differences")
        print("  - AI personality variations")
        print("  - Multi-character support")
        
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
                    if self.state == DemoState.CHARACTER_SELECT:
                        self.running = False
                    else:
                        # Return to character select
                        self.state = DemoState.CHARACTER_SELECT
                        self._reset_demo()
                
                elif event.key == pygame.K_d:
                    self.show_debug_info = not self.show_debug_info
                elif event.key == pygame.K_a:
                    self.auto_battle = not self.auto_battle
                elif event.key == pygame.K_r:
                    self._reset_demo()
            
            # Pass events to current state
            if self.state == DemoState.CHARACTER_SELECT:
                self.character_select.handle_input(events)
    
    async def _update(self):
        """Update demo systems"""
        
        self.demo_timer += 1
        
        if self.state == DemoState.CHARACTER_SELECT:
            await self._update_character_select()
        elif self.state == DemoState.BATTLE:
            await self._update_battle()
    
    async def _update_character_select(self):
        """Update character selection"""
        self.character_select.update()
        
        # Check if selection is complete
        if self.character_select.is_selection_complete():
            # Transition handled by callback
            pass
    
    async def _update_battle(self):
        """Update battle simulation"""
        
        # Update game manager
        self.game_manager.update_frame()
        
        # Update AI
        if 2 in self.ai_systems:
            ai_system = self.ai_systems[2]
            
            # Create game situation
            distance = abs(self.player1.work.position.x - self.player2.work.position.x)
            situation = GameSituation(
                distance=distance,
                range_category="close" if distance < 150 else "mid" if distance < 300 else "far",
                my_health_ratio=self.player2.work.vitality / 1000,
                opponent_health_ratio=self.player1.work.vitality / 1000,
                frame_advantage=0
            )
            
            # Get AI decision
            direction, buttons = ai_system.update(self.player2, self.player1, situation)
        
        # Update effects
        self.effects_manager.update()
        
        # Simulate combat for demo
        await self._simulate_character_differences()
    
    async def _simulate_character_differences(self):
        """Simulate combat to show character differences"""
        
        # Randomly trigger character-specific effects
        if self.demo_timer % 120 == 0:  # Every 2 seconds
            await self._demonstrate_character_differences()
    
    async def _demonstrate_character_differences(self):
        """Demonstrate differences between characters"""
        
        char1_name = self.selected_characters[1]
        char2_name = self.selected_characters[2]
        
        print(f"🥋 Demonstrating {char1_name} vs {char2_name} differences:")
        
        # Get character data
        char1_data = self.character_managers[1].character_data
        char2_data = self.character_managers[2].character_data
        
        # Compare key differences
        print(f"   {char1_name} walk speed: {char1_data.character_info.walk_speed}")
        print(f"   {char2_name} walk speed: {char2_data.character_info.walk_speed}")
        
        print(f"   {char1_name} AI aggression: {char1_data.ai_personality.aggression}")
        print(f"   {char2_name} AI aggression: {char2_data.ai_personality.aggression}")
        
        # Trigger visual effect
        center_x = self.screen_size[0] // 2
        center_y = self.screen_size[1] // 2
        
        self.effects_manager.create_hit_effect(
            position=(center_x, center_y),
            damage=115,
            hit_level=self.effects_manager.SF3HitLevel.MID if hasattr(self.effects_manager, 'SF3HitLevel') else None
        )
    
    def _reset_demo(self):
        """Reset demo to character select"""
        self.state = DemoState.CHARACTER_SELECT
        self.demo_timer = 0
        self.selected_characters = {}
        self.character_managers = {}
        self.player1 = None
        self.player2 = None
        self.ai_systems = {}
        
        # Reset character select
        if self.character_select:
            self.character_select.state = self.character_select.SelectionState.BROWSING
            for player in self.character_select.players.values():
                player.selected_character = None
                player.confirmed = False
        
        print("🔄 Demo reset to character selection")
    
    def _draw(self):
        """Draw demo"""
        
        # Clear screen
        self.screen.fill((20, 20, 40))
        
        if self.state == DemoState.CHARACTER_SELECT:
            self._draw_character_select()
        elif self.state == DemoState.BATTLE:
            self._draw_battle()
        
        # Draw demo info
        self._draw_demo_info()
        
        # Draw debug info
        if self.show_debug_info:
            self._draw_debug_info()
        
        pygame.display.flip()
    
    def _draw_character_select(self):
        """Draw character selection screen"""
        if self.character_select:
            self.character_select.draw(self.screen)
    
    def _draw_battle(self):
        """Draw battle screen"""
        
        # Draw stage background (simplified)
        self._draw_stage_background()
        
        # Draw characters
        self._draw_characters()
        
        # Draw character info
        self._draw_character_info()
        
        # Draw effects
        self.effects_manager.draw(self.screen)
    
    def _draw_stage_background(self):
        """Draw simplified stage background"""
        # Ground
        ground_rect = pygame.Rect(0, 550, self.screen_size[0], self.screen_size[1] - 550)
        pygame.draw.rect(self.screen, (60, 40, 20), ground_rect)
        
        # Stage line
        pygame.draw.line(self.screen, (100, 80, 60), (0, 550), (self.screen_size[0], 550), 3)
    
    def _draw_characters(self):
        """Draw character representations"""
        if self.player1:
            # Player 1 (blue)
            player1_rect = pygame.Rect(
                self.player1.work.position.x - 20,
                self.player1.work.position.y - 80,
                40, 80
            )
            pygame.draw.rect(self.screen, (100, 150, 255), player1_rect)
            
            # Character name
            char1_name = self.selected_characters[1]
            name_surface = self.small_font.render(char1_name.title(), True, (255, 255, 255))
            self.screen.blit(name_surface, (player1_rect.x - 10, player1_rect.y - 20))
        
        if self.player2:
            # Player 2 (red)
            player2_rect = pygame.Rect(
                self.player2.work.position.x - 20,
                self.player2.work.position.y - 80,
                40, 80
            )
            pygame.draw.rect(self.screen, (255, 100, 100), player2_rect)
            
            # Character name
            char2_name = self.selected_characters[2]
            name_surface = self.small_font.render(char2_name.title(), True, (255, 255, 255))
            self.screen.blit(name_surface, (player2_rect.x - 10, player2_rect.y - 20))
    
    def _draw_character_info(self):
        """Draw character information"""
        if not self.character_managers:
            return
        
        # Player 1 info
        if 1 in self.character_managers:
            char_data = self.character_managers[1].character_data
            info_lines = [
                f"Player 1: {char_data.character_info.name}",
                f"Health: {self.player1.work.vitality if self.player1 else 1000}",
                f"Walk Speed: {char_data.character_info.walk_speed:.3f}",
                f"AI Aggression: {char_data.ai_personality.aggression:.1f}",
                f"Combo Preference: {char_data.ai_personality.combo_preference:.1f}"
            ]
            
            for i, line in enumerate(info_lines):
                line_surface = self.small_font.render(line, True, (255, 255, 255))
                self.screen.blit(line_surface, (20, 20 + i * 18))
        
        # Player 2 info
        if 2 in self.character_managers:
            char_data = self.character_managers[2].character_data
            info_lines = [
                f"Player 2: {char_data.character_info.name} (CPU)",
                f"Health: {self.player2.work.vitality if self.player2 else 1000}",
                f"Walk Speed: {char_data.character_info.walk_speed:.3f}",
                f"AI Aggression: {char_data.ai_personality.aggression:.1f}",
                f"Combo Preference: {char_data.ai_personality.combo_preference:.1f}"
            ]
            
            for i, line in enumerate(info_lines):
                line_surface = self.small_font.render(line, True, (255, 255, 255))
                self.screen.blit(line_surface, (self.screen_size[0] - 250, 20 + i * 18))
    
    def _draw_demo_info(self):
        """Draw demo information"""
        
        # Title
        title_text = "Character Expansion Demo"
        title_surface = self.title_font.render(title_text, True, (255, 255, 100))
        title_rect = title_surface.get_rect()
        title_rect.centerx = self.screen_size[0] // 2
        title_rect.y = 10
        self.screen.blit(title_surface, title_rect)
        
        # State indicator
        state_text = f"State: {self.state.replace('_', ' ').title()}"
        state_surface = self.font.render(state_text, True, (200, 200, 200))
        self.screen.blit(state_surface, (10, self.screen_size[1] - 100))
        
        # Controls
        controls = [
            "ESC: Exit/Return to character select",
            "D: Toggle debug info",
            "A: Toggle auto battle",
            "R: Reset demo"
        ]
        
        for i, control in enumerate(controls):
            control_surface = self.small_font.render(control, True, (150, 150, 150))
            self.screen.blit(control_surface, (10, self.screen_size[1] - 80 + i * 15))
    
    def _draw_debug_info(self):
        """Draw debug information"""
        debug_info = [
            f"FPS: {self.clock.get_fps():.1f}",
            f"Frame: {self.game_manager.current_frame if self.game_manager else 0}",
            f"Demo Timer: {self.demo_timer}",
            f"Characters: {len(self.character_managers)}",
            f"AI Systems: {len(self.ai_systems)}",
            f"Effects: {len(self.effects_manager.active_effects) if self.effects_manager else 0}"
        ]
        
        # Debug panel
        debug_panel = pygame.Rect(self.screen_size[0] - 200, self.screen_size[1] - 150, 190, 120)
        pygame.draw.rect(self.screen, (0, 0, 0, 180), debug_panel)
        pygame.draw.rect(self.screen, (255, 255, 255), debug_panel, 1)
        
        for i, info in enumerate(debug_info):
            info_surface = self.small_font.render(info, True, (255, 255, 255))
            self.screen.blit(info_surface, (debug_panel.x + 5, debug_panel.y + 5 + i * 18))
    
    def _show_import_error(self):
        """Show import error screen"""
        self.screen.fill((40, 20, 20))
        
        error_text = "Character Expansion Features Not Available"
        error_surface = self.title_font.render(error_text, True, (255, 100, 100))
        error_rect = error_surface.get_rect()
        error_rect.center = (self.screen_size[0] // 2, self.screen_size[1] // 2 - 50)
        self.screen.blit(error_surface, error_rect)
        
        help_text = "Please ensure all dependencies are installed"
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
    demo = CharacterExpansionDemo()
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main())
