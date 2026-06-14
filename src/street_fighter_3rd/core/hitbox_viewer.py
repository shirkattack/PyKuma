"""
Standalone hitbox viewer screen.

Reads the ROM-verified `HitboxRepository` directly and draws Akuma's per-move
attack boxes over the composed base hurtbox / pushbox / throwbox. Geometry is
already in PyKuma forward-positive offsets, so the character faces right and no
mirroring is needed.

PyKuma -> screen mapping (feet at a baseline y):
  screen_y = baseline_y + offset_y   (offset_y negative = up from feet)
  attack box  : screen_x = center_x + offset_x          (offset_x = LEFT edge)
  hurt/push/throw : screen_x = center_x + offset_x - width/2  (offset_x = CENTER)

NO INVENTED DATA: boxes that are not `verified` (inferred names, community data,
pending) are drawn DASHED with a label so they are never mistaken for verified.

Controls: LEFT/RIGHT cycle moves, UP/DOWN step frames, ESC/Q exit.
"""

import pygame

from street_fighter_3rd.data.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, STAGE_FLOOR,
    COLOR_BLACK, COLOR_WHITE, COLOR_RED, COLOR_BLUE, COLOR_GREEN, COLOR_YELLOW,
)
from street_fighter_3rd.data.hitbox_repository import HitboxRepository
from street_fighter_3rd.util.logging_config import get_logger

log = get_logger(__name__)

_CYAN = (0, 220, 220)
_BADGE_COLORS = {
    "verified": COLOR_GREEN,
    "inferred": COLOR_YELLOW,
    "community": COLOR_YELLOW,
    "pending": COLOR_YELLOW,
}


def _draw_dashed_rect(surface, color, rect, dash=5, width=2):
    """Dashed rectangle outline (used for non-verified boxes)."""
    x, y, w, h = rect.x, rect.y, rect.width, rect.height
    edges = [((x, y), (x + w, y)), ((x + w, y), (x + w, y + h)),
             ((x + w, y + h), (x, y + h)), ((x, y + h), (x, y))]
    for (x0, y0), (x1, y1) in edges:
        length = max(abs(x1 - x0), abs(y1 - y0))
        if length == 0:
            continue
        steps = int(length // (dash * 2)) + 1
        for i in range(steps):
            t0 = (i * dash * 2) / length
            t1 = min(1.0, (i * dash * 2 + dash) / length)
            pygame.draw.line(
                surface, color,
                (x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0),
                (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1),
                width,
            )


class HitboxViewer:
    """Standalone pygame screen for inspecting ROM-accurate hitboxes."""

    def __init__(self, screen: pygame.Surface, repository: HitboxRepository = None):
        self.screen = screen
        self.repo = repository or HitboxRepository.instance()
        self.moves = list(self.repo.iter_moves())
        self.move_index = 0
        self.frame_index = 0  # index into the current move's active frames

        self.center_x = SCREEN_WIDTH // 2
        self.baseline_y = STAGE_FLOOR + 136  # feet line (matches sprite.bottom)

        self.font = pygame.font.Font(None, 22)
        self.small_font = pygame.font.Font(None, 18)
        self.running = False

    # -- navigation --------------------------------------------------------

    @property
    def current_move(self):
        if not self.moves:
            return None
        return self.moves[self.move_index % len(self.moves)]

    def _active_frames(self):
        move = self.current_move
        return move.active_frames() if move else []

    def next_move(self, step=1):
        if self.moves:
            self.move_index = (self.move_index + step) % len(self.moves)
            self.frame_index = 0

    def step_frame(self, step=1):
        frames = self._active_frames()
        if frames:
            self.frame_index = (self.frame_index + step) % len(frames)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                self.running = False
            elif event.key == pygame.K_RIGHT:
                self.next_move(1)
            elif event.key == pygame.K_LEFT:
                self.next_move(-1)
            elif event.key == pygame.K_UP:
                self.step_frame(1)
            elif event.key == pygame.K_DOWN:
                self.step_frame(-1)

    # -- coordinate mapping ------------------------------------------------

    def _attack_rect(self, box):
        # offset_x = LEFT edge, forward-positive.
        return pygame.Rect(int(self.center_x + box.offset_x),
                           int(self.baseline_y + box.offset_y),
                           int(box.width), int(box.height))

    def _centered_rect(self, box):
        # offset_x = CENTER, forward-positive.
        return pygame.Rect(int(self.center_x + box.offset_x - box.width / 2),
                           int(self.baseline_y + box.offset_y),
                           int(box.width), int(box.height))

    def _draw_box(self, rect, status, solid_color):
        if status == "verified":
            pygame.draw.rect(self.screen, solid_color, rect, 2)
        else:
            _draw_dashed_rect(self.screen, COLOR_YELLOW, rect)

    # -- rendering ---------------------------------------------------------

    def render(self):
        self.screen.fill(COLOR_BLACK)

        # Ground line + placeholder silhouette (107px tall, native scale).
        pygame.draw.line(self.screen, (60, 60, 60),
                         (0, self.baseline_y), (SCREEN_WIDTH, self.baseline_y), 1)
        silhouette = pygame.Rect(self.center_x - 16, self.baseline_y - 107, 32, 107)
        pygame.draw.rect(self.screen, (40, 40, 50), silhouette)

        has_pending = False

        # Pushbox (green) and throwbox (cyan) -- centered boxes.
        push = self.repo.get_pushbox()
        if push:
            self._draw_box(self._centered_rect(push), push.status, COLOR_GREEN)
        throw = self.repo.get_throwbox()
        if throw:
            self._draw_box(self._centered_rect(throw), throw.status, _CYAN)

        # Base hurtboxes (blue) -- centered boxes.
        for hb in self.repo.get_base_hurtboxes():
            rect = self._centered_rect(hb)
            self._draw_box(rect, hb.status, COLOR_BLUE)
            if hb.status != "verified":
                has_pending = True

        # Current move's attack boxes for the selected active frame (red).
        move = self.current_move
        active = self._active_frames()
        frame_no = active[self.frame_index] if active else None
        if move and frame_no is not None:
            for box in move.attack_boxes_for_frame(frame_no):
                rect = self._attack_rect(box)
                # Attack geometry is verified, but if the move name is only
                # inferred, flag the box as non-verified for the viewer.
                status = box.status
                if move.name_status == "inferred":
                    status = "inferred"
                self._draw_box(rect, status, COLOR_RED)
                if status != "verified":
                    has_pending = True

        self._render_hud(move, active, frame_no, has_pending)

    def _render_hud(self, move, active, frame_no, has_pending):
        y = 8
        lines = []
        if move is None:
            lines.append("No moves loaded (hitboxes.yaml missing?)")
        else:
            state = move.state or "(unmapped)"
            lines.append(f"rom_id {move.rom_id}   state: {state}")
            if move.name_status:
                conf = move.confidence or "?"
                lines.append(f"name_status: {move.name_status} (confidence {conf})")
            timing = move.timing
            lines.append("timing  s/a/r/total: "
                         f"{timing.get('startup')}/{timing.get('active')}/"
                         f"{timing.get('recovery')}/{timing.get('total')}")
            if active:
                lines.append(f"active frame {frame_no}  "
                             f"({self.frame_index + 1}/{len(active)})")
            src = move.source
            lines.append(f"source: {src.repo}")
            lines.append(f"        @{src.commit[:12]}")

        for text in lines:
            self.screen.blit(self.font.render(text, True, COLOR_WHITE), (8, y))
            y += 22

        # Provenance badge.
        if move is not None:
            tier = "verified"
            if move.name_status == "inferred":
                tier = "inferred"
            elif move.combat is not None:
                tier = "community"
            badge = self.small_font.render(f"[{tier.upper()}]", True,
                                           _BADGE_COLORS.get(tier, COLOR_WHITE))
            self.screen.blit(badge, (8, y))
            y += 20

        # Legend.
        legend = [
            ("attack (red)", COLOR_RED),
            ("hurt (blue)", COLOR_BLUE),
            ("push (green)", COLOR_GREEN),
            ("throw (cyan)", _CYAN),
        ]
        lx = SCREEN_WIDTH - 160
        ly = 8
        for text, col in legend:
            self.screen.blit(self.small_font.render(text, True, col), (lx, ly))
            ly += 18
        self.screen.blit(self.small_font.render(
            "LEFT/RIGHT move  UP/DOWN frame  ESC quit", True, COLOR_WHITE),
            (8, SCREEN_HEIGHT - 22))

        if has_pending:
            label = self.font.render("PENDING/INFERRED DATA", True, COLOR_YELLOW)
            self.screen.blit(label, (self.center_x - label.get_width() // 2,
                                     SCREEN_HEIGHT - 46))

    # -- loop --------------------------------------------------------------

    def run(self, window=None, clock=None, target_fps=60):
        """Run the viewer until ESC/Q/quit. ``window``/``clock`` optional."""
        self.running = True
        owns_clock = clock is None
        if owns_clock:
            clock = pygame.time.Clock()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.handle_event(event)
            self.render()
            if window is not None:
                pygame.transform.scale(self.screen, window.get_size(), window)
                pygame.display.flip()
            else:
                pygame.display.flip()
            clock.tick(target_fps)
