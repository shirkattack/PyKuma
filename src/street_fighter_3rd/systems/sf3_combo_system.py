"""
SF3:3S Authentic Combo System

This module implements SF3's combo mechanics including:
- Combo counter tracking
- Damage scaling (proration)
- Gravity scaling for juggles
- Hit confirmation tracking

References:
- SF3 damage scaling analysis
- Community combo system documentation
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from street_fighter_3rd.util.logging_config import get_logger

log = get_logger(__name__)


class SF3ComboType(Enum):
    """Types of combos in SF3"""
    GROUND = "ground"      # Ground-based combo
    JUGGLE = "juggle"      # Air juggle combo
    RESET = "reset"        # Combo reset


@dataclass
class SF3ComboHit:
    """Individual hit in a combo"""
    damage: int
    scaled_damage: int
    hit_number: int
    timestamp: float
    hit_type: str = "normal"  # normal, special, super
    

@dataclass
class SF3ComboState:
    """Tracks combo state for a player"""
    # Combo tracking
    combo_count: int = 0
    combo_damage: int = 0
    combo_hits: List[SF3ComboHit] = field(default_factory=list)
    combo_active: bool = False
    combo_type: SF3ComboType = SF3ComboType.GROUND
    
    # Timing tracking
    last_hit_time: float = 0.0
    combo_start_time: float = 0.0
    
    # Scaling factors
    damage_scaling: float = 1.0
    gravity_scaling: float = 1.0
    
    def reset(self):
        """Reset combo state"""
        self.combo_count = 0
        self.combo_damage = 0
        self.combo_hits.clear()
        self.combo_active = False
        self.combo_type = SF3ComboType.GROUND
        self.last_hit_time = 0.0
        self.combo_start_time = 0.0
        self.damage_scaling = 1.0
        self.gravity_scaling = 1.0


class SF3ComboSystem:
    """
    SF3's authentic combo system
    
    This implements damage scaling, combo tracking, and juggle mechanics
    based on authentic SF3 behavior.
    """
    
    # SF3 authentic damage scaling values
    # Each successive hit does less damage
    DAMAGE_SCALING_TABLE = [
        1.00,  # 1st hit - 100%
        0.90,  # 2nd hit - 90%
        0.80,  # 3rd hit - 80%
        0.70,  # 4th hit - 70%
        0.60,  # 5th hit - 60%
        0.50,  # 6th hit - 50%
        0.40,  # 7th hit - 40%
        0.30,  # 8th hit - 30%
        0.20,  # 9th hit - 20%
        0.10,  # 10th+ hit - 10%
    ]

    def __init__(self):
        # Combo state for each player (who is being comboed)
        self.player_combo_states: Dict[int, SF3ComboState] = {
            1: SF3ComboState(),
            2: SF3ComboState()
        }
    
    def register_hit(self, attacker_id: int, defender_id: int, base_damage: int,
                    hit_type: str = "normal", defender_in_hitstun: bool = False) -> int:
        """
        Register a hit and apply damage scaling

        Args:
            attacker_id: ID of attacking player
            defender_id: ID of defending player
            base_damage: Base damage before scaling
            hit_type: Type of hit (normal, special, super)
            defender_in_hitstun: True if the defender was ALREADY in a hit reaction
                when this hit landed. A combo is a chain the defender can't recover
                between, so the counter only continues while this is True; a hit on
                a recovered defender starts a fresh combo. This is the real combo
                rule and is deterministic, unlike the old wall-clock timeout (which
                counted mashed jabs with recovery gaps as one long combo).

        Returns:
            Scaled damage amount
        """
        # Timestamps are informational only (combo logic is driven by
        # defender_in_hitstun / update(), not the clock); keep them deterministic.
        current_time = 0.0
        combo_state = self.player_combo_states[defender_id]

        # Continue only if the defender hasn't recovered since the last hit;
        # otherwise start a fresh combo.
        if combo_state.combo_active and defender_in_hitstun:
            combo_state.combo_count += 1
        else:
            self._start_new_combo(combo_state, current_time)
        
        # Apply damage scaling
        scaled_damage = self._apply_damage_scaling(base_damage, combo_state.combo_count)
        
        # Record the hit
        hit = SF3ComboHit(
            damage=base_damage,
            scaled_damage=scaled_damage,
            hit_number=combo_state.combo_count,
            timestamp=current_time,
            hit_type=hit_type
        )
        combo_state.combo_hits.append(hit)
        combo_state.combo_damage += scaled_damage
        combo_state.last_hit_time = current_time
        combo_state.combo_active = True
        
        # Update scaling for next hit
        self._update_scaling_factors(combo_state)
        
        log.debug("Combo Hit #%s: %s -> %s damage", combo_state.combo_count, base_damage, scaled_damage)

        return scaled_damage

    def _start_new_combo(self, combo_state: SF3ComboState, current_time: float):
        """Start a new combo"""
        combo_state.reset()
        combo_state.combo_count = 1
        combo_state.combo_start_time = current_time
        combo_state.combo_active = True
    
    def _apply_damage_scaling(self, base_damage: int, hit_number: int) -> int:
        """Apply SF3's damage scaling based on hit number in combo"""
        if hit_number <= 0:
            return base_damage
        
        # Get scaling factor (hit_number is 1-indexed)
        scaling_index = min(hit_number - 1, len(self.DAMAGE_SCALING_TABLE) - 1)
        scaling_factor = self.DAMAGE_SCALING_TABLE[scaling_index]
        
        # Apply scaling
        scaled_damage = int(base_damage * scaling_factor)
        
        # Minimum damage is 1
        return max(1, scaled_damage)
    
    def _update_scaling_factors(self, combo_state: SF3ComboState):
        """Update scaling factors for next hit"""
        # Update damage scaling for next hit
        next_hit_number = combo_state.combo_count + 1
        scaling_index = min(next_hit_number - 1, len(self.DAMAGE_SCALING_TABLE) - 1)
        combo_state.damage_scaling = self.DAMAGE_SCALING_TABLE[scaling_index]
        
        # Update gravity scaling for juggles (simplified)
        if combo_state.combo_type == SF3ComboType.JUGGLE:
            combo_state.gravity_scaling = max(0.5, 1.0 - (combo_state.combo_count * 0.1))
    
    def end_combo(self, player_id: int, reason: str = "recovered"):
        """End a combo for a player"""
        combo_state = self.player_combo_states[player_id]

        if combo_state.combo_active and combo_state.combo_count > 1:
            log.debug("COMBO ENDED: %s hits, %s damage (%s)",
                      combo_state.combo_count, combo_state.combo_damage, reason)

        combo_state.combo_active = False

    def update(self, in_hitstun_by_id: Optional[Dict[int, bool]] = None):
        """End any active combo whose defender has recovered from hitstun.

        A combo is a chain of hits the defender cannot recover between, so it
        ends the moment the defender leaves hitstun -- NOT on a wall-clock
        timeout (the old behavior, which both counted mashed jabs with recovery
        gaps as one long combo and was non-deterministic). Call once per frame
        with each player's current in-hitstun status.
        """
        if not in_hitstun_by_id:
            return
        for player_id, combo_state in self.player_combo_states.items():
            if combo_state.combo_active and not in_hitstun_by_id.get(player_id, False):
                self.end_combo(player_id, "recovered")
    
    def get_combo_count(self, player_id: int) -> int:
        """Get current combo count for a player"""
        return self.player_combo_states[player_id].combo_count
    
    def get_combo_damage(self, player_id: int) -> int:
        """Get total combo damage for a player"""
        return self.player_combo_states[player_id].combo_damage
    
    def is_in_combo(self, player_id: int) -> bool:
        """Check if player is currently being comboed"""
        return self.player_combo_states[player_id].combo_active
    
    def get_next_hit_scaling(self, player_id: int) -> float:
        """Get damage scaling for the next hit on a player"""
        combo_state = self.player_combo_states[player_id]
        if not combo_state.combo_active:
            return 1.0
        
        next_hit_number = combo_state.combo_count + 1
        scaling_index = min(next_hit_number - 1, len(self.DAMAGE_SCALING_TABLE) - 1)
        return self.DAMAGE_SCALING_TABLE[scaling_index]
    
    def reset_all_combos(self):
        """Reset all combo states"""
        for combo_state in self.player_combo_states.values():
            combo_state.reset()
    
    def get_combo_display_info(self, player_id: int) -> Dict[str, Any]:
        """Get combo information for display"""
        combo_state = self.player_combo_states[player_id]
        
        return {
            'count': combo_state.combo_count,
            'damage': combo_state.combo_damage,
            'last_damage': combo_state.combo_hits[-1].scaled_damage if combo_state.combo_hits else 0,
            'active': combo_state.combo_active,
            'scaling': combo_state.damage_scaling,
            'type': combo_state.combo_type.value
        }
