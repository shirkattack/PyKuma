"""Core game class managing game state and main loop."""

import json
import logging
import os
from collections import deque
import pygame
from typing import Dict

from street_fighter_3rd.util.logging_config import get_logger, is_strict, log_once
from street_fighter_3rd.core.diagnostics import InvariantChecker, FrameRecorder, RING_FRAMES

log = get_logger(__name__)
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
    CAMERA_MAX_ZOOM,
    CAMERA_MIN_ZOOM,
    CAMERA_H_MARGIN,
    CAMERA_GROUND_Y,
)
from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.systems.input_system import InputSystem
from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter
from street_fighter_3rd.systems.vfx import VFXManager
from street_fighter_3rd.core.round_manager import RoundManager
from street_fighter_3rd.core.game_modes import GameModeManager, GameMode

# Round-start positions
P1_START_X = 200
P2_START_X = 440

# Input-display glyphs. Directions are facing-relative (FORWARD = toward the
# opponent), keyed by InputDirection numpad value.
_DIR_GLYPHS = {
    8: "↑", 9: "↗", 6: "→", 3: "↘",
    2: "↓", 1: "↙", 4: "←", 7: "↖", 5: "·",
}
# Short labels for held attack buttons, in canonical LP..HK order.
_BUTTON_LABELS = [
    ("LIGHT_PUNCH", "LP"), ("MEDIUM_PUNCH", "MP"), ("HEAVY_PUNCH", "HP"),
    ("LIGHT_KICK", "LK"), ("MEDIUM_KICK", "MK"), ("HEAVY_KICK", "HK"),
]


class Game:
    """Main game class.

    The engine is fixed-timestep: one update() call is one game frame at 60 FPS.
    All gameplay logic is frame-based; there is no delta-time anywhere.
    """

    def __init__(self, screen: pygame.Surface, game_mode_manager: GameModeManager = None):
        """Initialize the game.

        Args:
            screen: Pygame display surface
            game_mode_manager: Optional game mode manager for different play modes
        """
        self.screen = screen
        self.frame_count = 0
        self.paused = False
        self.debug_display = DEBUG_MODE

        # Gameplay diagnostics: per-frame invariant checks + frame recorder
        self.diagnostics = InvariantChecker()
        self.recorder = FrameRecorder()

        # Screen shake (deterministic): countdown + intensity, fed by the VFX
        # manager's shake_request. Fight layer is composed into this buffer then
        # blitted offset; see render() / shake_offset().
        self.shake_frames = 0
        self.shake_intensity = 0
        self.SHAKE_TOTAL = 8
        self._shake_buf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

        # World buffer: the fight (stage + characters + boxes + vfx) is composed
        # here at NATIVE scale, then the dynamic view camera zoom-scales a crop of
        # it onto the screen. _cam = (crop_x, crop_y, zoom) for world->screen maps.
        self._world_buf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._cam = (0.0, 0.0, 1.0)

        # Health-bar animation + training regen state (set up after players exist)
        self.p1_ghost_health = 0
        self.p2_ghost_health = 0
        self._prev_p1_health = 0
        self._prev_p2_health = 0
        self.last_damage_frame = 0
        # Frames of no damage before training-mode regen kicks in (10s @ 60fps)
        self.REGEN_IDLE_FRAMES = 600

        # Initialize game mode manager
        self.game_mode_manager = game_mode_manager or GameModeManager()
        self.config = self.game_mode_manager.get_config()

        # Initialize systems
        self.input_system = InputSystem()
        self.collision_system = SF3CollisionAdapter()
        self.vfx_manager = VFXManager()
        self.round_manager = RoundManager()

        # Load stage background. Resolve against the repo root so it loads no
        # matter the working directory the game is launched from.
        from pathlib import Path
        stage_path = Path(__file__).resolve().parents[3] / "assets" / "stages" / "ryu-stage.gif"
        try:
            self.stage_background = pygame.image.load(str(stage_path)).convert()
        except (pygame.error, OSError, FileNotFoundError) as e:
            log_once(log, ("stage_load",), logging.WARNING, "Could not load stage background: %s", e)
            self.stage_background = None

        # Create characters
        self.player1 = Akuma(P1_START_X, STAGE_FLOOR, player_number=1)
        self.player1.input = self.input_system.player1

        self.player2 = Akuma(P2_START_X, STAGE_FLOOR, player_number=2)
        self.player2.input = self.input_system.player2

        # Start new match
        self.round_manager.start_new_match()
        self._last_game_state = self.round_manager.game_state

        # Health-bar ghost layers start full
        self.p1_ghost_health = self.player1.health
        self.p2_ghost_health = self.player2.health
        self._prev_p1_health = self.player1.health
        self._prev_p2_health = self.player2.health

        # Debug info
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

        # Input-display icons (direction arrows + button icons), vendored from
        # 3rd_training_lua (see assets/ui/inputs/PROVENANCE.md). Loaded + scaled
        # once; falls back to text glyphs if any are missing.
        self._input_icons = self._load_input_icons()

        # Text rendering cache: Font.render is expensive, so static labels are
        # rendered once and dynamic text (timer digits, round text) is cached
        # per unique string.
        self._text_cache: Dict[tuple, pygame.Surface] = {}
        self.p1_name_label = self.small_font.render(
            f"P1 - {self.player1.name.upper()}", True, COLOR_WHITE)
        self.p2_name_label = self.small_font.render(
            f"{self.player2.name.upper()} - P2", True, COLOR_WHITE)
        self.controls_label = self.small_font.render(
            "P1: WASD + JKLUIO | P2: Arrows + NumPad", True, (150, 150, 150))

        # --- Training display state (rendered by _render_training_overlays) ---
        # Floating damage numbers: each is {x, y, amount, age, player}.
        self._damage_popups: list = []
        # Rolling log of recent damage events for the F10 issue report.
        self._recent_damage: deque = deque(maxlen=8)
        # Frame-data panel latch: the last move's data, kept on screen for a
        # short linger after the move ends so it's readable. None when expired.
        self._fd_latch: dict = None
        self._FD_LINGER = 120  # frames (~2s at 60fps) to keep showing after a move
        self._fd_big_font = pygame.font.Font(None, 46)  # big frame-advantage number

    def _render_text(self, font: pygame.font.Font, text: str, color) -> pygame.Surface:
        """Render text through a cache so repeated frames don't re-render."""
        key = (id(font), text, color)
        surface = self._text_cache.get(key)
        if surface is None:
            surface = font.render(text, True, color)
            self._text_cache[key] = surface
        return surface

    def handle_event(self, event: pygame.event.Event):
        """Handle pygame events.

        Args:
            event: Pygame event
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._toggle_pause()
            elif event.key == pygame.K_F1:
                self.debug_display = not self.debug_display
            elif event.key == pygame.K_F10:
                self.build_issue_report()
            elif event.key == pygame.K_F11:
                self.save_clip()
            elif event.key == pygame.K_F12:
                self.save_debug_snapshot()
            elif event.key == pygame.K_RETURN:
                # Handle "Play Again" on continue screen
                if self.round_manager.game_state == GameState.CONTINUE_SCREEN:
                    self._reset_for_new_match()

    def _toggle_pause(self):
        """Toggle pause. Pausing freezes the whole update loop, timer included."""
        self.paused = not self.paused

    def shake_offset(self):
        """Deterministic screen-shake offset (px). Pure function of the countdown
        and intensity — no RNG/frame_count — so replays are bit-identical. (0,0)
        when idle."""
        if self.shake_frames <= 0:
            return (0, 0)
        mag = (self.shake_intensity * self.shake_frames) // self.SHAKE_TOTAL  # decays to 0
        sign = 1 if (self.shake_frames % 2 == 0) else -1
        return (sign * mag, -sign * (mag // 2))

    def update(self):
        """Advance the game by exactly one frame (fixed 60 FPS timestep)."""
        if self.paused:
            return

        self.frame_count += 1

        # Apply training mode features
        self._apply_infinite_health()

        # Update round manager (skip if no rounds mode is enabled)
        if not self.config.no_rounds:
            self.round_manager.update(self.player1.health, self.player2.health)

            # A new round just began (ROUND_END -> PRE_ROUND): reset characters
            # and systems so every round starts from a clean slate.
            if (self.round_manager.game_state == GameState.PRE_ROUND
                    and self._last_game_state == GameState.ROUND_END):
                self._reset_round_state()
            self._last_game_state = self.round_manager.game_state

        # Only update gameplay during PRE_ROUND and FIGHTING states (or always if no rounds)
        if self.config.no_rounds:
            # In no-rounds mode, always update as if fighting
            self._update_fight()
        elif self.round_manager.game_state == GameState.PRE_ROUND:
            self._update_pre_round()
        elif self.round_manager.game_state == GameState.FIGHTING:
            self._update_fight()

        # Training idle-regen + animated health-bar ghost layers
        self._update_health_dynamics()

        # Screen shake: pick up a request from this frame's hits, else count down.
        if self.vfx_manager.shake_request > 0:
            self.shake_intensity = self.vfx_manager.shake_request
            self.shake_frames = self.SHAKE_TOTAL
            self.vfx_manager.shake_request = 0
        elif self.shake_frames > 0:
            self.shake_frames -= 1

        # Diagnostics — record this frame + check invariants. Runs after the
        # collision tick so box/combo state is populated.
        #   - Frame RECORDING (cheap deque append) is on whenever replays are
        #     enabled (TRAINING/DEV) or debug, so F11 always yields a real
        #     ~10s session clip.
        #   - Invariant CHECKS (heavier) stay gated to debug/strict builds.
        if self.config.record_replay or self.debug_display or DEBUG_MODE or is_strict():
            self.recorder.record(self)
        if self.debug_display or DEBUG_MODE or is_strict():
            self.diagnostics.check(self)

    def _update_health_dynamics(self):
        """Track damage timing, run training idle-regen, animate ghost bars."""
        p1, p2 = self.player1, self.player2

        # Note when damage was last dealt (either player lost health this frame)
        if p1.health < self._prev_p1_health or p2.health < self._prev_p2_health:
            self.last_damage_frame = self.frame_count
        # Spawn a floating damage number for each player that lost health.
        if p1.health < self._prev_p1_health:
            self._on_damage(p1, self._prev_p1_health - p1.health)
        if p2.health < self._prev_p2_health:
            self._on_damage(p2, self._prev_p2_health - p2.health)

        # Training mode: after a no-damage lull, regenerate both to full
        if self.config.regen_after_idle:
            idle = self.frame_count - self.last_damage_frame
            if idle >= self.REGEN_IDLE_FRAMES:
                regen = 3  # HP per frame (~visible refill, not instant)
                if p1.health < p1.max_health:
                    p1.health = min(p1.max_health, p1.health + regen)
                if p2.health < p2.max_health:
                    p2.health = min(p2.max_health, p2.health + regen)

        self._prev_p1_health = p1.health
        self._prev_p2_health = p2.health

        # Age + retire floating damage numbers.
        self._update_damage_popups()

        # Ghost/chip layer: snaps UP instantly on heal, eases DOWN to meet
        # current health over ~0.3s so damage reads as a draining chip.
        self.p1_ghost_health = self._ease_ghost(self.p1_ghost_health, p1.health)
        self.p2_ghost_health = self._ease_ghost(self.p2_ghost_health, p2.health)

    @staticmethod
    def _ease_ghost(ghost: float, actual: float) -> float:
        """Move a ghost-health value toward actual: instant up, eased down."""
        if actual >= ghost:
            return actual
        # ease out, with a minimum step so it always finishes promptly
        return max(actual, ghost - max(1.0, (ghost - actual) * 0.25))

    # Frames a floating damage number lives before it fades out.
    DAMAGE_POPUP_LIFETIME = 48

    def _on_damage(self, player, amount: float):
        """Record a health-loss event: spawn a floating number + log it (F10)."""
        amount = int(round(amount))
        if amount <= 0:
            return
        # Anchor above the damaged character's head; it rises as it ages.
        self._damage_popups.append({
            "x": float(player.x),
            "y": float(player.y) - 110.0,
            "amount": amount,
            "age": 0,
            "player": player.player_number,
        })
        self._recent_damage.append({
            "frame": self.frame_count,
            "player": player.player_number,
            "amount": amount,
        })

    def _update_damage_popups(self):
        """Rise + age floating damage numbers, retiring expired ones."""
        for p in self._damage_popups:
            p["age"] += 1
            p["y"] -= 0.8  # drift upward
        self._damage_popups = [
            p for p in self._damage_popups
            if p["age"] < self.DAMAGE_POPUP_LIFETIME
        ]

    def _update_pre_round(self):
        """Update pre-round state (characters frozen)."""
        # Update facing so characters look at each other
        self.player1._update_facing(self.player2)
        self.player2._update_facing(self.player1)

        # Don't process input or update characters during pre-round freeze

    def _update_fight(self):
        """Update fighting state."""
        # Update facing FIRST (before input processing) using current positions
        self.player1._update_facing(self.player2)
        self.player2._update_facing(self.player1)

        # Update input system with correct facing
        self.input_system.update(
            player1_facing_right=self.player1.is_facing_right(),
            player2_facing_right=self.player2.is_facing_right()
        )

        # Update parry windows from this frame's directional inputs
        self.collision_system.update_parry_inputs(
            self.player1, self._get_parry_inputs_for_player(1))
        self.collision_system.update_parry_inputs(
            self.player2, self._get_parry_inputs_for_player(2))

        # Update characters (this will call _update_facing again in parent, but that's ok)
        self.player1.update(self.player2)
        self.player2.update(self.player1)

        # Advance the SF3 core exactly once per game frame, then resolve combat.
        # ONE call: the core checks BOTH attack directions internally and tags each
        # hit with its attacker/defender, so calling it twice would re-detect (and
        # mis-attribute) the same hit back onto the attacker.
        self.collision_system.tick(self.player1, self.player2)
        self.collision_system.check_attack_collision(self.player1, self.player2, self.vfx_manager)

        # Latch the most recent move's frame data so the panel can linger ~2s
        # after the move (set here, after combat, so combo stats reflect the hit).
        self._update_frame_data_latch()

        # Update VFX
        self.vfx_manager.update()

    def _reset_round_state(self):
        """Reset every stateful system to a clean round-start slate.

        This is the reset contract: characters (position, health, transient
        combat state, projectiles), input buffers, VFX, and the collision
        adapter (frame counter, combos, parry state) all start fresh.
        """
        self.player1.reset(P1_START_X, STAGE_FLOOR)
        self.player2.reset(P2_START_X, STAGE_FLOOR)
        self.input_system.reset()
        self.vfx_manager.clear()
        self.collision_system.reset()
        # Reset health-bar animation + idle-regen tracking
        self.p1_ghost_health = self.player1.health
        self.p2_ghost_health = self.player2.health
        self._prev_p1_health = self.player1.health
        self._prev_p2_health = self.player2.health
        self.last_damage_frame = self.frame_count
        self.shake_frames = 0  # no round starts mid-shake

    def _reset_for_new_match(self):
        """Reset characters and start a new match."""
        self._reset_round_state()
        self.round_manager.start_new_match()
        self._last_game_state = self.round_manager.game_state

    def render(self):
        """Render the current frame."""
        state = self.round_manager.game_state
        fight_state = state in (GameState.PRE_ROUND, GameState.FIGHTING,
                                GameState.ROUND_END, GameState.MATCH_END)
        shaking = self.shake_frames > 0 and fight_state

        if fight_state:
            # Compose the fight (stage + characters + boxes + VFX) into the world
            # buffer at native scale, then the dynamic camera zoom-scales a crop of
            # it onto the screen (screen-shake offsets that final blit). UI +
            # overlays draw on the real screen afterward so they stay crisp and
            # never zoom/jitter.
            self._world_buf.fill(COLOR_BLACK)
            real_screen = self.screen
            self.screen = self._world_buf
            self._render_fight()
            self.screen = real_screen
            self.screen.fill(COLOR_BLACK)
            offset = self.shake_offset() if shaking else (0, 0)
            self._blit_world_zoomed(offset)
            self._render_ui()
            self._render_training_overlays()
        else:
            self.screen.fill(COLOR_BLACK)
            if state == GameState.CONTINUE_SCREEN:
                self._render_continue_screen()

        # Render debug info (on the real, un-shaken screen)
        if self.debug_display:
            self._render_debug()

        # Pause overlay on top of everything
        if self.paused:
            paused_text = self._render_text(self.font, "PAUSED", COLOR_WHITE)
            self.screen.blit(paused_text, (SCREEN_WIDTH // 2 - paused_text.get_width() // 2,
                                           SCREEN_HEIGHT // 2 - 30))
            hint_text = self._render_text(self.small_font, "Press ESC to resume", (150, 150, 150))
            self.screen.blit(hint_text, (SCREEN_WIDTH // 2 - hint_text.get_width() // 2,
                                         SCREEN_HEIGHT // 2))

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

        # Render characters — attacker on top so an extended limb isn't hidden
        # behind the opponent's body (default order otherwise).
        p1, p2 = self.player1, self.player2
        if p1.is_attacking() and not p2.is_attacking():
            back, front = p2, p1
        elif p2.is_attacking() and not p1.is_attacking():
            back, front = p1, p2
        else:
            back, front = p1, p2
        back.render(self.screen)
        front.render(self.screen)

        # Render VFX (hit sparks, etc.)
        self.vfx_manager.render(self.screen)

        # Render collision debug (hitboxes/hurtboxes)
        self.collision_system.render_debug(
            self.screen, 
            show_hitboxes=self.config.show_hitboxes,
            show_hurtboxes=self.config.show_hurtboxes
        )
        # NOTE: UI (health bars) is drawn on the real screen by render(), AFTER
        # the camera zoom, so it stays crisp and screen-anchored (not zoomed).

    def _compute_camera(self):
        """Crop rect (x, y, w, h) of the world buffer to zoom onto the screen.

        Width tracks the fighters' separation (+ margin), clamped so zoom stays in
        [MIN, MAX]: close fighters -> small crop -> zoomed in; far apart -> wider
        crop -> zoomed out (SF3-style). Vertically anchored to keep the ground low.
        """
        W, H = SCREEN_WIDTH, SCREEN_HEIGHT
        midx = (self.player1.x + self.player2.x) / 2.0
        sep = abs(self.player1.x - self.player2.x)
        crop_w = sep + 2 * CAMERA_H_MARGIN
        crop_w = max(W / CAMERA_MAX_ZOOM, min(crop_w, W / CAMERA_MIN_ZOOM))
        crop_w = min(crop_w, W)
        crop_h = crop_w * H / W
        crop_x = max(0.0, min(midx - crop_w / 2.0, W - crop_w))
        crop_y = max(0.0, min(CAMERA_GROUND_Y - crop_h * 0.86, H - crop_h))
        return crop_x, crop_y, crop_w, crop_h

    def _blit_world_zoomed(self, offset=(0, 0)):
        """Zoom-scale the camera crop of the world buffer onto the screen."""
        cx, cy, cw, ch = self._compute_camera()
        self._cam = (cx, cy, SCREEN_WIDTH / cw)  # for world->screen mapping
        crop = self._world_buf.subsurface((int(cx), int(cy),
                                           int(round(cw)), int(round(ch))))
        scaled = pygame.transform.scale(crop, (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.screen.blit(scaled, offset)

    def _world_to_screen(self, x, y):
        """Map a world-buffer point to screen coords through the current camera."""
        cx, cy, zoom = self._cam
        return (x - cx) * zoom, (y - cy) * zoom

    @staticmethod
    def _health_color(percent: float):
        """Color for a health bar by remaining fraction: green->yellow->orange->red.

        Same scheme for both players so health is read by color+length, not side.
        """
        percent = max(0.0, min(1.0, percent))
        # (threshold, color) stops from empty (0.0) to full (1.0)
        stops = (
            (0.0, (200, 30, 30)),    # red
            (0.33, (235, 130, 0)),   # orange
            (0.66, (235, 215, 0)),   # yellow
            (1.0, (40, 195, 60)),    # green
        )
        for i in range(len(stops) - 1):
            lo_p, lo_c = stops[i]
            hi_p, hi_c = stops[i + 1]
            if percent <= hi_p:
                span = hi_p - lo_p
                t = (percent - lo_p) / span if span else 0.0
                return tuple(int(lo_c[j] + (hi_c[j] - lo_c[j]) * t) for j in range(3))
        return stops[-1][1]

    def _timer_color(self):
        """Clock color: white normally, escalating in the final seconds."""
        secs = self.round_manager.timer_seconds
        if secs > 10:
            return COLOR_WHITE
        if secs > 5:
            return (240, 200, 0)  # last 10s: yellow warning
        # last 5s: flash red / bright for urgency
        return (235, 30, 30) if (self.frame_count // 15) % 2 == 0 else (255, 220, 120)

    def _render_ui(self):
        """Render game UI (health bars, timer, round indicators, etc.).

        Both health bars deplete toward the center timer: the colored
        (remaining) health stays anchored at the inner/center end of each bar,
        so damage eats inward from the outer edges and the eye is drawn to the
        center. P1 (left bar) is right-anchored; P2 (right bar) is left-anchored.
        """
        health_bar_width = 250
        health_bar_height = 20
        chip_color = (245, 245, 245)  # ghost/chip layer (recently lost health)

        # --- Player 1 (left bar): colored health right-anchored (center end) ---
        p1_pct = max(0, self.player1.health / self.player1.max_health)
        p1_ghost_pct = max(0, self.p1_ghost_health / self.player1.max_health)
        p1_fill = int(health_bar_width * p1_pct)
        p1_ghost = int(health_bar_width * p1_ghost_pct)
        pygame.draw.rect(self.screen, (50, 50, 50), (20, 20, health_bar_width, health_bar_height))
        # ghost/chip behind, then current health on top
        pygame.draw.rect(self.screen, chip_color,
                        (20 + health_bar_width - p1_ghost, 20, p1_ghost, health_bar_height))
        pygame.draw.rect(self.screen, self._health_color(p1_pct),
                        (20 + health_bar_width - p1_fill, 20, p1_fill, health_bar_height))
        pygame.draw.rect(self.screen, COLOR_WHITE, (20, 20, health_bar_width, health_bar_height), 2)
        self.screen.blit(self.p1_name_label, (20, 3))

        # --- Player 2 (right bar): colored health left-anchored (center end) ---
        p2_x = SCREEN_WIDTH - 20 - health_bar_width
        p2_pct = max(0, self.player2.health / self.player2.max_health)
        p2_ghost_pct = max(0, self.p2_ghost_health / self.player2.max_health)
        p2_fill = int(health_bar_width * p2_pct)
        p2_ghost = int(health_bar_width * p2_ghost_pct)
        pygame.draw.rect(self.screen, (50, 50, 50), (p2_x, 20, health_bar_width, health_bar_height))
        pygame.draw.rect(self.screen, chip_color, (p2_x, 20, p2_ghost, health_bar_height))
        pygame.draw.rect(self.screen, self._health_color(p2_pct), (p2_x, 20, p2_fill, health_bar_height))
        pygame.draw.rect(self.screen, COLOR_WHITE, (p2_x, 20, health_bar_width, health_bar_height), 2)
        p2_name = self.p2_name_label
        self.screen.blit(p2_name, (p2_x + health_bar_width - p2_name.get_width(), 3))

        center_x = SCREEN_WIDTH // 2

        # Timer (hidden in no-timer modes like training) — color escalates late
        if not self.config.no_timer:
            timer_text = self._render_text(self.font, self.round_manager.get_timer_display(), self._timer_color())
            self.screen.blit(timer_text, (center_x - timer_text.get_width() // 2, 10))

        # Round indicators (win dots + ROUND/FIGHT/result text) only when rounds
        # are enabled — training/quick-play have no round structure.
        if not self.config.no_rounds:
            p1_wins, p2_wins = self.round_manager.get_round_wins()
            for i in range(p1_wins):
                pygame.draw.circle(self.screen, COLOR_RED, (center_x - 60 - (i * 20), 25), 8)
            for i in range(p2_wins):
                pygame.draw.circle(self.screen, COLOR_BLUE, (center_x + 60 + (i * 20), 25), 8)

            if self.round_manager.game_state == GameState.PRE_ROUND:
                if self.round_manager.state_frame < 60:
                    round_text = self._render_text(self.font, self.round_manager.get_round_display(), COLOR_WHITE)
                    self.screen.blit(round_text, (center_x - round_text.get_width() // 2, SCREEN_HEIGHT // 2 - 30))
                else:
                    fight_text = self._render_text(self.font, "FIGHT!", COLOR_WHITE)
                    self.screen.blit(fight_text, (center_x - fight_text.get_width() // 2, SCREEN_HEIGHT // 2 - 30))
            elif self.round_manager.game_state == GameState.ROUND_END:
                result_text = self._render_text(self.font, self.round_manager.get_round_result_text(), COLOR_WHITE)
                self.screen.blit(result_text, (center_x - result_text.get_width() // 2, SCREEN_HEIGHT // 2 - 30))
            elif self.round_manager.game_state == GameState.MATCH_END:
                winner_text = self._render_text(self.font, self.round_manager.get_match_winner_text(), COLOR_WHITE)
                self.screen.blit(winner_text, (center_x - winner_text.get_width() // 2, SCREEN_HEIGHT // 2 - 30))

    def _render_continue_screen(self):
        """Render the continue/play again screen."""
        # Dark background
        self.screen.fill((20, 20, 20))

        # Match result
        winner_text = self._render_text(self.font, self.round_manager.get_match_winner_text(), COLOR_WHITE)
        self.screen.blit(winner_text, (SCREEN_WIDTH // 2 - winner_text.get_width() // 2, SCREEN_HEIGHT // 2 - 60))

        # Play again prompt
        play_again = self._render_text(self.font, "Play Again?", COLOR_WHITE)
        self.screen.blit(play_again, (SCREEN_WIDTH // 2 - play_again.get_width() // 2, SCREEN_HEIGHT // 2))

        # Instructions
        instructions = self._render_text(self.small_font, "Press ENTER to continue", (150, 150, 150))
        self.screen.blit(instructions, (SCREEN_WIDTH // 2 - instructions.get_width() // 2, SCREEN_HEIGHT // 2 + 40))

    def _debug_lines(self, player) -> list:
        """Build the per-player debug panel text from its numerical state."""
        s = player.get_debug_state()
        anim = s.get("anim", {}) or {}
        spr = anim.get("sprite_number", anim.get("source", "-"))
        return [
            f"P{s['player']} {s.get('name', '')}",
            f"state {s['state']} (f{s['state_frame']})",
            f"anim {anim.get('animation', '-')}",
            f"  frame {anim.get('frame_index', '-')}/{anim.get('total_frames', '-')}  spr={spr}",
            f"pos {s['pos']} vel {s['vel']} {s['facing']}",
            f"hp {s['health']}/{s['max_health']}  feet_y {s.get('feet_y', '-')}",
            f"stun h{s['hitstun']} b{s['blockstun']} frz{s['hitfreeze']}",
            f"grnd {s['grounded']} act {s['can_act']} inv {s['invincible']}",
        ]

    def _blit_debug_panel(self, lines, x, y, color):
        """Draw a translucent debug panel of text lines at (x, y)."""
        line_h = 18
        w, h = 240, len(lines) * line_h + 8
        bg = pygame.Surface((w, h))
        bg.set_alpha(175)
        bg.fill((0, 0, 0))
        self.screen.blit(bg, (x - 4, y - 4))
        for i, line in enumerate(lines):
            self.screen.blit(self.small_font.render(line, True, color), (x, y + i * line_h))

    def _render_debug(self):
        """Render the live debug overlay (toggle with F1)."""
        # Per-player state panels
        self._blit_debug_panel(self._debug_lines(self.player1), 10, 44, COLOR_RED)
        self._blit_debug_panel(self._debug_lines(self.player2), SCREEN_WIDTH - 240, 44, COLOR_BLUE)

        # Frame counter + combo state
        info = [f"frame {self.frame_count}  state {self.round_manager.game_state.name}"]
        if hasattr(self.collision_system, 'get_combo_info'):
            for pid, col in ((1, "P1"), (2, "P2")):
                c = self.collision_system.get_combo_info(pid)
                if c['active'] and c['count'] > 1:
                    info.append(f"{col} combo {c['count']} hits / {c['damage']} dmg")
        for i, line in enumerate(info):
            self.screen.blit(self.small_font.render(line, True, COLOR_WHITE),
                             (10, SCREEN_HEIGHT - 56 + i * 18))

        # Invariant status line (green OK / red last violation)
        ok, last = self.diagnostics.last_status()
        if ok:
            inv_text, inv_color = "INV OK", (90, 220, 90)
        else:
            inv_text = f"INV {last.type} p{last.player} @f{last.frame}"
            inv_color = (235, 80, 80)
        self.screen.blit(self.small_font.render(inv_text, True, inv_color),
                         (SCREEN_WIDTH - 240, SCREEN_HEIGHT - 56))

        # Hotkey hint
        hint = self._render_text(self.small_font, "F1 debug  F10 report  F11 clip  F12 snapshot", (150, 150, 150))
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 18))

    # -- training/dev display layer ---------------------------------------

    def _render_training_overlays(self):
        """Draw the mode-gated training diagnostics: input history, floating
        damage numbers, combo counter, and the per-move frame-data strip.

        Each sub-display is isolated: a failure in one is logged once and skipped
        so it can't blank the others (or, via the main loop's frame guard, drop
        every overlay for the frame).
        """
        cfg = self.config
        sections = []
        if cfg.show_input_display:
            sections.append(("input", lambda: (
                self._render_input_display(self.input_system.player1, side="left"),
                self._render_input_display(self.input_system.player2, side="right"))))
        if cfg.show_damage_numbers:
            sections.append(("damage", self._render_damage_popups))
        if cfg.show_combo_counter:
            sections.append(("combo", self._render_combo_counters))
        if cfg.show_frame_data:
            sections.append(("frame_data", self._render_frame_data))
        for name, fn in sections:
            try:
                fn()
            except Exception:
                log_once(log, ("overlay_fail", name), logging.WARNING,
                         "Training overlay %r failed to render; skipping it.", name)

    @staticmethod
    def _buttons_label(buttons) -> str:
        """'LP+HK'-style label for a set of held Button enum members."""
        names = {getattr(b, "name", str(b)) for b in buttons}
        return "+".join(lbl for key, lbl in _BUTTON_LABELS if key in names)

    @staticmethod
    def _input_entry_str(entry) -> str:
        """One-line text form of an InputHistoryEntry (for the F10 report)."""
        glyph = _DIR_GLYPHS.get(entry.direction.value, "?")
        btns = Game._buttons_label(entry.buttons)
        s = glyph + (" " + btns if btns else "")
        if entry.repeat > 1:
            s += f" x{entry.repeat}"
        return s

    # Input-display column geometry (Fightcade-style ordered, scrolling list).
    _INPUT_ROWS = 12
    _INPUT_ROW_H = 15
    _INPUT_COL_W = 88
    _INPUT_BASELINE_Y = 380  # bottom of the column; newest row sits just above it

    _INPUT_ICON_H = 13  # rendered height of the vendored input icons

    @classmethod
    def _load_input_icons(cls):
        """Load + scale the direction/button icons. Returns
        {'dir': {numpad:int -> Surface}, 'btn': {'LP'.. -> Surface}}; empty dicts
        if the assets are missing (the renderer then falls back to text)."""
        import os
        base = os.path.join("assets", "ui", "inputs")
        icons = {"dir": {}, "btn": {}}

        def load(fn):
            path = os.path.join(base, fn)
            if not os.path.exists(path):
                return None
            img = pygame.image.load(path).convert_alpha()
            scale = cls._INPUT_ICON_H / img.get_height()
            return pygame.transform.scale(
                img, (round(img.get_width() * scale), cls._INPUT_ICON_H))

        for n in range(1, 10):
            s = load(f"{n}_dir.png")
            if s is not None:
                icons["dir"][n] = s
        for code in ("LP", "MP", "HP", "LK", "MK", "HK"):
            s = load(f"{code}_button.png")
            if s is not None:
                icons["btn"][code] = s
        return icons

    @staticmethod
    def _button_codes(buttons):
        """Held buttons as LP..HK codes in canonical order."""
        names = {getattr(b, "name", str(b)) for b in buttons}
        return [lbl for key, lbl in _BUTTON_LABELS if key in names]

    def _render_input_display(self, player_input, side: str):
        """Fixed, persistent input column like Fightcade/FBNeo: newest input is
        always anchored at the bottom and older inputs scroll upward, so the list
        stays in chronological order in stable on-screen positions (it doesn't
        jump around). Each row: direction arrow icon + held button icons +
        held-frame count (falls back to text glyphs if icons are missing).
        """
        history = player_input.get_input_history(self._INPUT_ROWS)
        x = 12 if side == "left" else SCREEN_WIDTH - self._INPUT_COL_W - 8
        row_h = self._INPUT_ROW_H
        col_h = self._INPUT_ROWS * row_h + 6
        baseline = self._INPUT_BASELINE_Y
        # Fixed-size backdrop so the column never resizes as history fills.
        bg = pygame.Surface((self._INPUT_COL_W, col_h))
        bg.set_alpha(130)
        bg.fill((0, 0, 0))
        self.screen.blit(bg, (x - 4, baseline - col_h))
        dir_icons = self._input_icons["dir"]
        btn_icons = self._input_icons["btn"]
        # Newest at the bottom: walk history newest-first, place rows upward.
        for k, e in enumerate(reversed(history)):
            ry = baseline - row_h - k * row_h
            di = dir_icons.get(e.direction.value)
            if di is not None:
                self.screen.blit(di, (x, ry + (row_h - di.get_height()) // 2))
                bx = x + di.get_width() + 3
            else:
                glyph = _DIR_GLYPHS.get(e.direction.value, "·")
                self.screen.blit(self.small_font.render(glyph, True, (235, 235, 235)), (x, ry))
                bx = x + 18

            codes = self._button_codes(e.buttons)
            if btn_icons and codes:
                for code in codes:
                    bi = btn_icons.get(code)
                    if bi is not None:
                        self.screen.blit(bi, (bx, ry + (row_h - bi.get_height()) // 2))
                        bx += bi.get_width() + 1
            elif codes:
                self.screen.blit(self.small_font.render(self._buttons_label(e.buttons),
                                                        True, (245, 235, 90)), (bx, ry))
            if e.repeat > 1:
                cnt = self.small_font.render(str(e.repeat), True, (120, 120, 120))
                self.screen.blit(cnt, (x + self._INPUT_COL_W - 8 - cnt.get_width(), ry))

    def _render_damage_popups(self):
        """Floating damage numbers that rise and fade above the hit character.

        Popups are anchored in world space (at the character), so map them through
        the view camera to screen so they track the character as the view zooms.
        """
        for p in self._damage_popups:
            t = p["age"] / self.DAMAGE_POPUP_LIFETIME
            surf = self.font.render(str(p["amount"]), True,
                                    (255, int(220 * (1 - t)), int(90 * (1 - t))))
            surf.set_alpha(max(0, int(255 * (1.0 - t))))
            sx, sy = self._world_to_screen(p["x"], p["y"])
            self.screen.blit(surf, (int(sx - surf.get_width() / 2), int(sy)))

    def _render_combo_counters(self):
        """Per-player combo readout (hits + cumulative damage) when active."""
        if not hasattr(self.collision_system, "get_combo_info"):
            return
        center_x = SCREEN_WIDTH // 2
        for pid, anchor in ((1, center_x - 150), (2, center_x + 150)):
            c = self.collision_system.get_combo_info(pid)
            if c.get("active") and c.get("count", 0) > 1:
                txt = f"{c['count']} HITS  {c.get('damage', 0)} DMG"
                surf = self.small_font.render(txt, True, (255, 220, 80))
                self.screen.blit(surf, (anchor - surf.get_width() // 2, 70))

    def _update_frame_data_latch(self):
        """Capture the most-recent attacker's move frame data so the panel can
        linger after the move ends. While someone is attacking, (re)latch their
        move + the defender id (for combo stats); otherwise count the latch down
        and clear it when it expires."""
        from street_fighter_3rd.data.akuma_hitboxes import get_move_frame_data
        for atk in (self.player1, self.player2):
            if atk.is_attacking():
                fd = get_move_frame_data(atk.state)
                if fd:
                    self._fd_latch = {
                        "fd": fd, "attacker": atk, "state": atk.state,
                        "defender_id": 2 if atk is self.player1 else 1,
                        "ttl": self._FD_LINGER,
                    }
                    return
        if self._fd_latch:
            self._fd_latch["ttl"] -= 1
            if self._fd_latch["ttl"] <= 0:
                self._fd_latch = None

    def _render_frame_data(self):
        """Bottom-center frame-data panel (lingers ~2s after the move): move name,
        startup/active/recovery + advantage, a phase-colored timeline strip, and a
        3rd_training_lua-style big frame-advantage number with Damage/Combo/Total."""
        latch = self._fd_latch
        if not latch:
            return
        fd = latch["fd"]
        startup, active_n, recovery = fd.startup, len(fd.active), fd.recovery
        total = min(max(1, startup + active_n + recovery), 60)
        cell_w, cell_h, gap = 6, 12, 1
        strip_w = total * (cell_w + gap)
        panel_w = max(strip_w, 260)
        panel_h = 96
        px = (SCREEN_WIDTH - panel_w) // 2
        py = SCREEN_HEIGHT - panel_h - 8

        bg = pygame.Surface((panel_w + 12, panel_h))
        bg.set_alpha(165)
        bg.fill((0, 0, 0))
        self.screen.blit(bg, (px - 6, py - 4))

        def centered(surf, y):
            self.screen.blit(surf, (px + (panel_w - surf.get_width()) // 2, y))

        centered(self.small_font.render(fd.name, True, COLOR_WHITE), py)
        info = (f"S{startup}  A{active_n}  R{recovery}    "
                f"on hit {fd.on_hit:+d}    on block {fd.on_block:+d}")
        centered(self.small_font.render(info, True, (200, 200, 200)), py + 16)

        # Timeline strip (centered); the live frame is marked only while the move
        # is still playing (during the linger there's no marker).
        ty = py + 34
        strip_x = px + (panel_w - strip_w) // 2
        atk = latch["attacker"]
        live = atk.is_attacking() and atk.state == latch["state"]
        cur = max(0, min(atk.state_frame, total - 1)) if live else -1
        for i in range(total):
            if i < startup:
                col = (110, 110, 110)
            elif i < startup + active_n:
                col = (210, 60, 60)
            else:
                col = (70, 120, 210)
            cx = strip_x + i * (cell_w + gap)
            pygame.draw.rect(self.screen, col, (cx, ty, cell_w, cell_h))
            if i == cur:
                pygame.draw.rect(self.screen, COLOR_WHITE, (cx, ty, cell_w, cell_h), 1)

        # Big frame-advantage number (left) + Damage / Combo / Total (right).
        adv_col = (120, 230, 120) if fd.on_hit >= 0 else (235, 110, 110)
        big = self._fd_big_font.render(f"{fd.on_hit:+d}", True, adv_col)
        by = py + 50
        self.screen.blit(big, (px + 6, by))
        combo = {}
        if hasattr(self.collision_system, "get_combo_info"):
            combo = self.collision_system.get_combo_info(latch["defender_id"]) or {}
        stats = [
            ("Damage", combo.get("last_damage", 0)),
            ("Combo", combo.get("count", 0)),
            ("Total", combo.get("damage", 0)),
        ]
        sx = px + 6 + big.get_width() + 16
        for k, (label, val) in enumerate(stats):
            s = self.small_font.render(f"{label}: {val}", True, (235, 235, 120))
            self.screen.blit(s, (sx, by + k * 16))

    def _training_debug(self) -> dict:
        """Training-display state for snapshots / F10 reports: recent inputs,
        recent damage events, and each player's current move frame data."""
        from street_fighter_3rd.data.akuma_hitboxes import get_move_frame_data
        moves = {}
        for p in (self.player1, self.player2):
            if p.is_attacking():
                fd = get_move_frame_data(p.state)
                if fd:
                    moves[f"p{p.player_number}"] = {
                        "name": fd.name, "startup": fd.startup, "active": fd.active,
                        "recovery": fd.recovery, "on_hit": fd.on_hit,
                        "on_block": fd.on_block, "state_frame": p.state_frame,
                    }
        return {
            "inputs": {
                "p1": [self._input_entry_str(e)
                       for e in self.input_system.player1.get_input_history(8)],
                "p2": [self._input_entry_str(e)
                       for e in self.input_system.player2.get_input_history(8)],
            },
            "recent_damage": list(self._recent_damage),
            "current_moves": moves,
        }

    def debug_state(self) -> dict:
        """Full game numerical state for snapshots / crash reports / clips."""
        return {
            "frame": self.frame_count,
            "game_state": self.round_manager.game_state.name,
            "stage_floor": STAGE_FLOOR,
            "screen": [SCREEN_WIDTH, SCREEN_HEIGHT],
            "players": [self.player1.get_debug_state(), self.player2.get_debug_state()],
            "training": self._training_debug(),
        }

    def save_debug_snapshot(self, out_dir="debug_snapshots", name=None):
        """Dump the current frame as PNG + a JSON of full numerical state.

        Hand both files to a collaborator/assistant to pinpoint a bug: the PNG
        shows what's on screen, the JSON shows exactly which sprite each
        character is drawing, positions, frames, health, stun, etc.
        """
        os.makedirs(out_dir, exist_ok=True)
        base = os.path.join(out_dir, name or f"snapshot_{self.frame_count:06d}")
        pygame.image.save(self.screen, base + ".png")
        with open(base + ".json", "w") as f:
            json.dump(self.debug_state(), f, indent=2)
        log.info("Saved debug snapshot: %s.png + %s.json", base, base)
        return base

    def save_clip(self, out_dir=None, frames=RING_FRAMES):
        """Dump the recorded per-frame session timeline (F11) — the last ~10s.

        This is the 'session log over a few seconds' for diagnosing dynamic
        issues (a hitch, a jump that flips, a move that comes out wrong) from
        DATA rather than a single instant: frames.json has, per frame, each
        player's state/anim/pos/vel/facing/jump_direction/grounded AND the raw
        inputs that were held. Reproduce the issue, then press F11. Returns the
        clip directory.
        """
        out_dir = out_dir or os.path.join("debug_snapshots", f"clip_{self.frame_count:06d}")
        os.makedirs(out_dir, exist_ok=True)
        timeline = self.recorder.recent(frames)
        with open(os.path.join(out_dir, "frames.json"), "w") as f:
            json.dump(timeline, f, indent=2)
        self.save_debug_snapshot(out_dir=out_dir, name="current")
        # short human summary of the window
        states = {1: set(), 2: set()}
        for fr in timeline:
            for p in fr["players"]:
                states[p["player"]].add(p["state"])
        lines = [f"# Clip @frame {self.frame_count}", "",
                 f"- frames captured: {len(timeline)} "
                 f"({timeline[0]['frame'] if timeline else '-'}–{self.frame_count})",
                 f"- P1 states: {', '.join(sorted(states[1]))}",
                 f"- P2 states: {', '.join(sorted(states[2]))}",
                 "", "See `frames.json` for the per-frame timeline and `current.png`."]
        with open(os.path.join(out_dir, "summary.md"), "w") as f:
            f.write("\n".join(lines))
        log.info("Saved clip: %s", out_dir)
        return out_dir

    def build_issue_report(self):
        """Bundle a pasteable issue report (F10): snapshot + violations + clip.

        Everything an assistant needs to act on a gameplay issue in one folder.
        """
        out_dir = os.path.join("debug_snapshots", f"report_{self.frame_count:06d}")
        os.makedirs(out_dir, exist_ok=True)
        self.save_debug_snapshot(out_dir=out_dir, name="snapshot")
        self.save_clip(out_dir=out_dir)
        violations = [v.as_dict() for v in self.diagnostics.recent(40)]
        with open(os.path.join(out_dir, "violations.json"), "w") as f:
            json.dump(violations, f, indent=2)

        s1, s2 = self.player1.get_debug_state(), self.player2.get_debug_state()
        md = [f"# Issue report @frame {self.frame_count}", "",
              f"- game state: `{self.round_manager.game_state.name}`", ""]
        md.append("## Players")
        for s in (s1, s2):
            anim = s.get("anim", {})
            md.append(f"- **P{s['player']} {s.get('name','')}** — state `{s['state']}` "
                      f"(f{s['state_frame']}), pos {s['pos']}, hp {s['health']}/{s['max_health']}, "
                      f"anim `{anim.get('animation')}` spr `{anim.get('sprite_number', anim.get('source'))}`"
                      + (", **MISSING ART**" if s.get("rendering_fallback") else ""))
        # Training diagnostics: the inputs/damage/move that led into this frame.
        tr = self._training_debug()
        md += ["", "## Recent inputs (oldest first)"]
        for pid in ("p1", "p2"):
            rows = tr["inputs"][pid]
            md.append(f"- **{pid.upper()}**: {'  '.join(rows) if rows else '(none)'}")
        md += ["", "## Recent damage"]
        if tr["recent_damage"]:
            md += [f"- f{d['frame']} P{d['player']} took {d['amount']}"
                   for d in tr["recent_damage"]]
        else:
            md.append("- none")
        if tr["current_moves"]:
            md += ["", "## Current move frame data"]
            for pid, m in tr["current_moves"].items():
                md.append(f"- **{pid.upper()}** `{m['name']}` "
                          f"S{m['startup']} A{len(m['active'])} R{m['recovery']} "
                          f"(on hit {m['on_hit']:+d}, on block {m['on_block']:+d}, "
                          f"now f{m['state_frame']})")

        md += ["", "## Recent invariant violations"]
        if violations:
            md += [f"- f{v['frame']} `{v['type']}` p{v['player']} {v['values']}" for v in violations[-15:]]
        else:
            md.append("- none flagged")
        md += ["", "## Files", "- `snapshot.png` / `snapshot.json` — this frame",
               "- `frames.json` — recent timeline · `violations.json` — full list"]
        with open(os.path.join(out_dir, "report.md"), "w") as f:
            f.write("\n".join(md))
        log.info("Saved issue report: %s", out_dir)
        return out_dir

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

        self.player1.x = P1_START_X
        self.player1.y = STAGE_FLOOR
        self.player1.velocity_x = 0
        self.player1.velocity_y = 0
        self.player1._transition_to_state(CharacterState.STANDING)

        self.player2.x = P2_START_X
        self.player2.y = STAGE_FLOOR
        self.player2.velocity_x = 0
        self.player2.velocity_y = 0
        self.player2._transition_to_state(CharacterState.STANDING)

        log.info("Positions reset")

    def reset_health(self):
        """Reset both players' health to maximum (training/dev hotkey)."""
        self.player1.health = self.player1.max_health
        self.player2.health = self.player2.max_health
        self.p1_ghost_health = self.player1.health
        self.p2_ghost_health = self.player2.health
        log.info("Health reset")

    def _apply_infinite_health(self):
        """Apply infinite health if enabled."""
        if self.config.infinite_health:
            self.player1.health = self.player1.max_health
            self.player2.health = self.player2.max_health
