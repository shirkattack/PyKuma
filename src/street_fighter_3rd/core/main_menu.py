"""Main menu system for Street Fighter 3rd Strike."""

import glob
import os
import pygame
import sys
from enum import Enum, auto
from typing import List, Optional, Callable

from street_fighter_3rd.util.logging_config import get_logger, log_once
import logging

log = get_logger(__name__)

# Animated intro banner shown at the top of the main menu.
INTRO_GLOB = "assets/intro/intro_*.png"
INTRO_MAX_HEIGHT = 180          # banner is scaled to fit within this height
INTRO_TICKS_PER_FRAME = 10      # menu runs at 60 FPS -> ~6 banner fps

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
    """Represents a menu item with text and action.

    `available=False` greys the item out: it's skipped during navigation and
    does nothing when selected. Flip it to True as the feature comes online.
    """

    def __init__(self, text: str, action: Optional[Callable] = None,
                 submenu: Optional[MenuState] = None, available: bool = True):
        self.text = text
        self.action = action
        self.submenu = submenu
        self.available = available
        self.selected = False

    def execute(self):
        """Execute the menu item's action or navigate to submenu."""
        if not self.available:
            return None
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

        # Animated intro banner (frames preloaded + pre-scaled once)
        self.intro_frames = self._load_intro_frames()
        self.intro_timer = 0
        
        # Menu definitions
        self.menus = {
            MenuState.MAIN: [
                MenuItem("START GAME", self._start_normal_game),
                MenuItem("TRAINING MODE", self._start_training_mode),
                MenuItem("DEV MODE", self._start_dev_mode),
                MenuItem("HITBOX VIEWER", self._start_hitbox_viewer_mode),
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
                MenuItem("HITBOX VIEWER", self._select_hitbox_viewer_mode),
                # Not yet distinct from Normal (no CPU AI / no separate versus flow)
                MenuItem("VERSUS MODE", self._select_versus_mode, available=False),
                MenuItem("DEMO MODE", self._select_demo_mode, available=False),
                MenuItem("BACK TO MAIN", submenu=MenuState.MAIN)
            ]
        }

        # Start selection on the first available item of the current menu
        self.selected_index = self._first_available(MenuState.MAIN)

        # Return values for game state
        self.start_game = False
        self.selected_mode = GameMode.NORMAL
        self.quit_game = False

    def _first_available(self, state) -> int:
        """Index of the first selectable item in a menu (0 if none)."""
        for i, item in enumerate(self.menus[state]):
            if item.available:
                return i
        return 0

    def _move_selection(self, step: int):
        """Move selection by step, skipping unavailable items (no infinite loop)."""
        menu = self.menus[self.current_state]
        n = len(menu)
        idx = self.selected_index
        for _ in range(n):
            idx = (idx + step) % n
            if menu[idx].available:
                self.selected_index = idx
                return
        
    def _load_intro_frames(self) -> List[pygame.Surface]:
        """Load and pre-scale the intro banner frames once.

        Frames are scaled to fit the menu width while capping height so the
        menu items still fit beneath the banner. Returns [] if no art is found,
        in which case the menu falls back to the text title.
        """
        frames: List[pygame.Surface] = []
        paths = sorted(glob.glob(INTRO_GLOB))
        if not paths:
            return frames
        target_w = SCREEN_WIDTH - 40
        for p in paths:
            try:
                img = pygame.image.load(p).convert_alpha()
                w, h = img.get_size()
                scale = min(target_w / w, INTRO_MAX_HEIGHT / h)
                frames.append(pygame.transform.smoothscale(
                    img, (max(1, int(w * scale)), max(1, int(h * scale)))))
            except pygame.error as e:
                log_once(log, ("intro_frame", p), logging.WARNING, "Could not load intro frame %s: %s", os.path.basename(p), e)
        return frames

    def _current_intro_frame(self) -> Optional[pygame.Surface]:
        """The banner frame to show this tick, or None if no intro art."""
        if not self.intro_frames:
            return None
        idx = (self.intro_timer // INTRO_TICKS_PER_FRAME) % len(self.intro_frames)
        return self.intro_frames[idx]

    def handle_event(self, event):
        """Handle menu input events."""
        if event.type == pygame.KEYDOWN:
            current_menu = self.menus[self.current_state]

            if event.key == pygame.K_UP:
                self._move_selection(-1)

            elif event.key == pygame.K_DOWN:
                self._move_selection(1)

            elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                selected_item = current_menu[self.selected_index]
                result = selected_item.execute()  # no-op if unavailable

                if isinstance(result, MenuState):
                    self.current_state = result
                    self.selected_index = self._first_available(result)

            elif event.key == pygame.K_ESCAPE:
                if self.current_state != MenuState.MAIN:
                    self.current_state = MenuState.MAIN
                    self.selected_index = self._first_available(MenuState.MAIN)
                else:
                    self.quit_game = True
                    
    def render(self):
        """Render the current menu screen."""
        self.screen.fill((20, 20, 30))  # Dark background
        self.intro_timer += 1  # advance the banner animation

        if self.current_state == MenuState.MAIN:
            self._render_main_menu()
        elif self.current_state == MenuState.CONTROLS:
            self._render_controls_screen()
        elif self.current_state == MenuState.MOVES:
            self._render_moves_screen()
        elif self.current_state == MenuState.MODE_SELECT:
            self._render_mode_select_screen()
            
    def _item_label_color(self, item, index):
        """Label (with '(soon)' suffix if locked) and color for a menu item."""
        if not item.available:
            return f"{item.text}  (soon)", (110, 110, 120)  # greyed out
        color = COLOR_RED if index == self.selected_index else COLOR_WHITE
        return item.text, color

    def _render_main_menu(self):
        """Render the main menu."""
        # Animated intro banner as the title (falls back to text if no art)
        banner = self._current_intro_frame()
        if banner is not None:
            banner_rect = banner.get_rect()
            banner_rect.centerx = SCREEN_WIDTH // 2
            banner_rect.top = 12
            self.screen.blit(banner, banner_rect)
            content_top = banner_rect.bottom + 8
        else:
            title = self.font_large.render("STREET FIGHTER III: 3RD STRIKE", True, COLOR_YELLOW)
            self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 100)))
            subtitle = self.font_medium.render("Python Edition", True, COLOR_WHITE)
            self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, 140)))
            content_top = 170

        # Current mode indicator
        mode_text = f"Current Mode: {self.game_mode_manager.current_mode.name}"
        mode_surface = self.font_small.render(mode_text, True, COLOR_BLUE)
        mode_rect = mode_surface.get_rect(center=(SCREEN_WIDTH // 2, content_top))
        self.screen.blit(mode_surface, mode_rect)

        # Menu items, reflowed to fit beneath the banner
        menu_items = self.menus[MenuState.MAIN]
        start_y = content_top + 22
        spacing = 32

        for i, item in enumerate(menu_items):
            label, color = self._item_label_color(item, i)
            text_surface = self.font_medium.render(label, True, color)
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, start_y + i * spacing))
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
            3: "ROM-accurate hitbox visualization viewer",
            4: "Local 2-player versus matches",
            5: "AI demonstration mode",
            6: ""  # Back button
        }
        
        # Menu items
        menu_items = self.menus[MenuState.MODE_SELECT]
        start_y = 150
        
        for i, item in enumerate(menu_items):
            label, color = self._item_label_color(item, i)
            text_surface = self.font_medium.render(label, True, color)
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
        
    def _start_hitbox_viewer_mode(self):
        """Start the standalone hitbox viewer."""
        self.game_mode_manager.set_mode(GameMode.HITBOX_VIEWER)
        self.selected_mode = GameMode.HITBOX_VIEWER
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

    def _select_hitbox_viewer_mode(self):
        """Select the hitbox viewer mode."""
        self.game_mode_manager.set_mode(GameMode.HITBOX_VIEWER)
        
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
