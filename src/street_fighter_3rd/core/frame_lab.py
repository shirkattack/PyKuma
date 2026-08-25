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
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    GAP = auto()       # between active windows of a multi-hit move (s.HK)
    RECOVERY = auto()
    HITSTUN = auto()
    BLOCKSTUN = auto()
    MOVEMENT = auto()
    NEUTRAL = auto()


# SF6-inspired palette: green windup, red danger, blue vulnerable-cooldown.
PHASE_COLORS = {
    Phase.STARTUP:   (46, 168, 66),
    Phase.ACTIVE:    (222, 48, 48),
    Phase.GAP:       (150, 70, 58),   # ember: "the move is still hot, boxes off"
    Phase.RECOVERY:  (66, 108, 222),
    Phase.HITSTUN:   (232, 202, 44),
    Phase.BLOCKSTUN: (72, 198, 214),
    Phase.MOVEMENT:  (120, 120, 140),
    Phase.NEUTRAL:   (48, 48, 58),
}
COLOR_FREEZE = (245, 245, 245)   # hitstop notch
COLOR_DISCREPANCY = (255, 140, 0)
COLOR_FALLBACK = (230, 60, 200)  # placeholder rectangle was drawn
CEL_SHADES = ((150, 150, 158), (96, 96, 104))  # alternating cel-hold shading

# Every "!!" discrepancy the meter shows is also appended here as plain text,
# so it can be copied/grepped instead of transcribed off the screen. Set the
# env var to another path, or to an empty string to disable the file.
DISCREPANCY_LOG = os.environ.get("PYKUMA_DISCREPANCY_LOG", "bugs/discrepancies.log")


def _log_discrepancy(report, d: Dict[str, Any]) -> None:
    """Mirror one discrepancy to the console log and the copyable text log."""
    note = f"  ({d['note']})" if d.get("note") else ""
    line = (f"P{report.player} {report.move} f{report.start_frame}-{report.end_frame} "
            f"{d['channel']}: observed={d['observed']} expected={d['expected']} "
            f"[{d['provenance']}]{note}")
    log.warning("FrameLab: %s", line)
    if DISCREPANCY_LOG:
        try:
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            with open(DISCREPANCY_LOG, "a", encoding="utf-8") as f:
                f.write(f"{stamp} {line}\n")
        except OSError:
            pass  # never let bookkeeping break gameplay


@dataclass
class Sample:
    """One character-frame on the meter: mechanical phase + sprite track."""
    frame: int
    phase: Phase
    frozen: bool
    expected_phase: Optional[Phase] = None  # from declared timing, when in a move
    move_start: bool = False
    # Sprite track (phase 2): what was visibly drawn this frame. None when the
    # character has no animation controller (e.g. test stubs).
    anim: Optional[str] = None
    cel: Optional[int] = None          # cel index within the animation
    cel_total: Optional[int] = None
    sprite: Optional[str] = None       # sprite number or folder/frame id
    anim_complete: bool = False
    fallback: bool = False             # placeholder rectangle drawn (prev frame)


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
    move_frame: int = 0  # 1-indexed move frame the hit landed on (attacker's
                         # state_frame+1 at contact — which active window hit)


@dataclass
class Expected:
    """Declared move values, with per-field provenance for honest tickets."""
    startup: int
    active: int
    recovery: int
    total: int          # ROM total — NOT s+a+r for multi-hit moves (gap between windows)
    damage: int
    hitstun: int
    blockstun: int
    on_hit: Optional[int]
    on_block: Optional[int]
    gap: int = 0                       # frames between active windows (s.HK: 7)
    hit_windows: int = 1               # number of distinct active windows (hits)
    active_frames: tuple = ()          # 1-indexed declared active frames
    segment: bool = False              # ROM script is only part of the move:
                                       # recovery/gap/total aren't script-measurable


@dataclass
class MoveReport:
    player: int
    move: str
    start_frame: int
    end_frame: int = 0
    startup: int = 0            # measured, non-frozen frames
    active: int = 0
    gap: int = 0                # boxes-off frames BETWEEN active windows (multi-hit)
    recovery: int = 0
    frozen_frames: int = 0
    cancelled: bool = False     # closed by cancelling into another attack
    hits: List[HitEvent] = field(default_factory=list)
    expected: Optional[Expected] = None
    advantage: Optional[int] = None       # measured; None until both actors free
    advantage_kind: str = ""              # "hit" | "block" | "knockdown" | ""
    discrepancies: List[Dict[str, Any]] = field(default_factory=list)
    # Sprite track (phase 2)
    expected_anim: Optional[str] = None
    anims_seen: List[str] = field(default_factory=list)
    fallback_frames: int = 0
    anim_completed_at: Optional[int] = None  # non-frozen move index of completion
    cels_shown: int = 0
    cel_total: Optional[int] = None
    cel_timeline: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.startup + self.active + self.gap + self.recovery

    def summary(self) -> Dict[str, Any]:
        return {
            "move": self.move, "player": self.player,
            "measured": {"startup": self.startup, "active": self.active,
                         "gap": self.gap,
                         "recovery": self.recovery, "total": self.total,
                         "hitstop_frames": self.frozen_frames,
                         "cancelled": self.cancelled,
                         "advantage": self.advantage,
                         "advantage_kind": self.advantage_kind},
            "hits": [vars(h) for h in self.hits],
            "expected": vars(self.expected) if self.expected else None,
            "sprite": {"expected_anim": self.expected_anim,
                       "anims_seen": self.anims_seen,
                       "fallback_frames": self.fallback_frames,
                       "anim_completed_at": self.anim_completed_at,
                       "cels_shown": self.cels_shown,
                       "cel_total": self.cel_total},
        }


def _sprite_info(char) -> Optional[Dict[str, Any]]:
    """What the character is visibly drawing right now, read from the live
    animation controller. Defensive: returns None for controller-less stubs.

    Note: `fallback` reflects the PREVIOUS frame's render (the flag is set in
    _render, which runs after update/observe) — a one-frame lag that doesn't
    matter for counting missing-art frames."""
    ctrl = getattr(char, "animation_controller", None)
    if ctrl is None:
        return None
    try:
        info = ctrl.get_current_frame_info()
    except Exception:
        return None
    if not info or info.get("animation") is None:
        return None
    sprite = info.get("sprite_number")
    if sprite is None:
        sprite = info.get("source")
    return {
        "anim": info.get("animation"),
        "cel": info.get("frame_index"),
        "cel_total": info.get("total_frames"),
        "sprite": str(sprite) if sprite is not None else None,
        "complete": bool(info.get("complete")),
        "fallback": bool(getattr(char, "_rendered_fallback", False)),
    }


def _expected_anim_for(char, state: CharacterState) -> Optional[str]:
    """The animation _STATE_ANIM says this state should play."""
    mapping = getattr(type(char), "_STATE_ANIM", None) or getattr(char, "_STATE_ANIM", None)
    if not mapping:
        return None
    return mapping.get(state)


def _expected_for(state: CharacterState, variant: Optional[str] = None) -> Optional[Expected]:
    """Declared values for a move. Timing = ROM-verified; combat = community."""
    mfd = get_move_frame_data(state, variant)
    if mfd is None:
        return None
    dmg = hs = bs = 0
    if mfd.hitboxes:
        hb = mfd.hitboxes[0][1]
        dmg, hs, bs = hb.damage, hb.hitstun, hb.blockstun
    active = len(mfd.active)
    # ROM total is the ruler; a multi-hit move (s.HK) has a GAP between its
    # active windows, so total > startup + active + recovery.
    total = mfd.total or (mfd.startup + active + mfd.recovery)
    windows = (len(mfd.hit_windows) if mfd.hit_windows
               else 1 + sum(1 for a, b in zip(mfd.active, mfd.active[1:]) if b > a + 1))
    segment = getattr(mfd, "timing_scope", "full") == "segment"
    if segment and getattr(mfd, "community_total", None):
        # The ROM script is only the rise/spin; the move's length is the
        # community total (recovery/gap are not measurable from the script).
        total = int(mfd.community_total)
    return Expected(
        startup=mfd.startup, active=active, recovery=mfd.recovery,
        total=total,
        damage=dmg, hitstun=hs, blockstun=bs,
        on_hit=getattr(mfd, "on_hit", None), on_block=getattr(mfd, "on_block", None),
        gap=max(0, total - (mfd.startup + active + mfd.recovery)),
        hit_windows=windows,
        active_frames=tuple(mfd.active),
        segment=segment,
    )


class MoveCapture:
    """Tracks one execution of one move for one player."""

    def __init__(self, player: int, state: CharacterState, start_frame: int,
                 expected_anim: Optional[str] = None, variant: Optional[str] = None):
        self.player = player
        self.state = state
        self.report = MoveReport(player=player, move=state.name, start_frame=start_frame)
        self.report.expected = _expected_for(state, variant)
        self.report.expected_anim = expected_anim
        self.seen_active = False
        self.nonfrozen_index = 0  # position on the declared timeline
        self._last_cel_key = None
        self._move_samples: List[tuple] = []  # (Sample, had_boxes), non-frozen only
        e = self.report.expected
        self._expected_active_set = frozenset(e.active_frames) if e else frozenset()

    def sample(self, character, frame: int) -> Sample:
        frozen = character.hitfreeze_frames > 0
        boxes = get_akuma_hitboxes(self.state, character.state_frame + 1,
                                   getattr(character, "move_variant", None))
        if boxes:
            phase = Phase.ACTIVE
            self.seen_active = True
        elif not self.seen_active:
            phase = Phase.STARTUP
        else:
            # Provisionally RECOVERY. If another active window opens later
            # (multi-hit move), close() retro-classifies this run as GAP —
            # both in the counts and in the already-emitted meter Samples.
            phase = Phase.RECOVERY

        # Expected phase straight from the DECLARED active windows (1-indexed
        # move frame), so a multi-hit move's underline shows S/A/GAP/A/R.
        exp_phase = None
        e = self.report.expected
        if e is not None and e.active_frames:
            f = self.nonfrozen_index + 1 if not frozen else self.nonfrozen_index
            if f >= 1:
                if f in self._expected_active_set:
                    exp_phase = Phase.ACTIVE
                elif f < e.active_frames[0]:
                    exp_phase = Phase.STARTUP
                elif f > e.active_frames[-1]:
                    exp_phase = Phase.RECOVERY if f <= e.total else None
                else:
                    exp_phase = Phase.GAP

        if frozen:
            self.report.frozen_frames += 1
        else:
            self.nonfrozen_index += 1

        sample = Sample(frame=frame, phase=phase, frozen=frozen,
                        expected_phase=exp_phase,
                        move_start=(not frozen and self.nonfrozen_index == 1))
        if not frozen:
            # Kept for close(): retroactive S/A/GAP/R accounting + recolor.
            self._move_samples.append((sample, bool(boxes)))
        self._record_sprite(sample, _sprite_info(character), frame, phase, frozen)
        return sample

    def _record_sprite(self, sample: Sample, sp: Optional[Dict[str, Any]],
                       frame: int, phase: Phase, frozen: bool):
        if sp is None:
            return
        r = self.report
        sample.anim, sample.cel = sp["anim"], sp["cel"]
        sample.cel_total, sample.sprite = sp["cel_total"], sp["sprite"]
        sample.anim_complete, sample.fallback = sp["complete"], sp["fallback"]
        if sp["anim"] and sp["anim"] not in r.anims_seen:
            r.anims_seen.append(sp["anim"])
        if sp["fallback"]:
            r.fallback_frames += 1
        if sp["complete"] and r.anim_completed_at is None and not frozen:
            # frames the animation actually PLAYED. The playback engine raises
            # is_finished DURING the final cel's last frame (update() advances
            # past the end and clamps back), so the first complete=True sample
            # IS the last played frame — no off-by-one correction.
            r.anim_completed_at = self.nonfrozen_index
        if sp["cel"] is not None:
            r.cels_shown = max(r.cels_shown, sp["cel"] + 1)
        if sp["cel_total"] is not None:
            r.cel_total = sp["cel_total"]
        # cel_timeline: one row per (anim, cel) hold + every fallback frame.
        key = (sp["anim"], sp["cel"])
        if key != self._last_cel_key or sp["fallback"]:
            r.cel_timeline.append({"frame": frame, "phase": phase.name,
                                   "frozen": frozen, "anim": sp["anim"],
                                   "cel": sp["cel"], "sprite": sp["sprite"],
                                   "fallback": sp["fallback"]})
            self._last_cel_key = key

    def close(self, frame: int, cancelled: bool) -> MoveReport:
        r = self.report
        r.end_frame = frame
        r.cancelled = cancelled
        # Retroactive S/A/GAP/R accounting from what the engine actually did:
        # boxes-off frames BETWEEN the first and last observed box frame are
        # GAP (multi-hit move), not recovery. Only now — at close — do we know
        # which no-box run was the last one. Recolors the meter Samples too
        # (same objects live in the ring).
        flags = [b for _, b in self._move_samples]
        first_box = flags.index(True) if True in flags else None
        last_box = (len(flags) - 1 - flags[::-1].index(True)) if True in flags else None
        for i, (sample, had_boxes) in enumerate(self._move_samples):
            if had_boxes:
                r.active += 1
            elif first_box is None or i < first_box:
                r.startup += 1
            elif i < last_box:
                r.gap += 1
                sample.phase = Phase.GAP
            else:
                r.recovery += 1
        self._diff()
        self._diff_sprites()
        return r

    # -- expected vs measured -> discrepancies ------------------------------
    def _flag(self, channel, observed, expected, source, provenance, note=""):
        d = {"channel": channel, "observed": observed, "expected": expected,
             "source": source, "provenance": provenance, "note": note}
        self.report.discrepancies.append(d)
        _log_discrepancy(self.report, d)

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
        # A segment record (specials) can't declare recovery/gap: its ROM
        # script stops at the rise/spin; only the community total is checked.
        if not r.cancelled and e.segment:
            if r.total != e.total:
                self._flag("total", r.total, e.total, community, "community")
        elif not r.cancelled:
            if r.gap != e.gap:
                self._flag("gap", r.gap, e.gap, rom, "verified",
                           "boxes-off frames between the active windows of a "
                           "multi-hit move")
            if r.recovery != e.recovery:
                self._flag("recovery", r.recovery, e.recovery, rom, "verified")
            if r.total != e.total:
                self._flag("total", r.total, e.total, rom, "verified")
        for h in r.hits:
            if h.blocked:
                if e.blockstun and h.blockstun != e.blockstun:
                    self._flag("blockstun", h.blockstun, e.blockstun, community,
                               "community",
                               "declared blockstun is applied directly "
                               "(hitstun//2 is only the no-data fallback)")
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

    def _diff_sprites(self):
        """Sprite-track checks. Conservative by design: only flag what is
        provably wrong from engine truth; alignment JUDGEMENT (does the fist
        LOOK extended during active?) stays with the human, who files it via
        F9 with the cel_timeline as the alignment table."""
        r = self.report
        if not r.anims_seen:
            return  # no sprite track (stub, or no controller)
        map_src = "characters/akuma.py _STATE_ANIM"
        if r.expected_anim:
            wrong = [a for a in r.anims_seen if a != r.expected_anim]
            if wrong:
                self._flag("sprite_mapping", "+".join(wrong), r.expected_anim,
                           map_src, "engine-mapping",
                           "a different animation than the state's mapped one "
                           "was drawn during this move")
        if r.fallback_frames:
            self._flag("sprite_fallback", r.fallback_frames, 0,
                       "renderer (placeholder rectangle)", "engine",
                       "missing local sprite assets or a bad sprite id/path")
        # Timing: the mechanical move is the ruler. Cancels truncate anything.
        if not r.cancelled:
            total = r.total
            if r.anim_completed_at is not None and r.anim_completed_at < total:
                self._flag("sprite_timing", r.anim_completed_at, total,
                           "data/animations.yaml (anim length vs ROM total)",
                           "verified",
                           "animation finished and held its last cel while the "
                           "move was still running")
                if r.anim_completed_at <= r.startup and r.active:
                    self._flag("sprite_sync", r.anim_completed_at, r.startup,
                               "cel_timeline", "verified",
                               "animation ended before the active window began "
                               "— the visible motion cannot match the hit")
            elif (r.anim_completed_at is None and r.cel_total
                  and r.cels_shown < r.cel_total):
                self._flag("sprite_timing", f"{r.cels_shown}/{r.cel_total} cels",
                           f"{r.cel_total}/{r.cel_total} cels",
                           "data/animations.yaml (anim length vs ROM total)",
                           "verified",
                           "the move ended before the animation finished — "
                           "trailing cels are never shown")

    def finalize_advantage(self):
        """Called once advantage is known; diffs it against community values."""
        r, e = self.report, self.report.expected
        if e is None or r.advantage is None or r.cancelled:
            return
        # Community advantage is quoted for a connect of the FINAL active
        # window (whose stun application supersedes any earlier hit's). If
        # only an earlier window of a multi-hit move landed (s.HK's second
        # kick whiffed because knockback pushed the defender out), the quoted
        # number doesn't apply — measuring against it would be a false flag.
        if e.hit_windows > 1 and e.active_frames:
            last_window_start = e.active_frames[-1]
            for a, b in zip(e.active_frames, e.active_frames[1:]):
                if b > a + 1:
                    last_window_start = b  # start of the (eventual) final run
            if not any(h.move_frame >= last_window_start for h in r.hits):
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
            attacker_char = chars.get(pid)
            he = HitEvent(frame=frame,
                          raw_damage=ev.get("raw_damage", 0),
                          scaled_damage=ev.get("scaled_damage", 0),
                          hitstun=ev.get("hitstun", 0),
                          hitstop=ev.get("hitstop", 0),
                          blocked=ev.get("blocked", False),
                          blockstun=ev.get("blockstun", 0),
                          chip_damage=ev.get("chip_damage", 0),
                          # Collision indexed boxes with state_frame+1 this
                          # same frame — that IS the move frame that hit.
                          move_frame=(getattr(attacker_char, "state_frame", -1) + 1
                                      if attacker_char is not None else 0))
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
                cap = MoveCapture(pid, char.state, frame,
                                  expected_anim=_expected_anim_for(char, char.state),
                                  variant=getattr(char, "move_variant", None))
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
        sample = Sample(frame=frame, phase=phase, frozen=frozen)
        sp = _sprite_info(char)
        if sp is not None:
            sample.anim, sample.cel = sp["anim"], sp["cel"]
            sample.cel_total, sample.sprite = sp["cel_total"], sp["sprite"]
            sample.anim_complete, sample.fallback = sp["complete"], sp["fallback"]
        return sample

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
            # Filmstrip row: the sprite track locked to the same frame ruler.
            # Alternating shades per cel hold make the cel RHYTHM visible
            # against the phase colours below; magenta = placeholder drawn;
            # a bright tick marks each cel change.
            shade_i, prev_key = 0, object()
            for i, s in enumerate(self.samples[pid]):
                x = x0 + i * (pip_w + gap)
                key = (s.anim, s.cel)
                changed = (key != prev_key)
                if changed:
                    shade_i ^= 1
                prev_key = key
                if s.anim is not None:
                    color = COLOR_FALLBACK if s.fallback else CEL_SHADES[shade_i]
                    pygame.draw.rect(screen, color, (x, y[pid] - 8, pip_w, 5))
                    if changed:
                        pygame.draw.line(screen, COLOR_FREEZE,
                                         (x, y[pid] - 9), (x, y[pid] - 3), 1)
                pygame.draw.rect(screen, PHASE_COLORS[s.phase],
                                 (x, y[pid], pip_w, pip_h))
                if s.frozen:
                    pygame.draw.rect(screen, COLOR_FREEZE, (x, y[pid], pip_w, 3))
                if s.expected_phase is not None:
                    pygame.draw.rect(screen, PHASE_COLORS[s.expected_phase],
                                     (x, y[pid] + pip_h + 2, pip_w, 3))
                if s.move_start:
                    pygame.draw.line(screen, COLOR_FREEZE,
                                     (x, y[pid] - 10), (x, y[pid] + pip_h + 5), 1)
            self._render_report_line(screen, pid, x0, y[pid] + pip_h + 8
                                     if pid == 2 else y[1] - 14)

    def _render_report_line(self, screen, pid, x, y):
        r = self.last_reports.get(pid)
        if r is None:
            return
        e = r.expected
        show_gap = r.gap or (e is not None and e.gap)
        m_gap = f"/G{r.gap}" if show_gap else ""
        txt = (f"P{pid} {r.move}  meas S{r.startup}/A{r.active}{m_gap}/R{r.recovery} "
               f"T{r.total}" + (" (cancel)" if r.cancelled else ""))
        if e:
            e_gap = f"/G{e.gap}" if show_gap else ""
            txt += f"  exp S{e.startup}/A{e.active}{e_gap}/R{e.recovery} T{e.total}"
        if r.hits:
            h = r.hits[0]
            txt += (f"  blk stun{h.blockstun}" if h.blocked
                    else f"  dmg{h.raw_damage}")
            if e and not h.blocked:
                txt += f"(exp{e.damage})"
            txt += f" stop{h.hitstop}"
        if r.advantage is not None:
            txt += f"  adv{r.advantage:+d}"
        if r.anims_seen:
            txt += f"  [{'+'.join(r.anims_seen)}"
            if r.cel_total:
                txt += f" {r.cels_shown}/{r.cel_total}c"
            if r.fallback_frames:
                txt += f" FB{r.fallback_frames}"
            txt += "]"
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
                {"frame": s.frame, "phase": s.phase.name, "frozen": s.frozen,
                 **({"anim": s.anim, "cel": s.cel, "sprite": s.sprite,
                     "fallback": s.fallback} if s.anim is not None else {})}
                for s in self.samples[report.player]
                if report.start_frame <= s.frame <= (report.end_frame or s.frame)
            ],
        }
        if report.cel_timeline:
            # The alignment table for sprite tickets: one row per cel hold,
            # annotated with the mechanical phase it landed in.
            repro["cel_timeline"] = report.cel_timeline
        if game is not None and getattr(game, "recorder", None):
            span = max(10, (report.end_frame or report.start_frame)
                       - report.start_frame + 10)
            repro["session_clip"] = game.recorder.recent(span)
        return repro
