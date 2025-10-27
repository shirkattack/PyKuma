"""Core game class managing game state and main loop."""

import pygame
from typing import Dict
from street_fighter_3rd.data.enums import GameState
from street_fighter_3rd.data.constants import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    STAGE_FLOOR,
    COLOR_BLACK,
    COLOR_WHITE,
    COLOR_HEALTH_BAR,
    COLOR_RED,
    COLOR_BLUE,
    DEBUG_MODE,
    SHOW_FRAME_DATA,
    MAX_HEALTH,
)
from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.systems.input_system import InputSystem
from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter
from street_fighter_3rd.systems.vfx import VFXManager
from street_fighter_3rd.core.round_manager import RoundManager
from street_fighter_3rd.core.game_modes import GameModeManager, GameMode


class Game:
    """Main game class."""

    def __init__(self, screen: pygame.Surface, game_mode_manager: GameModeManager = None):
        """Initialize the game.

        Args:
            screen: Pygame display surface
            game_mode_manager: Optional game mode manager for different play modes
        """
        self.screen = screen
        self.frame_count = 0

        # Initialize game mode manager
        self.game_mode_manager = game_mode_manager or GameModeManager()
        self.config = self.game_mode_manager.get_config()

        # Initialize systems
        self.input_system = InputSystem()
        self.collision_system = SF3CollisionAdapter()
        self.vfx_manager = VFXManager()
        self.round_manager = RoundManager()

        # Load stage background
        try:
            self.stage_background = pygame.image.load("assets/stages/ryu-stage.gif").convert()
        except:
            print("Warning: Could not load stage background")
            self.stage_background = None

        # Create characters
        self.player1 = Akuma(200, STAGE_FLOOR, player_number=1)
        self.player1.input = self.input_system.player1

        self.player2 = Akuma(440, STAGE_FLOOR, player_number=2)
        self.player2.input = self.input_system.player2

        # Start new match
        self.round_manager.start_new_match()

        # Debug info
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

    def handle_event(self, event: pygame.event.Event):
        """Handle pygame events.

        Args:
            event: Pygame event
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Toggle pause or quit
                pass
            elif event.key == pygame.K_F1 and DEBUG_MODE:
                # Toggle debug display
                pass
            elif event.key == pygame.K_RETURN:
                # Handle "Play Again" on continue screen
                if self.round_manager.game_state == GameState.CONTINUE_SCREEN:
                    self._reset_for_new_match()

    def update(self, dt: float):
        """Update game state.

        Args:
            dt: Delta time in seconds
        """
        self.frame_count += 1

        # Apply training mode features
        self._apply_infinite_health()

        # Update round manager (skip if no rounds mode is enabled)
        if not self.config.no_rounds:
            self.round_manager.update(self.player1.health, self.player2.health)

        # Only update gameplay during PRE_ROUND and FIGHTING states (or always if no rounds)
        if self.config.no_rounds:
            # In no-rounds mode, always update as if fighting
            self._update_fight(dt)
        elif self.round_manager.game_state == GameState.PRE_ROUND:
            self._update_pre_round(dt)
        elif self.round_manager.game_state == GameState.FIGHTING:
            self._update_fight(dt)
        elif self.round_manager.game_state == GameState.PAUSE:
            pass  # No updates while paused

    def _update_pre_round(self, dt: float):
        """Update pre-round state (characters frozen).

        Args:
            dt: Delta time in seconds
        """
        # Update facing so characters look at each other
        self.player1._update_facing(self.player2)
        self.player2._update_facing(self.player1)

        # Don't process input or update characters during pre-round freeze

    def _update_fight(self, dt: float):
        """Update fighting state.

        Args:
            dt: Delta time in seconds
        """
        # Update facing FIRST (before input processing) using current positions
        self.player1._update_facing(self.player2)
        self.player2._update_facing(self.player1)

        # Update input system with correct facing
        self.input_system.update(
            player1_facing_right=self.player1.is_facing_right(),
            player2_facing_right=self.player2.is_facing_right()
        )

        # Update parry inputs for SF3 collision system
        # TODO: Re-enable once parry system is fully integrated
        # The parry system needs to be called AFTER check_attack_collision creates player_works
        # if hasattr(self.collision_system, 'update_parry_inputs'):
        #     try:
        #         # Convert input system state to parry input format
        #         p1_inputs = self._get_parry_inputs_for_player(1)
        #         p2_inputs = self._get_parry_inputs_for_player(2)
        #
        #         self.collision_system.update_parry_inputs(self.player1, p1_inputs)
        #         self.collision_system.update_parry_inputs(self.player2, p2_inputs)
        #     except Exception as e:
        #         # Graceful fallback if parry system has issues
        #         print(f"Warning: Parry system error: {e}")
        #         pass

        # Update characters (this will call _update_facing again in parent, but that's ok)
        self.player1.update(self.player2)
        self.player2.update(self.player1)

        # Check collisions and spawn hit sparks
        self.collision_system.check_attack_collision(self.player1, self.player2, self.vfx_manager)
        self.collision_system.check_attack_collision(self.player2, self.player1, self.vfx_manager)

        # Update VFX
        self.vfx_manager.update()

    def _reset_for_new_match(self):
        """Reset characters and start a new match."""
        # Reset character positions and health
        self.player1.x = 200
        self.player1.y = STAGE_FLOOR
        self.player1.health = MAX_HEALTH
        self.player1.velocity_x = 0
        self.player1.velocity_y = 0

        self.player2.x = 440
        self.player2.y = STAGE_FLOOR
        self.player2.health = MAX_HEALTH
        self.player2.velocity_x = 0
        self.player2.velocity_y = 0

        # Start new match
        self.round_manager.start_new_match()

    def render(self):
        """Render the current frame."""
        # Clear screen
        self.screen.fill(COLOR_BLACK)

        # Render fight scene for all gameplay states
        if self.round_manager.game_state in [GameState.PRE_ROUND, GameState.FIGHTING,
                                               GameState.ROUND_END, GameState.MATCH_END]:
            self._render_fight()
        elif self.round_manager.game_state == GameState.CONTINUE_SCREEN:
            self._render_continue_screen()

        # Render debug info
        if DEBUG_MODE:
            self._render_debug()

    def _render_fight(self):
        """Render fighting game scene."""
        # Draw stage background
        if self.stage_background:
            self.screen.blit(self.stage_background, (0, 0))
        else:
            # Fallback: Draw stage floor line
            pygame.draw.line(
                self.screen,
                COLOR_WHITE,
                (0, STAGE_FLOOR),
                (SCREEN_WIDTH, STAGE_FLOOR),
                2
            )

        # Render characters
        self.player1.render(self.screen)
        self.player2.render(self.screen)

        # Render VFX (hit sparks, etc.)
        self.vfx_manager.render(self.screen)

        # Render collision debug (hitboxes/hurtboxes)
        self.collision_system.render_debug(
            self.screen, 
            show_hitboxes=self.config.show_hitboxes,
            show_hurtboxes=self.config.show_hurtboxes
        )

        # Render UI
        self._render_ui()

    def _render_ui(self):
        """Render game UI (health bars, timer, round indicators, etc.)."""
        # Player 1 health bar
        health_bar_width = 250
        health_bar_height = 20
        p1_health_percent = max(0, self.player1.health / MAX_HEALTH)

        # P1 Health background
        pygame.draw.rect(self.screen, (50, 50, 50),
                        (20, 20, health_bar_width, health_bar_height))
        # P1 Health foreground
        pygame.draw.rect(self.screen, COLOR_RED,
                        (20, 20, int(health_bar_width * p1_health_percent), health_bar_height))
        # P1 Health border
        pygame.draw.rect(self.screen, COLOR_WHITE,
                        (20, 20, health_bar_width, health_bar_height), 2)

        # P1 Name
        p1_name = self.small_font.render("P1 - AKUMA", True, COLOR_WHITE)
        self.screen.blit(p1_name, (20, 3))

        # Player 2 health bar (right side)
        p2_health_percent = max(0, self.player2.health / MAX_HEALTH)
        p2_x = SCREEN_WIDTH - 20 - health_bar_width

        # P2 Health background
        pygame.draw.rect(self.screen, (50, 50, 50),
                        (p2_x, 20, health_bar_width, health_bar_height))
        # P2 Health foreground
        pygame.draw.rect(self.screen, COLOR_BLUE,
                        (p2_x, 20, int(health_bar_width * p2_health_percent), health_bar_height))
        # P2 Health border
        pygame.draw.rect(self.screen, COLOR_WHITE,
                        (p2_x, 20, health_bar_width, health_bar_height), 2)

        # P2 Name
        p2_name = self.small_font.render("AKUMA - P2", True, COLOR_WHITE)
        self.screen.blit(p2_name, (p2_x + health_bar_width - p2_name.get_width(), 3))

        # Timer (centered at top)
        timer_text = self.font.render(self.round_manager.get_timer_display(), True, COLOR_WHITE)
        timer_x = SCREEN_WIDTH // 2 - timer_text.get_width() // 2
        self.screen.blit(timer_text, (timer_x, 10))

        # Round wins indicators
        p1_wins, p2_wins = self.round_manager.get_round_wins()

        # P1 round wins (left of timer)
        win_circle_radius = 8
        for i in range(p1_wins):
            pygame.draw.circle(self.screen, COLOR_RED, (timer_x - 40 - (i * 20), 25), win_circle_radius)

        # P2 round wins (right of timer)
        for i in range(p2_wins):
            pygame.draw.circle(self.screen, COLOR_BLUE, (timer_x + timer_text.get_width() + 40 + (i * 20), 25), win_circle_radius)

        # Round/state text overlays
        if self.round_manager.game_state == GameState.PRE_ROUND:
            # Show "ROUND X" and then "FIGHT!"
            if self.round_manager.state_frame < 60:
                round_text = self.font.render(self.round_manager.get_round_display(), True, COLOR_WHITE)
                self.screen.blit(round_text, (SCREEN_WIDTH // 2 - round_text.get_width() // 2, SCREEN_HEIGHT // 2 - 30))
            else:
                fight_text = self.font.render("FIGHT!", True, COLOR_WHITE)
                self.screen.blit(fight_text, (SCREEN_WIDTH // 2 - fight_text.get_width() // 2, SCREEN_HEIGHT // 2 - 30))

        elif self.round_manager.game_state == GameState.ROUND_END:
            # Show round result
            result_text = self.font.render(self.round_manager.get_round_result_text(), True, COLOR_WHITE)
            self.screen.blit(result_text, (SCREEN_WIDTH // 2 - result_text.get_width() // 2, SCREEN_HEIGHT // 2 - 30))

        elif self.round_manager.game_state == GameState.MATCH_END:
            # Show match winner
            winner_text = self.font.render(self.round_manager.get_match_winner_text(), True, COLOR_WHITE)
            self.screen.blit(winner_text, (SCREEN_WIDTH // 2 - winner_text.get_width() // 2, SCREEN_HEIGHT // 2 - 30))

    def _render_continue_screen(self):
        """Render the continue/play again screen."""
        # Dark background
        self.screen.fill((20, 20, 20))

        # Match result
        winner_text = self.font.render(self.round_manager.get_match_winner_text(), True, COLOR_WHITE)
        self.screen.blit(winner_text, (SCREEN_WIDTH // 2 - winner_text.get_width() // 2, SCREEN_HEIGHT // 2 - 60))

        # Play again prompt
        play_again = self.font.render("Play Again?", True, COLOR_WHITE)
        self.screen.blit(play_again, (SCREEN_WIDTH // 2 - play_again.get_width() // 2, SCREEN_HEIGHT // 2))

        # Instructions
        instructions = self.small_font.render("Press ENTER to continue", True, (150, 150, 150))
        self.screen.blit(instructions, (SCREEN_WIDTH // 2 - instructions.get_width() // 2, SCREEN_HEIGHT // 2 + 40))

    def _render_debug(self):
        """Render debug information."""
        if self.config.show_frame_data or SHOW_FRAME_DATA:
            y_offset = SCREEN_HEIGHT - 120

            # Show frame count
            frame_text = self.small_font.render(f"Frame: {self.frame_count}", True, COLOR_WHITE)
            self.screen.blit(frame_text, (10, y_offset))

            # P1 State
            p1_state = self.small_font.render(f"P1: {self.player1.state.name}", True, COLOR_RED)
            self.screen.blit(p1_state, (10, y_offset + 20))

            # P1 Position
            p1_pos = self.small_font.render(f"   Pos: ({int(self.player1.x)}, {int(self.player1.y)})", True, COLOR_RED)
            self.screen.blit(p1_pos, (10, y_offset + 40))

            # P2 State
            p2_state = self.small_font.render(f"P2: {self.player2.state.name}", True, COLOR_BLUE)
            self.screen.blit(p2_state, (10, y_offset + 60))

            # P2 Position
            p2_pos = self.small_font.render(f"   Pos: ({int(self.player2.x)}, {int(self.player2.y)})", True, COLOR_BLUE)
            self.screen.blit(p2_pos, (10, y_offset + 80))

            # Combo information (if SF3 collision system is active)
            if hasattr(self.collision_system, 'get_combo_info'):
                p1_combo = self.collision_system.get_combo_info(1)
                p2_combo = self.collision_system.get_combo_info(2)
                
                if p1_combo['active'] and p1_combo['count'] > 1:
                    combo_text = f"P1 COMBO: {p1_combo['count']} hits, {p1_combo['damage']} damage"
                    combo_surface = self.small_font.render(combo_text, True, COLOR_RED)
                    self.screen.blit(combo_surface, (10, y_offset + 100))
                
                if p2_combo['active'] and p2_combo['count'] > 1:
                    combo_text = f"P2 COMBO: {p2_combo['count']} hits, {p2_combo['damage']} damage"
                    combo_surface = self.small_font.render(combo_text, True, COLOR_BLUE)
                    self.screen.blit(combo_surface, (10, y_offset + 120))

            # Controls reminder
            controls = self.small_font.render("P1: WASD + JKLUIO | P2: Arrows + NumPad", True, (150, 150, 150))
            self.screen.blit(controls, (SCREEN_WIDTH // 2 - controls.get_width() // 2, SCREEN_HEIGHT - 20))

    def _get_parry_inputs_for_player(self, player_num: int) -> Dict[str, bool]:
        """Convert input system state to parry input format for a player"""
        from street_fighter_3rd.data.enums import InputDirection

        if player_num == 1:
            player_input = self.input_system.player1
            direction = player_input.get_direction()
        else:
            player_input = self.input_system.player2
            direction = player_input.get_direction()

        # Check if direction is forward or down-forward
        # Note: InputDirection already accounts for facing direction (handled by PlayerInput.update)
        forward = direction in [InputDirection.FORWARD, InputDirection.UP_FORWARD, InputDirection.DOWN_FORWARD]
        down_forward = direction == InputDirection.DOWN_FORWARD

        return {
            'forward': forward,
            'down_forward': down_forward
        }

    def reset_positions(self):
        """Reset character positions to starting positions (training mode)."""
        from street_fighter_3rd.data.enums import CharacterState
        
        self.player1.x = 200
        self.player1.y = STAGE_FLOOR
        self.player1.velocity_x = 0
        self.player1.velocity_y = 0
        self.player1._transition_to_state(CharacterState.STANDING)
        
        self.player2.x = 440
        self.player2.y = STAGE_FLOOR
        self.player2.velocity_x = 0
        self.player2.velocity_y = 0
        self.player2._transition_to_state(CharacterState.STANDING)
        
        print("Positions reset")

    def reset_health(self):
        """Reset both players' health to maximum (training mode)."""
        if self.config.infinite_health:
            self.player1.health = self.player1.max_health if hasattr(self.player1, 'max_health') else MAX_HEALTH
            self.player2.health = self.player2.max_health if hasattr(self.player2, 'max_health') else MAX_HEALTH
            print("Health reset")

    def _apply_infinite_health(self):
        """Apply infinite health if enabled."""
        if self.config.infinite_health:
            # Store original health values if not already stored
            if not hasattr(self.player1, 'max_health'):
                self.player1.max_health = self.player1.health
            if not hasattr(self.player2, 'max_health'):
                self.player2.max_health = self.player2.health
                
            # Keep health at maximum
            self.player1.health = self.player1.max_health
            self.player2.health = self.player2.max_health
