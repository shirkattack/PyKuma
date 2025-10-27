#!/usr/bin/env python3
"""
SF3:3S Enhanced Demo

This demo showcases all the enhanced features from Phase 2:
- Training mode with real-time frame data
- Advanced AI with personality-based behavior
- Network play foundation (local simulation)
- Visual effects and polish
- Complete integration of all systems

This demonstrates the full power of our authentic SF3 recreation
with modern enhancements.
"""

import pygame
import sys
import asyncio
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    # Import our complete SF3 system
    from street_fighter_3rd.schemas.sf3_schemas import (
        CharacterData, AIPersonality, SF3GameConfig, CharacterArchetype
    )
    from street_fighter_3rd.integration.sf3_integration import (
        SF3CharacterManager, SF3GameManager
    )
    from street_fighter_3rd.modes.training_mode import SF3TrainingMode, TrainingSettings
    from street_fighter_3rd.ai.advanced_ai import SF3AdvancedAI, GameSituation
    from street_fighter_3rd.network.netplay import SF3NetworkManager
    from street_fighter_3rd.effects.visual_effects import SF3EffectsManager
    from street_fighter_3rd.systems.sf3_core import SF3_DAMAGE_SCALING, SF3_PARRY_WINDOW
    from street_fighter_3rd.systems.sf3_input import SF3InputDirection, SF3ButtonInput
    from street_fighter_3rd.systems.sf3_hitboxes import SF3HitLevel
    
    IMPORTS_AVAILABLE = True
    
except ImportError as e:
    print(f"⚠️ Enhanced features not available: {e}")
    print("This demo requires all Phase 1 and Phase 2 components")
    IMPORTS_AVAILABLE = False


class DemoMode:
    """Demo mode selection"""
    TRAINING = "training"
    AI_BATTLE = "ai_battle"
    NETWORK_DEMO = "network_demo"
    EFFECTS_SHOWCASE = "effects_showcase"


class EnhancedSF3Demo:
    """
    Enhanced SF3 Demo showcasing all Phase 2 features
    
    This demo provides a complete showcase of our authentic SF3 recreation
    with all the modern enhancements and polish.
    """
    
    def __init__(self):
        # Initialize pygame
        pygame.init()
        self.screen_size = (1280, 720)
        self.screen = pygame.display.set_mode(self.screen_size)
        pygame.display.set_caption("SF3:3S Enhanced Demo - Phase 2 Features")
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.fps = 60
        
        # Demo state
        self.current_mode = DemoMode.TRAINING
        self.demo_timer = 0
        
        # Initialize systems
        self.game_manager = None
        self.training_mode = None
        self.ai_system = None
        self.network_manager = None
        self.effects_manager = None
        
        # Demo players
        self.player1 = None
        self.player2 = None
        
        # UI
        self.font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 18)
        
        # Demo settings
        self.show_debug_info = True
        self.auto_switch_modes = True
        self.mode_switch_interval = 1800  # 30 seconds at 60fps
        
    def initialize_game_systems(self):
        """Initialize all game systems"""
        
        # Create game config
        game_config = SF3GameConfig(
            damage_scaling=SF3_DAMAGE_SCALING,
            parry_window=SF3_PARRY_WINDOW,
            hit_queue_size=32,
            input_buffer_size=15
        )
        
        # Create game manager
        self.game_manager = SF3GameManager(game_config)
        
        # Load Akuma character (using mock data for demo)
        akuma_data = self._create_demo_character_data()
        character_data = CharacterData(**akuma_data)
        character_manager = SF3CharacterManager(character_data)
        self.game_manager.characters["Akuma"] = character_manager
        
        # Create players
        self.player1 = self.game_manager.create_player(1, "Akuma", is_cpu=False)
        self.player2 = self.game_manager.create_player(2, "Akuma", is_cpu=True)
        
        # Position players
        self.player1.work.position.x = 400
        self.player1.work.position.y = 500
        self.player2.work.position.x = 600
        self.player2.work.position.y = 500
        
        # Initialize enhanced systems
        self._initialize_training_mode()
        self._initialize_ai_system()
        self._initialize_effects_manager()
        self._initialize_network_manager()
        
        print("✅ All game systems initialized")
    
    def _create_demo_character_data(self) -> Dict:
        """Create demo character data for testing"""
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
                    "frame_data": {
                        "startup": 5,
                        "active": 3,
                        "recovery": 10,
                        "total": 18,
                        "hit_advantage": 2,
                        "block_advantage": 1,
                        "special_cancelable": True,
                        "super_cancelable": True
                    },
                    "hitboxes": {
                        "attack": [{"offset_x": 50, "offset_y": -65, "width": 60, "height": 40, "damage": 115, "stun": 7}],
                        "body": [{"offset_x": 0, "offset_y": -80, "width": 40, "height": 80}],
                        "hand": [{"offset_x": 30, "offset_y": -65, "width": 25, "height": 25}]
                    },
                    "ai_utility": 0.7,
                    "ai_risk_level": 0.3,
                    "ai_range": "mid"
                }
            },
            "special_moves": {
                "gohadoken_light": {
                    "name": "gohadoken_light",
                    "move_type": "special",
                    "input_command": "QCF+P",
                    "frame_data": {
                        "startup": 13,
                        "active": 2,
                        "recovery": 31,
                        "total": 46,
                        "hit_advantage": 0,
                        "block_advantage": -2
                    },
                    "hitboxes": {
                        "attack": [{"offset_x": 45, "offset_y": -50, "width": 50, "height": 35, "damage": 100, "stun": 8}],
                        "projectile": [{"offset_x": 0, "offset_y": 0, "width": 30, "height": 20}]
                    },
                    "projectile_speed": 3.0,
                    "projectile_durability": 1,
                    "ai_utility": 0.8,
                    "ai_range": "far"
                }
            },
            "super_arts": {},
            "throws": {},
            "movement": {
                "walk_forward_speed": 0.032,
                "walk_backward_speed": 0.025,
                "dash_forward_distance": 80,
                "jump_startup": 4
            },
            "parry": {
                "window_frames": 7,
                "advantage_frames": 8,
                "guard_directions": ["high", "mid", "low"]
            },
            "ai_personality": {
                "aggression": 0.7,
                "defensive_style": 0.4,
                "zoning_preference": 0.6,
                "combo_preference": 0.8,
                "risk_taking": 0.5,
                "reaction_time": 5,
                "input_accuracy": 0.9,
                "pattern_recognition": 0.7
            }
        }
    
    def _initialize_training_mode(self):
        """Initialize training mode"""
        settings = TrainingSettings(
            show_frame_data=True,
            show_hitboxes=True,
            show_input_display=True,
            show_damage_scaling=True,
            dummy_behavior="cpu",
            infinite_meter=True
        )
        
        self.training_mode = SF3TrainingMode(self.game_manager, self.screen_size)
        self.training_mode.settings = settings
        self.training_mode.initialize_display(self.screen)
        
        print("✅ Training mode initialized")
    
    def _initialize_ai_system(self):
        """Initialize advanced AI system"""
        ai_personality = AIPersonality(
            aggression=0.7,
            defensive_style=0.4,
            zoning_preference=0.6,
            combo_preference=0.8,
            risk_taking=0.5,
            reaction_time=5,
            input_accuracy=0.9,
            pattern_recognition=0.7
        )
        
        character_manager = self.game_manager.characters["Akuma"]
        self.ai_system = SF3AdvancedAI(ai_personality, character_manager)
        
        print("✅ Advanced AI system initialized")
    
    def _initialize_effects_manager(self):
        """Initialize visual effects manager"""
        self.effects_manager = SF3EffectsManager(self.screen_size)
        self.effects_manager.initialize_fonts()
        
        print("✅ Visual effects manager initialized")
    
    def _initialize_network_manager(self):
        """Initialize network manager (demo mode)"""
        self.network_manager = SF3NetworkManager(self.game_manager)
        
        print("✅ Network manager initialized")
    
    async def run(self):
        """Main demo loop"""
        
        if not IMPORTS_AVAILABLE:
            self._show_import_error()
            return
        
        # Initialize systems
        self.initialize_game_systems()
        
        print("🚀 Starting Enhanced SF3 Demo...")
        print("Features showcased:")
        print("  - Training mode with real-time frame data")
        print("  - Advanced AI with personality system")
        print("  - Visual effects and screen shake")
        print("  - Network play foundation")
        print("  - Complete SF3 authenticity")
        
        # Main loop
        while self.running:
            await self._handle_events()
            await self._update()
            self._draw()
            
            # Cap framerate
            self.clock.tick(self.fps)
        
        pygame.quit()
    
    async def _handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_1:
                    self.current_mode = DemoMode.TRAINING
                elif event.key == pygame.K_2:
                    self.current_mode = DemoMode.AI_BATTLE
                elif event.key == pygame.K_3:
                    self.current_mode = DemoMode.NETWORK_DEMO
                elif event.key == pygame.K_4:
                    self.current_mode = DemoMode.EFFECTS_SHOWCASE
                elif event.key == pygame.K_d:
                    self.show_debug_info = not self.show_debug_info
                elif event.key == pygame.K_a:
                    self.auto_switch_modes = not self.auto_switch_modes
                elif event.key == pygame.K_SPACE:
                    # Trigger demo effects
                    await self._trigger_demo_effects()
    
    async def _update(self):
        """Update demo systems"""
        
        self.demo_timer += 1
        
        # Auto-switch modes
        if self.auto_switch_modes and self.demo_timer % self.mode_switch_interval == 0:
            self._switch_to_next_mode()
        
        # Update game manager
        self.game_manager.update_frame()
        
        # Update based on current mode
        if self.current_mode == DemoMode.TRAINING:
            await self._update_training_mode()
        elif self.current_mode == DemoMode.AI_BATTLE:
            await self._update_ai_battle()
        elif self.current_mode == DemoMode.NETWORK_DEMO:
            await self._update_network_demo()
        elif self.current_mode == DemoMode.EFFECTS_SHOWCASE:
            await self._update_effects_showcase()
        
        # Update effects manager
        self.effects_manager.update()
        
        # Simulate some combat for demo
        await self._simulate_demo_combat()
    
    async def _update_training_mode(self):
        """Update training mode demo"""
        if self.training_mode:
            self.training_mode.update(self.player1, self.player2)
    
    async def _update_ai_battle(self):
        """Update AI battle demo"""
        if self.ai_system:
            # Create game situation
            distance = abs(self.player1.work.position.x - self.player2.work.position.x)
            situation = GameSituation(
                distance=distance,
                range_category="mid" if distance < 200 else "far",
                my_health_ratio=self.player2.work.vitality / 1050,
                opponent_health_ratio=self.player1.work.vitality / 1050,
                frame_advantage=0
            )
            
            # Get AI decision
            direction, buttons = self.ai_system.update(self.player2, self.player1, situation)
            
            # Apply AI input (simplified)
            # In full implementation, this would go through the input system
    
    async def _update_network_demo(self):
        """Update network demo"""
        if self.network_manager:
            await self.network_manager.update()
    
    async def _update_effects_showcase(self):
        """Update effects showcase"""
        # Randomly trigger effects for showcase
        if random.random() < 0.02:  # 2% chance per frame
            await self._trigger_demo_effects()
    
    async def _simulate_demo_combat(self):
        """Simulate combat for demo purposes"""
        
        # Randomly trigger hits for effect demonstration
        if random.random() < 0.005:  # 0.5% chance per frame
            # Simulate hit
            hit_position = (
                (self.player1.work.position.x + self.player2.work.position.x) / 2,
                (self.player1.work.position.y + self.player2.work.position.y) / 2
            )
            
            damage = random.randint(50, 150)
            is_counter = random.random() < 0.1
            is_blocked = random.random() < 0.3
            
            self.effects_manager.create_hit_effect(
                position=hit_position,
                damage=damage,
                hit_level=SF3HitLevel.MID,
                is_counter=is_counter,
                is_blocked=is_blocked
            )
            
            # Update combo counter
            if not is_blocked:
                self.player1.increment_combo()
                
                if self.player1.combo_count >= 3:
                    self.effects_manager.create_combo_effect(
                        position=hit_position,
                        hit_count=self.player1.combo_count,
                        damage=damage * self.player1.combo_count
                    )
        
        # Reset combo occasionally
        if random.random() < 0.01:
            self.player1.reset_combo()
    
    async def _trigger_demo_effects(self):
        """Trigger various effects for demonstration"""
        
        center_x = self.screen_size[0] // 2
        center_y = self.screen_size[1] // 2
        
        # Random effect type
        effect_type = random.choice([
            "hit", "parry", "super", "combo"
        ])
        
        if effect_type == "hit":
            self.effects_manager.create_hit_effect(
                position=(center_x + random.randint(-100, 100), center_y + random.randint(-50, 50)),
                damage=random.randint(80, 200),
                hit_level=SF3HitLevel.MID,
                is_counter=random.random() < 0.2
            )
        
        elif effect_type == "parry":
            self.effects_manager.create_parry_effect(
                position=(center_x + random.randint(-50, 50), center_y + random.randint(-25, 25))
            )
        
        elif effect_type == "super":
            self.effects_manager.create_super_flash(
                color=(random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
            )
        
        elif effect_type == "combo":
            self.effects_manager.create_combo_effect(
                position=(center_x, center_y - 50),
                hit_count=random.randint(3, 8),
                damage=random.randint(200, 500)
            )
    
    def _switch_to_next_mode(self):
        """Switch to next demo mode"""
        modes = [DemoMode.TRAINING, DemoMode.AI_BATTLE, DemoMode.NETWORK_DEMO, DemoMode.EFFECTS_SHOWCASE]
        current_index = modes.index(self.current_mode)
        next_index = (current_index + 1) % len(modes)
        self.current_mode = modes[next_index]
        
        print(f"Demo mode switched to: {self.current_mode}")
    
    def _draw(self):
        """Draw demo"""
        
        # Clear screen
        self.screen.fill((20, 20, 40))  # Dark blue background
        
        # Draw stage background (simplified)
        self._draw_stage_background()
        
        # Draw characters (simplified)
        self._draw_characters()
        
        # Draw mode-specific elements
        if self.current_mode == DemoMode.TRAINING:
            self._draw_training_mode()
        elif self.current_mode == DemoMode.AI_BATTLE:
            self._draw_ai_battle()
        elif self.current_mode == DemoMode.NETWORK_DEMO:
            self._draw_network_demo()
        elif self.current_mode == DemoMode.EFFECTS_SHOWCASE:
            self._draw_effects_showcase()
        
        # Draw effects (this applies screen shake automatically)
        camera_offset = self.effects_manager.get_camera_offset()
        
        # Apply camera shake to main drawing
        shake_surface = pygame.Surface(self.screen_size)
        shake_surface.blit(self.screen, camera_offset)
        self.screen.blit(shake_surface, (0, 0))
        
        # Draw effects on top
        self.effects_manager.draw(self.screen)
        
        # Draw UI
        self._draw_ui()
        
        # Draw debug info
        if self.show_debug_info:
            self._draw_debug_info()
        
        pygame.display.flip()
    
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
            
            # Health bar
            health_ratio = self.player1.work.vitality / 1050
            health_width = int(200 * health_ratio)
            health_rect = pygame.Rect(50, 50, health_width, 20)
            pygame.draw.rect(self.screen, (255, 100, 100), health_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), pygame.Rect(50, 50, 200, 20), 2)
        
        if self.player2:
            # Player 2 (red)
            player2_rect = pygame.Rect(
                self.player2.work.position.x - 20,
                self.player2.work.position.y - 80,
                40, 80
            )
            pygame.draw.rect(self.screen, (255, 100, 100), player2_rect)
            
            # Health bar
            health_ratio = self.player2.work.vitality / 1050
            health_width = int(200 * health_ratio)
            health_rect = pygame.Rect(self.screen_size[0] - 250, 50, health_width, 20)
            pygame.draw.rect(self.screen, (255, 100, 100), health_rect)
            pygame.draw.rect(self.screen, (255, 255, 255), pygame.Rect(self.screen_size[0] - 250, 50, 200, 20), 2)
    
    def _draw_training_mode(self):
        """Draw training mode elements"""
        if self.training_mode:
            self.training_mode.draw(self.screen)
    
    def _draw_ai_battle(self):
        """Draw AI battle elements"""
        # AI status
        ai_text = "Advanced AI Battle Mode"
        ai_surface = self.font.render(ai_text, True, (255, 255, 100))
        self.screen.blit(ai_surface, (10, 100))
        
        if self.ai_system:
            # AI personality display
            personality = self.ai_system.personality
            personality_text = f"AI: Aggression={personality.aggression:.1f}, Defense={personality.defensive_style:.1f}"
            personality_surface = self.small_font.render(personality_text, True, (200, 200, 200))
            self.screen.blit(personality_surface, (10, 125))
            
            # AI state
            state_text = f"AI State: {self.ai_system.current_state.value}"
            state_surface = self.small_font.render(state_text, True, (200, 200, 200))
            self.screen.blit(state_surface, (10, 145))
    
    def _draw_network_demo(self):
        """Draw network demo elements"""
        network_text = "Network Play Foundation Demo"
        network_surface = self.font.render(network_text, True, (100, 255, 100))
        self.screen.blit(network_surface, (10, 100))
        
        if self.network_manager:
            # Connection status
            status_text = f"Network State: {self.network_manager.state.value}"
            status_surface = self.small_font.render(status_text, True, (200, 200, 200))
            self.screen.blit(status_surface, (10, 125))
            
            # Connection stats
            stats = self.network_manager.connection_stats
            stats_text = f"Ping: {stats.ping:.1f}ms, Quality: {stats.connection_quality}"
            stats_surface = self.small_font.render(stats_text, True, (200, 200, 200))
            self.screen.blit(stats_surface, (10, 145))
    
    def _draw_effects_showcase(self):
        """Draw effects showcase elements"""
        effects_text = "Visual Effects Showcase"
        effects_surface = self.font.render(effects_text, True, (255, 100, 255))
        self.screen.blit(effects_surface, (10, 100))
        
        # Effects stats
        active_effects = len(self.effects_manager.active_effects)
        particles = len(self.effects_manager.particle_system.particles)
        
        stats_text = f"Active Effects: {active_effects}, Particles: {particles}"
        stats_surface = self.small_font.render(stats_text, True, (200, 200, 200))
        self.screen.blit(stats_surface, (10, 125))
        
        # Screen shake info
        shake_intensity = self.effects_manager.screen_shake.intensity
        shake_text = f"Screen Shake: {shake_intensity:.1f}"
        shake_surface = self.small_font.render(shake_text, True, (200, 200, 200))
        self.screen.blit(shake_surface, (10, 145))
    
    def _draw_ui(self):
        """Draw main UI elements"""
        
        # Title
        title_text = "SF3:3S Enhanced Demo - Phase 2 Features"
        title_surface = self.title_font.render(title_text, True, (255, 255, 255))
        title_rect = title_surface.get_rect()
        title_rect.centerx = self.screen_size[0] // 2
        title_rect.y = 10
        self.screen.blit(title_surface, title_rect)
        
        # Mode indicator
        mode_text = f"Mode: {self.current_mode.replace('_', ' ').title()}"
        mode_surface = self.font.render(mode_text, True, (255, 255, 100))
        self.screen.blit(mode_surface, (10, self.screen_size[1] - 100))
        
        # Controls
        controls = [
            "1-4: Switch modes",
            "Space: Trigger effects",
            "D: Toggle debug",
            "A: Toggle auto-switch",
            "ESC: Exit"
        ]
        
        for i, control in enumerate(controls):
            control_surface = self.small_font.render(control, True, (200, 200, 200))
            self.screen.blit(control_surface, (10, self.screen_size[1] - 80 + i * 15))
    
    def _draw_debug_info(self):
        """Draw debug information"""
        debug_info = [
            f"FPS: {self.clock.get_fps():.1f}",
            f"Frame: {self.game_manager.current_frame if self.game_manager else 0}",
            f"Demo Timer: {self.demo_timer}",
            f"Auto Switch: {self.auto_switch_modes}",
            f"Effects: {len(self.effects_manager.active_effects) if self.effects_manager else 0}",
            f"Particles: {len(self.effects_manager.particle_system.particles) if self.effects_manager else 0}"
        ]
        
        # Debug panel
        debug_panel = pygame.Rect(self.screen_size[0] - 200, self.screen_size[1] - 150, 190, 140)
        pygame.draw.rect(self.screen, (0, 0, 0, 180), debug_panel)
        pygame.draw.rect(self.screen, (255, 255, 255), debug_panel, 1)
        
        for i, info in enumerate(debug_info):
            info_surface = self.small_font.render(info, True, (255, 255, 255))
            self.screen.blit(info_surface, (debug_panel.x + 5, debug_panel.y + 5 + i * 20))
    
    def _show_import_error(self):
        """Show import error screen"""
        self.screen.fill((40, 20, 20))
        
        error_text = "Enhanced Features Not Available"
        error_surface = self.title_font.render(error_text, True, (255, 100, 100))
        error_rect = error_surface.get_rect()
        error_rect.center = (self.screen_size[0] // 2, self.screen_size[1] // 2 - 50)
        self.screen.blit(error_surface, error_rect)
        
        help_text = "Please install dependencies: uv add pydantic pydantic-settings pyyaml"
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
    demo = EnhancedSF3Demo()
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main())
