"""Round system manager for Street Fighter III: 3rd Strike."""

from typing import Tuple, Optional
from ..data.enums import GameState, RoundResult
from ..data.constants import (
    ROUND_TIMER_START,
    TIMER_FRAME_DURATION,
    ROUNDS_TO_WIN,
    PRE_ROUND_FREEZE_FRAMES,
    ROUND_END_HOLD_FRAMES,
    MATCH_END_HOLD_FRAMES
)


class RoundManager:
    """Manages round state, timer, and win conditions."""

    def __init__(self):
        """Initialize the round manager."""
        # Game state
        self.game_state = GameState.TITLE_SCREEN

        # Round tracking
        self.current_round = 1
        self.p1_rounds_won = 0
        self.p2_rounds_won = 0

        # Timer
        self.timer_seconds = ROUND_TIMER_START
        self.timer_frames = 0  # Frame counter for timer countdown

        # Round result
        self.round_result = RoundResult.NONE
        self.match_winner = None  # 1 or 2, or None

        # State frame counters
        self.state_frame = 0  # Frames in current state

        # Store starting health for Perfect detection
        self.p1_starting_health = 0
        self.p2_starting_health = 0

    def start_new_match(self):
        """Reset everything for a new match."""
        self.current_round = 1
        self.p1_rounds_won = 0
        self.p2_rounds_won = 0
        self.match_winner = None
        self.start_pre_round()

    def start_pre_round(self):
        """Begin pre-round state (characters frozen, round announcement)."""
        self.game_state = GameState.PRE_ROUND
        self.state_frame = 0
        self.timer_seconds = ROUND_TIMER_START
        self.timer_frames = 0
        self.round_result = RoundResult.NONE

    def start_fighting(self, p1_health: int, p2_health: int):
        """Transition from pre-round to active fighting."""
        self.game_state = GameState.FIGHTING
        self.state_frame = 0
        self.p1_starting_health = p1_health
        self.p2_starting_health = p2_health

    def end_round(self, result: RoundResult, winner: int):
        """End the current round with a result."""
        self.game_state = GameState.ROUND_END
        self.round_result = result
        self.state_frame = 0

        # Award round win
        if winner == 1:
            self.p1_rounds_won += 1
        elif winner == 2:
            self.p2_rounds_won += 1

        # Check if match is over
        if self.p1_rounds_won >= ROUNDS_TO_WIN:
            self.match_winner = 1
        elif self.p2_rounds_won >= ROUNDS_TO_WIN:
            self.match_winner = 2

    def end_match(self):
        """Transition to match end state."""
        self.game_state = GameState.MATCH_END
        self.state_frame = 0

    def show_continue_screen(self):
        """Show play again / continue screen."""
        self.game_state = GameState.CONTINUE_SCREEN
        self.state_frame = 0

    def update(self, p1_health: int, p2_health: int) -> GameState:
        """Update round state and timer. Returns current game state."""
        self.state_frame += 1

        if self.game_state == GameState.PRE_ROUND:
            # Wait for freeze period to end, then start fighting
            if self.state_frame >= PRE_ROUND_FREEZE_FRAMES:
                self.start_fighting(p1_health, p2_health)

        elif self.game_state == GameState.FIGHTING:
            # Update timer
            self.timer_frames += 1
            if self.timer_frames >= TIMER_FRAME_DURATION:
                self.timer_frames = 0
                self.timer_seconds -= 1

                # Time over condition
                if self.timer_seconds <= 0:
                    self.timer_seconds = 0
                    self._handle_time_over(p1_health, p2_health)

            # Check for K.O. conditions
            if p1_health <= 0 and p2_health <= 0:
                # Double K.O.
                winner = self._determine_winner_by_health(p1_health, p2_health)
                self.end_round(RoundResult.DOUBLE_K_O, winner)
            elif p1_health <= 0:
                # Player 2 wins
                result = RoundResult.PERFECT if p2_health == self.p2_starting_health else RoundResult.K_O
                self.end_round(result, 2)
            elif p2_health <= 0:
                # Player 1 wins
                result = RoundResult.PERFECT if p1_health == self.p1_starting_health else RoundResult.K_O
                self.end_round(result, 1)

        elif self.game_state == GameState.ROUND_END:
            # Hold round result display
            if self.state_frame >= ROUND_END_HOLD_FRAMES:
                if self.match_winner is not None:
                    # Match is over
                    self.end_match()
                else:
                    # Start next round
                    self.current_round += 1
                    self.start_pre_round()

        elif self.game_state == GameState.MATCH_END:
            # Hold match result display
            if self.state_frame >= MATCH_END_HOLD_FRAMES:
                self.show_continue_screen()

        return self.game_state

    def _handle_time_over(self, p1_health: int, p2_health: int):
        """Handle time over condition."""
        winner = self._determine_winner_by_health(p1_health, p2_health)
        self.end_round(RoundResult.TIME_OVER, winner)

    def _determine_winner_by_health(self, p1_health: int, p2_health: int) -> int:
        """Determine winner when time runs out or double K.O. occurs."""
        if p1_health > p2_health:
            return 1
        elif p2_health > p1_health:
            return 2
        else:
            # Equal health - tie goes to player 1 (traditional SF behavior)
            return 1

    def get_timer_display(self) -> str:
        """Get timer as display string (e.g., '99', '42', '03')."""
        return f"{self.timer_seconds:02d}"

    def get_round_display(self) -> str:
        """Get current round as display string."""
        return f"ROUND {self.current_round}"

    def get_round_result_text(self) -> str:
        """Get text to display for round result."""
        if self.round_result == RoundResult.K_O:
            return "K.O."
        elif self.round_result == RoundResult.TIME_OVER:
            return "TIME OVER"
        elif self.round_result == RoundResult.PERFECT:
            return "PERFECT!"
        elif self.round_result == RoundResult.DOUBLE_K_O:
            return "DOUBLE K.O."
        return ""

    def get_match_winner_text(self) -> str:
        """Get text to display for match winner."""
        if self.match_winner == 1:
            return "PLAYER 1 WINS!"
        elif self.match_winner == 2:
            return "PLAYER 2 WINS!"
        return ""

    def should_freeze_gameplay(self) -> bool:
        """Check if characters should be frozen (pre-round, round end, etc)."""
        return self.game_state in [
            GameState.PRE_ROUND,
            GameState.ROUND_END,
            GameState.MATCH_END,
            GameState.CONTINUE_SCREEN
        ]

    def get_round_wins(self) -> Tuple[int, int]:
        """Get (p1_rounds_won, p2_rounds_won)."""
        return (self.p1_rounds_won, self.p2_rounds_won)
