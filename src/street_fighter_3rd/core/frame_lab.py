"""Frame Lab — live frame-phase measurement, expected-vs-actual diffing, and
bug-ticket emission.

The problem this solves: a human perceives bugs experientially ("the HP does
too much damage and freezes the opponent too long") while an AI assistant can
only act on dimensioned claims ("HEAVY_PUNCH channel=damage observed=200
expected=180"). Frame Lab is the translation layer, and the FRAME NUMBER is
the shared address space: every pip on the meter, every row in a report, and
every ticket refers to the same (move, frame N).

Three cooperating pieces, all reading LIVE ENGINE TRUTH (never re-deriving
from data files, so engine bugs are visible as engine bugs):

  1. Phase classifier — each character, each frame, is exactly one of
     STARTUP / ACTIVE / RECOVERY / HITSTUN / BLOCKSTUN / MOVEMENT / NEUTRAL,
     with hitstop as an orthogonal `frozen` flag. ACTIVE is defined as "the
     collision adapter would surface attack boxes THIS frame", using the same
     state_frame+1 indexing the adapter uses, so the meter cannot disagree
     with the collision system.

  2. Move capture — opens when a character enters an attack state, samples a
     phase per frame (frozen frames excluded from counts, matching how SF3
     frame data is quoted), records hit events drained from the collision
     adapter, and on close diffs measured values against expected values:
        timing  -> ROM-verified repository (hitboxes.yaml)   [tier: verified]
        combat  -> community values surfaced by the same repo [tier: community]
        hitstop -> the adapter's own design formula           [tier: engine]
     Frame advantage is measured emergently: defender_free - attacker_free.

  3. Outputs — an SF6-style frame meter (one pip per frame, expected-phase
     underline beneath the actual-phase pip, so a timing bug is a visible
     colour misalignment) and F9 bug tickets (schemas/bug_ticket.py) written
     to bugs/ for an AI assistant to consume.

Determinism note: everything here observes; nothing mutates gameplay state.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

import pygame

from street_fighter_3rd.data.enums import CharacterState
from street_fighter_3rd.data.akuma_hitboxes import get_akuma_hitboxes, get_move_frame_data
from street_fighter_3rd.schemas.bug_ticket import (
    BugTicket, ExpectedValue, hints_for, write_ticket,
)
from street_fighter_3rd.util.logging_config import get_logger

log = get_logger(__name__)

RING = 90  # frames of meter history (~1.5s)

_ATTACK_STATES = frozenset({
    CharacterState.LIGHT_PUNCH, CharacterState.MEDIUM_PUNCH, CharacterState.HEAVY_PUNCH,
    CharacterState.LIGHT_KICK, CharacterState.MEDIUM_KICK, CharacterState.HEAVY_KICK,
    CharacterState.CROUCH_LIGHT_PUNCH, CharacterState.CROUCH_MEDIUM_PUNCH,
    CharacterState.CROUCH_HEAVY_PUNCH, CharacterState.CROUCH_LIGHT_KICK,
    CharacterState.CROUCH_MEDIUM_KICK, CharacterState.CROUCH_HEAVY_KICK,
    CharacterState.JUMP_LIGHT_PUNCH, CharacterState.JUMP_MEDIUM_PUNCH,
    CharacterState.JUMP_HEAVY_PUNCH, CharacterState.JUMP_LIGHT_KICK,
    CharacterState.JUMP_MEDIUM_KICK, CharacterState.JUMP_HEAVY_KICK,
    CharacterState.GOHADOKEN, CharacterState.GOSHORYUKEN, CharacterState.TATSUMAKI,
    CharacterState.OVERHEAD,
})

_HITSTUN_STATES = frozenset({
    CharacterState.HITSTUN_STANDING, CharacterState.HITSTUN_CROUCHING,
    CharacterState.HITSTUN_AIRBORNE, CharacterState.KNOCKDOWN,
})

_MOVEMENT_STATES = frozenset({
    CharacterState.JUMP_STARTUP, CharacterState.JUMPING,
    CharacterState.JUMPING_FORWARD, CharacterState.JUMPING_BACKWARD,
    CharacterState.AIRBORNE, CharacterState.LANDING,
    CharacterState.DASH_FORWARD, CharacterState.DASH_BACKWARD,
})


class Phase(Enum):
    STARTUP = auto()
    ACTIVE = auto()
    RECOVERY = auto()
    HITSTUN = auto()
    BLOCKSTUN = auto()
    MOVEMENT = auto()
    NEUTRAL = auto()


# SF6-inspired palette: green windup, red danger, blue vulnerable-cooldown.
PHASE_COLORS = {
    Phase.STARTUP:   (46, 168, 66),
    Phase.ACTIVE:    (222, 48, 48),
    Phase.RECOVERY:  (66, 108, 222),
    Phase.HITSTUN:   (232, 202, 44),
    Phase.BLOCKSTUN: (72, 198, 214),
    Phase.MOVEMENT:  (120, 120, 140),
    Phase.NEUTRAL:   (48, 48, 58),
}
COLOR_FREEZE = (245, 245, 245)   # hitstop notch
COLOR_DISCREPANCY = (255, 140, 0)


@dataclass
class Sample:
    """One character-frame on the meter."""
    frame: int
    phase: Phase
    frozen: bool
    expected_phase: Optional[Phase] = None  # from declared timing, when in a move
    move_start: bool = False


@dataclass
class HitEvent:
    frame: int
    raw_damage: int
    scaled_damage: int
    hitstun: int
    hitstop: int
    blocked: bool
    blockstun: int = 0
    chip_damage: int = 0


@dataclass
class Expected:
    """Declared move values, with per-field provenance for honest tickets."""
    startup: int
    active: int
    recovery: int
    total: int
    damage: int
    hitstun: int
    blockstun: int
    on_hit: Optional[int]
    on_block: Optional[int]


@dataclass
class MoveReport:
    player: int
    move: str
    start_frame: int
    end_frame: int = 0
    startup: int = 0            # measured, non-frozen frames
    active: int = 0
    recovery: int = 0
    frozen_frames: int = 0
    cancelled: bool = False     # closed by cancelling into another attack
    hits: List[HitEvent] = field(default_factory=list)
    expected: Optional[Expected] = None
    advantage: Optional[int] = None       # measured; None until both actors free
    advantage_kind: str = ""              # "hit" | "block" | "knockdown" | ""
    discrepancies: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.startup + self.active + self.recovery

    def summary(self) -> Dict[str, Any]:
        return {
            "move": self.move, "player": self.player,
            "measured": {"startup": self.startup, "active": self.active,
                         "recovery": self.recovery, "total": self.total,
                         "hitstop_frames": self.frozen_frames,
                         "cancelled": self.cancelled,
                         "advantage": self.advantage,
                         "advantage_kind": self.advantage_kind},
            "hits": [vars(h) for h in self.hits],
            "expected": vars(self.expected) if self.expected else None,
        }


def _expected_for(state: CharacterState) -> Optional[Expected]:
    """Declared values for a move. Timing = ROM-verified; combat = community."""
    mfd = get_move_frame_data(state)
    if mfd is None:
        return None
    dmg = hs = bs = 0
    if mfd.hitboxes:
        hb = mfd.hitboxes[0][1]
        dmg, hs, bs = hb.damage, hb.hitstun, hb.blockstun
    active = len(mfd.active)
    return Expected(
        startup=mfd.startup, active=active, recovery=mfd.recovery,
        total=mfd.startup + active + mfd.recovery,
        damage=dmg, hitstun=hs, blockstun=bs,
        on_hit=getattr(mfd, "on_hit", None), on_block=getattr(mfd, "on_block", None),
    )


class MoveCapture:
    """Tracks one execution of one move for one player."""

    def __init__(self, player: int, state: CharacterState, start_frame: int):
        self.player = player
        self.state = state
        self.report = MoveReport(player=player, move=state.name, start_frame=start_frame)
        self.report.expected = _expected_for(state)
        self.seen_active = False
        self.nonfrozen_index = 0  # position on the declared timeline

    def sample(self, character, frame: int) -> Sample:
        frozen = character.hitfreeze_frames > 0
        boxes = get_akuma_hitboxes(self.state, character.state_frame + 1)
        if boxes:
            phase = Phase.ACTIVE
            self.seen_active = True
        elif not self.seen_active:
            phase = Phase.STARTUP
        else:
            phase = Phase.RECOVERY

        exp_phase = None
        if self.report.expected is not None:
            e, i = self.report.expected, self.nonfrozen_index
            if i < e.startup:
                exp_phase = Phase.STARTUP
            elif i < e.startup + e.active:
                exp_phase = Phase.ACTIVE
            elif i < e.total:
                exp_phase = Phase.RECOVERY

        if frozen:
            self.report.frozen_frames += 1
        else:
            self.nonfrozen_index += 1
            if phase is Phase.STARTUP:
                self.report.startup += 1
            elif phase is Phase.ACTIVE:
                self.report.active += 1
            else:
                self.report.recovery += 1

        return Sample(frame=frame, phase=phase, frozen=frozen,
                      expected_phase=exp_phase,
                      move_start=(self.nonfrozen_index == 1 and not frozen
                                  and self.report.startup + self.report.active
                                  + self.report.recovery == 1))

    def close(self, frame: int, cancelled: bool) -> MoveReport:
        r = self.report
        r.end_frame = frame
        r.cancelled = cancelled
        self._diff()
        return r

    # -- expected vs measured -> discrepancies ------------------------------
    def _flag(self, channel, observed, expected, source, provenance, note=""):
        d = {"channel": channel, "observed": observed, "expected": expected,
             "source": source, "provenance": provenance, "note": note}
        self.report.discrepancies.append(d)

    def _diff(self):
        r, e = self.report, self.report.expected
        if e is None:
            return
        rom = "data/characters/akuma/hitboxes.yaml (ROM dump)"
        community = "hitboxes.yaml combat tier (Baston ESN3S)"
        if r.startup != e.startup:
            self._flag("startup", r.startup, e.startup, rom, "verified")
        if r.active != e.active:
            self._flag("active", r.active, e.active, rom, "verified")
        # A cancel legitimately truncates recovery/total — don't false-flag.
        if not r.cancelled:
            if r.recovery != e.recovery:
                self._flag("recovery", r.recovery, e.recovery, rom, "verified")
            if r.total != e.total:
                self._flag("total", r.total, e.total, rom, "verified")
        for h in r.hits:
            if h.blocked:
                if e.blockstun and h.blockstun != e.blockstun:
                    self._flag("blockstun", h.blockstun, e.blockstun, community,
                               "community",
                               "engine derives blockstun=max(4,hitstun//2); "
                               "declared value is not read")
            else:
                if e.damage and h.raw_damage != e.damage:
                    self._flag("damage", h.raw_damage, e.damage, community,
                               "community",
                               f"raw (pre-scaling); scaled applied={h.scaled_damage}")
                if e.hitstun and h.hitstun != e.hitstun:
                    self._flag("hitstun", h.hitstun, e.hitstun, community, "community")
            exp_stop = self._expected_hitstop(h.scaled_damage)
            if exp_stop is not None and h.hitstop != exp_stop:
                self._flag("hitstop", h.hitstop, exp_stop,
                           "sf3_collision_adapter formula", "engine-formula")

    def finalize_advantage(self):
        """Called once advantage is known; diffs it against community values."""
        r, e = self.report, self.report.expected
        if e is None or r.advantage is None or r.cancelled:
            return
        if r.advantage_kind == "hit" and e.on_hit is not None and r.advantage != e.on_hit:
            self._flag("advantage_on_hit", r.advantage, e.on_hit,
                       "hitboxes.yaml combat tier", "community")
        if r.advantage_kind == "block" and e.on_block is not None and r.advantage != e.on_block:
            self._flag("advantage_on_block", r.advantage, e.on_block,
                       "hitboxes.yaml combat tier", "community")

    @staticmethod
    def _expected_hitstop(scaled_damage: int) -> Optional[int]:
        try:
            from street_fighter_3rd.systems.sf3_collision_adapter import (
                HITSTOP_BASE, HITSTOP_PER, HITSTOP_MAX)
            return min(HITSTOP_MAX, HITSTOP_BASE + scaled_damage // HITSTOP_PER)
        except ImportError:
            return None


class _AdvantageWatch:
    """After a connected hit, measure emergent frame advantage:
    (frame the defender can act) - (frame the attacker can act)."""

    def __init__(self, report: MoveReport, capture: MoveCapture, kind: str):
        self.report, self.capture, self.kind = report, capture, kind
        self.attacker_free: Optional[int] = None
        self.defender_free: Optional[int] = None

    def tick(self, frame, attacker, defender) -> bool:
        """Returns True when finished."""
        if self.attacker_free is None:
            if (attacker.hitfreeze_frames == 0
                    and attacker.state not in _ATTACK_STATES):
                self.attacker_free = frame
        if self.defender_free is None:
            if defender.state is CharacterState.KNOCKDOWN:
                self.report.advantage_kind = "knockdown"
                return True  # knockdown advantage is a different animal; skip
            if (defender.hitfreeze_frames == 0 and defender.hitstun_frames == 0
                    and defender.blockstun_frames == 0
                    and defender.state not in _HITSTUN_STATES):
                self.defender_free = frame
        if self.attacker_free is not None and self.defender_free is not None:
            self.report.advantage = self.defender_free - self.attacker_free
            self.report.advantage_kind = self.kind
            self.capture.finalize_advantage()
            return True
        return False


class FrameLab:
    """Orchestrator: observe(game) once per frame; render(); dump_tickets()."""

    def __init__(self, ring: int = RING):
        self.samples = {1: collections.deque(maxlen=ring),
                        2: collections.deque(maxlen=ring)}
        self.captures: Dict[int, Optional[MoveCapture]] = {1: None, 2: None}
        self.last_reports: Dict[int, Optional[MoveReport]] = {1: None, 2: None}
        self._watches: List[_AdvantageWatch] = []
        self._font = None
        self._ticket_seq = 0

    def reset(self):
        for d in self.samples.values():
            d.clear()
        self.captures = {1: None, 2: None}
        self._watches.clear()
        # last_reports intentionally survive reset so F9 works post-round.

    # -- per-frame observation ----------------------------------------------
    def observe(self, game):
        frame = game.frame_count
        chars = {1: game.player1, 2: game.player2}

        # Route this frame's hit events (drained from the collision adapter)
        # to the attacker's open capture, and start advantage watches.
        drain = getattr(game.collision_system, "drain_hit_events", None)
        events = drain() if drain else []
        for ev in events:
            pid = ev.get("attacker", 0)
            cap = self.captures.get(pid)
            he = HitEvent(frame=frame,
                          raw_damage=ev.get("raw_damage", 0),
                          scaled_damage=ev.get("scaled_damage", 0),
                          hitstun=ev.get("hitstun", 0),
                          hitstop=ev.get("hitstop", 0),
                          blocked=ev.get("blocked", False),
                          blockstun=ev.get("blockstun", 0),
                          chip_damage=ev.get("chip_damage", 0))
            if cap is not None:
                cap.report.hits.append(he)
                kind = "block" if he.blocked else "hit"
                other = 2 if pid == 1 else 1
                self._watches.append(_AdvantageWatch(cap.report, cap, kind))
                self._watches[-1]._pair = (pid, other)

        for pid, char in chars.items():
            self.samples[pid].append(self._observe_character(pid, char, frame))

        # Advance advantage watches after both characters were sampled.
        done = []
        for w in self._watches:
            a_id, d_id = getattr(w, "_pair", (1, 2))
            if w.tick(frame, chars[a_id], chars[d_id]):
                done.append(w)
        for w in done:
            self._watches.remove(w)

    def _observe_character(self, pid: int, char, frame: int) -> Sample:
        cap = self.captures[pid]
        in_attack = char.state in _ATTACK_STATES

        if in_attack:
            # New move, or cancel from one attack straight into another.
            if cap is None or cap.state != char.state or char.state_frame < 1:
                if cap is not None:
                    self.last_reports[pid] = cap.close(frame, cancelled=True)
                cap = MoveCapture(pid, char.state, frame)
                self.captures[pid] = cap
            return cap.sample(char, frame)

        if cap is not None:  # move just ended normally
            self.last_reports[pid] = cap.close(frame, cancelled=False)
            self.captures[pid] = None

        frozen = char.hitfreeze_frames > 0
        if char.hitstun_frames > 0 or char.state in _HITSTUN_STATES:
            phase = Phase.HITSTUN
        elif char.blockstun_frames > 0 or char.state in (
                CharacterState.BLOCKSTUN_HIGH, CharacterState.BLOCKSTUN_LOW):
            phase = Phase.BLOCKSTUN
        elif char.state in _MOVEMENT_STATES:
            phase = Phase.MOVEMENT
        else:
            phase = Phase.NEUTRAL
        return Sample(frame=frame, phase=phase, frozen=frozen)

    # -- rendering ------------------------------------------------------------
    def render(self, screen: pygame.Surface):
        if self._font is None:
            self._font = pygame.font.Font(None, 18)
        w = screen.get_width()
        pip_w, pip_h, gap = 6, 14, 1
        n = self.samples[1].maxlen
        strip_w = n * (pip_w + gap)
        x0 = (w - strip_w) // 2
        y = {1: screen.get_height() - 118, 2: screen.get_height() - 96}

        for pid in (1, 2):
            for i, s in enumerate(self.samples[pid]):
                x = x0 + i * (pip_w + gap)
                pygame.draw.rect(screen, PHASE_COLORS[s.phase],
                                 (x, y[pid], pip_w, pip_h))
                if s.frozen:
                    pygame.draw.rect(screen, COLOR_FREEZE, (x, y[pid], pip_w, 3))
                if s.expected_phase is not None:
                    pygame.draw.rect(screen, PHASE_COLORS[s.expected_phase],
                                     (x, y[pid] + pip_h + 2, pip_w, 3))
                if s.move_start:
                    pygame.draw.line(screen, COLOR_FREEZE,
                                     (x, y[pid] - 3), (x, y[pid] + pip_h + 5), 1)
            self._render_report_line(screen, pid, x0, y[pid] + pip_h + 8
                                     if pid == 2 else y[1] - 14)

    def _render_report_line(self, screen, pid, x, y):
        r = self.last_reports.get(pid)
        if r is None:
            return
        e = r.expected
        txt = (f"P{pid} {r.move}  meas S{r.startup}/A{r.active}/R{r.recovery} "
               f"T{r.total}" + (" (cancel)" if r.cancelled else ""))
        if e:
            txt += f"  exp S{e.startup}/A{e.active}/R{e.recovery} T{e.total}"
        if r.hits:
            h = r.hits[0]
            txt += (f"  blk stun{h.blockstun}" if h.blocked
                    else f"  dmg{h.raw_damage}")
            if e and not h.blocked:
                txt += f"(exp{e.damage})"
            txt += f" stop{h.hitstop}"
        if r.advantage is not None:
            txt += f"  adv{r.advantage:+d}"
        color = COLOR_DISCREPANCY if r.discrepancies else (200, 200, 200)
        screen.blit(self._font.render(txt, True, color), (x, y))
        if r.discrepancies:
            d = r.discrepancies[0]
            more = f" (+{len(r.discrepancies)-1} more)" if len(r.discrepancies) > 1 else ""
            dtxt = (f"!! {d['channel']}: observed {d['observed']} != expected "
                    f"{d['expected']} [{d['provenance']}]{more}  — F9 to file")
            screen.blit(self._font.render(dtxt, True, COLOR_DISCREPANCY),
                        (x, y + 12 if pid == 2 else y - 12))

    # -- ticket emission --------------------------------------------------------
    def dump_tickets(self, game=None, out_dir: str = "bugs") -> List[str]:
        """F9: turn the last completed move(s) into validated ticket YAMLs.

        One ticket per detected discrepancy; if a move had none, one
        'observation' ticket so the human can attach a complaint anyway.
        """
        paths: List[str] = []
        for pid in (1, 2):
            r = self.last_reports.get(pid)
            if r is None:
                continue
            repro = self._repro_for(r, game)
            rows = r.discrepancies or [None]
            for d in rows:
                self._ticket_seq += 1
                channel = d["channel"] if d else "observation"
                tid = f"{r.start_frame:06d}_p{pid}_{r.move.lower()}_{channel}_{self._ticket_seq:03d}"
                ticket = BugTicket(
                    id=tid, move=r.move, player=pid, channel=channel,
                    frame_range=(r.start_frame, r.end_frame),
                    observed=d["observed"] if d else None,
                    expected=ExpectedValue(value=d["expected"], source=d["source"],
                                           provenance=d["provenance"]) if d else None,
                    delta=(float(d["observed"] - d["expected"])
                           if d and isinstance(d["observed"], (int, float))
                           and isinstance(d["expected"], (int, float)) else None),
                    measured_summary=r.summary(),
                    repro=repro,
                    fix_hints=hints_for(channel)
                              + ([d["note"]] if d and d.get("note") else []),
                )
                paths.append(write_ticket(ticket, out_dir))
        if paths:
            log.info("Frame Lab: wrote %d ticket(s): %s", len(paths), paths)
        else:
            log.info("Frame Lab: no completed move to ticket yet.")
        return paths

    def _repro_for(self, report: MoveReport, game) -> Dict[str, Any]:
        repro: Dict[str, Any] = {
            "phase_timeline": [
                {"frame": s.frame, "phase": s.phase.name, "frozen": s.frozen}
                for s in self.samples[report.player]
                if report.start_frame <= s.frame <= (report.end_frame or s.frame)
            ],
        }
        if game is not None and getattr(game, "recorder", None):
            span = max(10, (report.end_frame or report.start_frame)
                       - report.start_frame + 10)
            repro["session_clip"] = game.recorder.recent(span)
        return repro
