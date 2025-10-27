"""Main menu system for Street Fighter 3rd Strike."""

import pygame
import sys
from enum import Enum, auto
from typing import Optional, Callable

from street_fighter_3rd.data.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, COLOR_RED, COLOR_BLUE, COLOR_YELLOW
)
from street_fighter_3rd.core.game_modes import GameMode, GameModeManager


class MenuState(Enum):
    """Different menu screens."""
    MAIN = auto()
    CONTROLS = auto()
    MOVES = auto()
    MODE_SELECT = auto()
    SETTINGS = auto()


class MenuItem:
    """Represents a menu item with text and action."""
    
    def __init__(self, text: str, action: Optional[Callable] = None, submenu: Optional[MenuState] = None):
        self.text = text
        self.action = action
        self.submenu = submenu
        self.selected = False
        
    def execute(self):
        """Execute the menu item's action or navigate to submenu."""
        if self.action:
            return self.action()
        elif self.submenu:
            return self.submenu
        return None


class MainMenu:
    """Main menu system with navigation and different screens."""
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 24)
        
        self.current_state = MenuState.MAIN
        self.selected_index = 0
        self.game_mode_manager = GameModeManager()
        
        # Menu definitions
        self.menus = {
            MenuState.MAIN: [
                MenuItem("START GAME", self._start_normal_game),
                MenuItem("TRAINING MODE", self._start_training_mode),
                MenuItem("DEV MODE", self._start_dev_mode),
                MenuItem("CONTROLS", submenu=MenuState.CONTROLS),
                MenuItem("MOVES LIST", submenu=MenuState.MOVES),
                MenuItem("MODE SELECT", submenu=MenuState.MODE_SELECT),
                MenuItem("EXIT GAME", self._exit_game)
            ],
            MenuState.CONTROLS: [
                MenuItem("BACK TO MAIN", submenu=MenuState.MAIN)
            ],
            MenuState.MOVES: [
                MenuItem("BACK TO MAIN", submenu=MenuState.MAIN)
            ],
            MenuState.MODE_SELECT: [
                MenuItem("NORMAL MODE", self._select_normal_mode),
                MenuItem("TRAINING MODE", self._select_training_mode),
                MenuItem("DEV MODE", self._select_dev_mode),
                MenuItem("VERSUS MODE", self._select_versus_mode),
                MenuItem("DEMO MODE", self._select_demo_mode),
                MenuItem("BACK TO MAIN", submenu=MenuState.MAIN)
            ]
        }
        
        # Return values for game state
        self.start_game = False
        self.selected_mode = GameMode.NORMAL
        self.quit_game = False
        
    def handle_event(self, event):
        """Handle menu input events."""
        if event.type == pygame.KEYDOWN:
            current_menu = self.menus[self.current_state]
            
            if event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1) % len(current_menu)
                
            elif event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(current_menu)
                
            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                selected_item = current_menu[self.selected_index]
                result = selected_item.execute()
                
                if isinstance(result, MenuState):
                    self.current_state = result
                    self.selected_index = 0
                    
            elif event.key == pygame.K_ESCAPE:
                if self.current_state != MenuState.MAIN:
                    self.current_state = MenuState.MAIN
                    self.selected_index = 0
                else:
                    self.quit_game = True
                    
    def render(self):
        """Render the current menu screen."""
        self.screen.fill((20, 20, 30))  # Dark background
        
        if self.current_state == MenuState.MAIN:
            self._render_main_menu()
        elif self.current_state == MenuState.CONTROLS:
            self._render_controls_screen()
        elif self.current_state == MenuState.MOVES:
            self._render_moves_screen()
        elif self.current_state == MenuState.MODE_SELECT:
            self._render_mode_select_screen()
            
    def _render_main_menu(self):
        """Render the main menu."""
        # Title
        title = self.font_large.render("STREET FIGHTER III: 3RD STRIKE", True, COLOR_YELLOW)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title, title_rect)
        
        # Subtitle
        subtitle = self.font_medium.render("Python Edition", True, COLOR_WHITE)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 140))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Current mode indicator
        mode_text = f"Current Mode: {self.game_mode_manager.current_mode.name}"
        mode_surface = self.font_small.render(mode_text, True, COLOR_BLUE)
        mode_rect = mode_surface.get_rect(center=(SCREEN_WIDTH // 2, 180))
        self.screen.blit(mode_surface, mode_rect)
        
        # Menu items
        menu_items = self.menus[MenuState.MAIN]
        start_y = 250
        
        for i, item in enumerate(menu_items):
            color = COLOR_RED if i == self.selected_index else COLOR_WHITE
            text_surface = self.font_medium.render(item.text, True, color)
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, start_y + i * 50))
            self.screen.blit(text_surface, text_rect)
            
        # Instructions
        instructions = [
            "↑↓ Navigate  ENTER Select  ESC Back/Quit",
            "Made with ❤️ by fighting game fans"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.font_small.render(instruction, True, COLOR_WHITE)
            text_rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60 + i * 25))
            self.screen.blit(text, text_rect)
            
    def _render_controls_screen(self):
        """Render the controls help screen."""
        title = self.font_large.render("CONTROLS", True, COLOR_YELLOW)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title, title_rect)
        
        controls_text = [
            "PLAYER 1:",
            "Movement: W/A/S/D (Up/Left/Down/Right)",
            "Attacks: J/K/L (Light/Medium/Heavy Punch)",
            "Kicks: U/I/O (Light/Medium/Heavy Kick)",
            "Double-tap A/D for dash",
            "",
            "PLAYER 2:",
            "Movement: Arrow Keys",
            "Attacks: NumPad 1/2/3 (Light/Medium/Heavy Punch)",
            "Kicks: NumPad 4/5/6 (Light/Medium/Heavy Kick)",
            "Double-tap ←/→ for dash",
            "",
            "SPECIAL MOVES:",
            "Hadoken: ↓↘→ + Punch",
            "Shoryuken: →↓↘ + Punch (coming soon)",
            "Tatsumaki: ↓↙← + Kick (coming soon)",
            "",
            "TRAINING MODE HOTKEYS:",
            "F1: Toggle Hitboxes",
            "F2: Toggle Frame Data",
            "F3: Reset Positions",
            "R: Reset Health"
        ]
        
        start_y = 100
        for i, line in enumerate(controls_text):
            color = COLOR_YELLOW if line.endswith(":") else COLOR_WHITE
            if line == "":
                continue
            text = self.font_small.render(line, True, color)
            self.screen.blit(text, (50, start_y + i * 20))
            
        # Back instruction
        back_text = self.font_small.render("ESC: Back to Main Menu", True, COLOR_RED)
        back_rect = back_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30))
        self.screen.blit(back_text, back_rect)
        
    def _render_moves_screen(self):
        """Render the moves list screen."""
        title = self.font_large.render("AKUMA MOVES", True, COLOR_YELLOW)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title, title_rect)
        
        moves_text = [
            "NORMAL ATTACKS:",
            "Light Punch (LP) - Fast jab, 12 frames",
            "Medium Punch (MP) - Balanced attack, 18 frames", 
            "Heavy Punch (HP) - Strong uppercut, 25 frames",
            "Light Kick (LK) - Quick kick, 15 frames",
            "Medium Kick (MK) - Mid-range kick, 27 frames",
            "Heavy Kick (HK) - Powerful kick, 42 frames",
            "",
            "SPECIAL MOVES:",
            "Gohadoken - ↓↘→ + P",
            "  Light: Slow fireball (7 px/frame)",
            "  Medium: Medium fireball (9 px/frame)",
            "  Heavy: Fast fireball (11 px/frame)",
            "",
            "Goshoryuken - →↓↘ + P (Coming Soon)",
            "  Anti-air dragon punch with invincibility",
            "",
            "Tatsumaki Senpukyaku - ↓↙← + K (Coming Soon)",
            "  Hurricane kick with multiple hits",
            "",
            "FRAME DATA:",
            "Startup: Frames before attack becomes active",
            "Active: Frames where attack can hit",
            "Recovery: Frames after attack until neutral",
            "",
            "AKUMA STATS:",
            "Health: 145 HP (Low)",
            "Walk Speed: 3.2 px/frame (Fast)"
        ]
        
        start_y = 100
        for i, line in enumerate(moves_text):
            color = COLOR_YELLOW if line.endswith(":") else COLOR_WHITE
            if line.startswith("  "):
                color = COLOR_BLUE
            if line == "":
                continue
            text = self.font_small.render(line, True, color)
            self.screen.blit(text, (50, start_y + i * 18))
            
        # Back instruction
        back_text = self.font_small.render("ESC: Back to Main Menu", True, COLOR_RED)
        back_rect = back_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30))
        self.screen.blit(back_text, back_rect)
        
    def _render_mode_select_screen(self):
        """Render the mode selection screen."""
        title = self.font_large.render("SELECT GAME MODE", True, COLOR_YELLOW)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title, title_rect)
        
        # Current mode
        current_text = f"Current: {self.game_mode_manager.current_mode.name}"
        current_surface = self.font_medium.render(current_text, True, COLOR_BLUE)
        current_rect = current_surface.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(current_surface, current_rect)
        
        # Mode descriptions
        descriptions = {
            0: "Standard fighting game experience",
            1: "Practice with infinite health and debug tools",
            2: "Full development mode with all debug features", 
            3: "Local 2-player versus matches",
            4: "AI demonstration mode",
            5: ""  # Back button
        }
        
        # Menu items
        menu_items = self.menus[MenuState.MODE_SELECT]
        start_y = 150
        
        for i, item in enumerate(menu_items):
            color = COLOR_RED if i == self.selected_index else COLOR_WHITE
            text_surface = self.font_medium.render(item.text, True, color)
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, start_y + i * 60))
            self.screen.blit(text_surface, text_rect)
            
            # Show description for selected item
            if i == self.selected_index and i in descriptions and descriptions[i]:
                desc_surface = self.font_small.render(descriptions[i], True, COLOR_YELLOW)
                desc_rect = desc_surface.get_rect(center=(SCREEN_WIDTH // 2, start_y + i * 60 + 25))
                self.screen.blit(desc_surface, desc_rect)
                
    # Menu action methods
    def _start_normal_game(self):
        """Start game in normal mode."""
        self.game_mode_manager.set_mode(GameMode.NORMAL)
        self.selected_mode = GameMode.NORMAL
        self.start_game = True
        
    def _start_training_mode(self):
        """Start game in training mode."""
        self.game_mode_manager.set_mode(GameMode.TRAINING)
        self.selected_mode = GameMode.TRAINING
        self.start_game = True
        
    def _start_dev_mode(self):
        """Start game in dev mode."""
        self.game_mode_manager.set_mode(GameMode.DEV)
        self.selected_mode = GameMode.DEV
        self.start_game = True
        
    def _select_normal_mode(self):
        """Select normal mode."""
        self.game_mode_manager.set_mode(GameMode.NORMAL)
        
    def _select_training_mode(self):
        """Select training mode."""
        self.game_mode_manager.set_mode(GameMode.TRAINING)
        
    def _select_dev_mode(self):
        """Select dev mode."""
        self.game_mode_manager.set_mode(GameMode.DEV)
        
    def _select_versus_mode(self):
        """Select versus mode."""
        self.game_mode_manager.set_mode(GameMode.VERSUS)
        
    def _select_demo_mode(self):
        """Select demo mode."""
        self.game_mode_manager.set_mode(GameMode.DEMO)
        
    def _exit_game(self):
        """Exit the game."""
        self.quit_game = True
        
    def should_start_game(self) -> bool:
        """Check if game should start."""
        return self.start_game
        
    def should_quit(self) -> bool:
        """Check if should quit."""
        return self.quit_game
        
    def get_selected_mode(self) -> GameMode:
        """Get the selected game mode."""
        return self.selected_mode
        
    def get_game_mode_manager(self) -> GameModeManager:
        """Get the game mode manager."""
        return self.game_mode_manager
