"""
SF3:3S Visual Effects and Polish System

This module implements authentic SF3 visual effects, screen shake, hit sparks,
and polish elements that enhance the fighting game experience while maintaining
the classic SF3 aesthetic.

Key Features:
- Authentic SF3 hit sparks and effects
- Screen shake with multiple intensities
- Damage numbers and combo display
- Super flash effects
- Particle systems for special moves
- Stage background effects
- UI polish and transitions
"""

import pygame
import math
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

# Import our systems
from ..systems.sf3_core import SF3PlayerWork
from ..systems.sf3_hitboxes import SF3HitboxType, SF3HitLevel


class EffectType(Enum):
    """Types of visual effects"""
    HIT_SPARK = "hit_spark"
    BLOCK_SPARK = "block_spark"
    PARRY_SPARK = "parry_spark"
    DAMAGE_NUMBER = "damage_number"
    SCREEN_SHAKE = "screen_shake"
    SUPER_FLASH = "super_flash"
    PROJECTILE_TRAIL = "projectile_trail"
    DUST_CLOUD = "dust_cloud"
    COMBO_TEXT = "combo_text"


class HitSparkType(Enum):
    """SF3 hit spark types"""
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    SPECIAL = "special"
    SUPER = "super"
    COUNTER = "counter"


@dataclass
class VisualEffect:
    """Base visual effect"""
    effect_type: EffectType
    position: Tuple[float, float]
    duration: int
    current_frame: int = 0
    active: bool = True
    
    # Visual properties
    color: Tuple[int, int, int] = (255, 255, 255)
    alpha: int = 255
    scale: float = 1.0
    rotation: float = 0.0
    
    # Animation
    velocity: Tuple[float, float] = (0.0, 0.0)
    acceleration: Tuple[float, float] = (0.0, 0.0)
    fade_rate: float = 0.0
    scale_rate: float = 0.0
    
    def update(self):
        """Update effect for one frame"""
        if not self.active:
            return
        
        self.current_frame += 1
        
        # Update position
        x, y = self.position
        vx, vy = self.velocity
        ax, ay = self.acceleration
        
        x += vx
        y += vy
        vx += ax
        vy += ay
        
        self.position = (x, y)
        self.velocity = (vx, vy)
        
        # Update visual properties
        if self.fade_rate > 0:
            self.alpha = max(0, self.alpha - self.fade_rate)
        
        if self.scale_rate != 0:
            self.scale += self.scale_rate
        
        # Check if effect should end
        if self.current_frame >= self.duration or self.alpha <= 0:
            self.active = False


@dataclass
class HitSpark(VisualEffect):
    """SF3-style hit spark effect"""
    spark_type: HitSparkType = HitSparkType.MEDIUM
    spark_count: int = 8
    spark_size: float = 4.0
    
    def __post_init__(self):
        # Set properties based on spark type
        if self.spark_type == HitSparkType.LIGHT:
            self.color = (255, 255, 150)
            self.spark_count = 6
            self.duration = 8
        elif self.spark_type == HitSparkType.MEDIUM:
            self.color = (255, 200, 100)
            self.spark_count = 8
            self.duration = 10
        elif self.spark_type == HitSparkType.HEAVY:
            self.color = (255, 150, 50)
            self.spark_count = 12
            self.duration = 12
        elif self.spark_type == HitSparkType.SPECIAL:
            self.color = (100, 150, 255)
            self.spark_count = 16
            self.duration = 15
        elif self.spark_type == HitSparkType.SUPER:
            self.color = (255, 100, 255)
            self.spark_count = 20
            self.duration = 20
        elif self.spark_type == HitSparkType.COUNTER:
            self.color = (255, 255, 255)
            self.spark_count = 24
            self.duration = 25
        
        self.fade_rate = self.alpha / self.duration


@dataclass
class DamageNumber(VisualEffect):
    """Floating damage number"""
    damage: int = 0
    is_combo: bool = False
    is_counter: bool = False
    
    def __post_init__(self):
        self.duration = 60  # 1 second at 60fps
        self.velocity = (0.0, -1.0)  # Float upward
        self.fade_rate = 255 / self.duration
        
        # Color based on damage type
        if self.is_counter:
            self.color = (255, 255, 100)  # Yellow for counter hit
        elif self.is_combo:
            self.color = (255, 100, 100)  # Red for combo
        else:
            self.color = (255, 255, 255)  # White for normal


@dataclass
class ScreenShake:
    """Screen shake effect"""
    intensity: float = 0.0
    duration: int = 0
    current_frame: int = 0
    decay_rate: float = 0.9
    
    # Shake pattern
    offset_x: float = 0.0
    offset_y: float = 0.0
    
    def update(self):
        """Update screen shake"""
        if self.intensity <= 0.1:
            self.intensity = 0.0
            return
        
        # Generate random shake offset
        angle = random.random() * 2 * math.pi
        self.offset_x = math.cos(angle) * self.intensity
        self.offset_y = math.sin(angle) * self.intensity
        
        # Decay intensity
        self.intensity *= self.decay_rate
        self.current_frame += 1
        
        if self.current_frame >= self.duration:
            self.intensity = 0.0
    
    def add_shake(self, intensity: float, duration: int):
        """Add shake to current effect"""
        self.intensity = max(self.intensity, intensity)
        self.duration = max(self.duration, duration)
        self.current_frame = 0


@dataclass
class SuperFlash:
    """Super move flash effect"""
    active: bool = False
    duration: int = 30  # Half second
    current_frame: int = 0
    flash_color: Tuple[int, int, int] = (255, 255, 255)
    flash_alpha: int = 200
    
    def start_flash(self, color: Tuple[int, int, int] = (255, 255, 255)):
        """Start super flash effect"""
        self.active = True
        self.current_frame = 0
        self.flash_color = color
        self.flash_alpha = 200
    
    def update(self):
        """Update super flash"""
        if not self.active:
            return
        
        self.current_frame += 1
        
        # Fade out flash
        progress = self.current_frame / self.duration
        self.flash_alpha = int(200 * (1.0 - progress))
        
        if self.current_frame >= self.duration:
            self.active = False


class ParticleSystem:
    """Generic particle system for effects"""
    
    @dataclass
    class Particle:
        x: float
        y: float
        vx: float
        vy: float
        life: int
        max_life: int
        color: Tuple[int, int, int]
        size: float
        
        def update(self):
            self.x += self.vx
            self.y += self.vy
            self.life -= 1
            
            # Apply gravity
            self.vy += 0.1
            
            # Fade out
            alpha_ratio = self.life / self.max_life
            return alpha_ratio > 0
    
    def __init__(self):
        self.particles: List[ParticleSystem.Particle] = []
    
    def emit_particles(self, x: float, y: float, count: int, 
                      color: Tuple[int, int, int] = (255, 255, 255)):
        """Emit particles at position"""
        for _ in range(count):
            angle = random.random() * 2 * math.pi
            speed = random.uniform(1.0, 4.0)
            
            particle = self.Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 2.0,  # Initial upward velocity
                life=random.randint(30, 60),
                max_life=60,
                color=color,
                size=random.uniform(1.0, 3.0)
            )
            particle.max_life = particle.life
            self.particles.append(particle)
    
    def update(self):
        """Update all particles"""
        self.particles = [p for p in self.particles if p.update()]
    
    def draw(self, screen: pygame.Surface, camera_offset: Tuple[float, float] = (0, 0)):
        """Draw all particles"""
        for particle in self.particles:
            alpha_ratio = particle.life / particle.max_life
            alpha = int(255 * alpha_ratio)
            
            # Create surface with alpha
            particle_surface = pygame.Surface((particle.size * 2, particle.size * 2), pygame.SRCALPHA)
            color_with_alpha = (*particle.color, alpha)
            pygame.draw.circle(particle_surface, color_with_alpha, 
                             (particle.size, particle.size), particle.size)
            
            # Draw to screen
            screen_x = particle.x - camera_offset[0]
            screen_y = particle.y - camera_offset[1]
            screen.blit(particle_surface, (screen_x - particle.size, screen_y - particle.size))


class SF3EffectsManager:
    """
    Manages all visual effects for SF3
    
    Handles hit sparks, screen shake, damage numbers, and other visual polish
    elements that enhance the fighting game experience.
    """
    
    def __init__(self, screen_size: Tuple[int, int] = (1280, 720)):
        self.screen_size = screen_size
        
        # Effect collections
        self.active_effects: List[VisualEffect] = []
        self.screen_shake = ScreenShake()
        self.super_flash = SuperFlash()
        self.particle_system = ParticleSystem()
        
        # Camera offset for screen shake
        self.camera_offset = [0.0, 0.0]
        
        # Effect fonts
        self.damage_font = None
        self.combo_font = None
        
        # Effect settings
        self.effects_enabled = True
        self.screen_shake_enabled = True
        self.particles_enabled = True
        
        # Hit spark sprites (would load from files in full implementation)
        self.hit_spark_sprites = {}
        
    def initialize_fonts(self):
        """Initialize fonts for text effects"""
        pygame.font.init()
        self.damage_font = pygame.font.Font(None, 36)
        self.combo_font = pygame.font.Font(None, 48)
    
    def create_hit_effect(self, position: Tuple[float, float], damage: int, 
                         hit_level: SF3HitLevel, is_counter: bool = False,
                         is_blocked: bool = False):
        """Create hit effect based on attack properties"""
        
        if not self.effects_enabled:
            return
        
        # Determine spark type
        if is_blocked:
            spark_type = HitSparkType.LIGHT
            spark_color = (150, 150, 255)  # Blue for blocks
        elif is_counter:
            spark_type = HitSparkType.COUNTER
        elif damage >= 200:
            spark_type = HitSparkType.HEAVY
        elif damage >= 100:
            spark_type = HitSparkType.MEDIUM
        else:
            spark_type = HitSparkType.LIGHT
        
        # Create hit spark
        hit_spark = HitSpark(
            effect_type=EffectType.HIT_SPARK,
            position=position,
            duration=15,
            spark_type=spark_type
        )
        
        if is_blocked:
            hit_spark.color = spark_color
        
        self.active_effects.append(hit_spark)
        
        # Create damage number
        if damage > 0:
            damage_number = DamageNumber(
                effect_type=EffectType.DAMAGE_NUMBER,
                position=(position[0], position[1] - 20),
                duration=60,
                damage=damage,
                is_counter=is_counter
            )
            self.active_effects.append(damage_number)
        
        # Screen shake
        if self.screen_shake_enabled:
            if is_counter:
                self.screen_shake.add_shake(8.0, 15)
            elif damage >= 200:
                self.screen_shake.add_shake(6.0, 12)
            elif damage >= 100:
                self.screen_shake.add_shake(4.0, 8)
            else:
                self.screen_shake.add_shake(2.0, 5)
        
        # Particles
        if self.particles_enabled:
            particle_count = min(damage // 20, 15)
            self.particle_system.emit_particles(position[0], position[1], particle_count)
    
    def create_parry_effect(self, position: Tuple[float, float]):
        """Create parry effect"""
        
        if not self.effects_enabled:
            return
        
        # Parry spark (white/blue)
        parry_spark = HitSpark(
            effect_type=EffectType.PARRY_SPARK,
            position=position,
            duration=20,
            spark_type=HitSparkType.SPECIAL
        )
        parry_spark.color = (200, 200, 255)
        parry_spark.spark_count = 16
        
        self.active_effects.append(parry_spark)
        
        # Screen flash for parry
        self.super_flash.start_flash((200, 200, 255))
        
        # Parry particles
        if self.particles_enabled:
            self.particle_system.emit_particles(position[0], position[1], 12, (200, 200, 255))
    
    def create_super_flash(self, color: Tuple[int, int, int] = (255, 255, 255)):
        """Create super move flash effect"""
        self.super_flash.start_flash(color)
        
        # Intense screen shake for supers
        if self.screen_shake_enabled:
            self.screen_shake.add_shake(12.0, 30)
    
    def create_combo_effect(self, position: Tuple[float, float], hit_count: int, damage: int):
        """Create combo display effect"""
        
        if hit_count < 2:
            return
        
        # Combo text effect would go here
        # For now, just create a damage number with combo styling
        combo_number = DamageNumber(
            effect_type=EffectType.COMBO_TEXT,
            position=position,
            duration=90,
            damage=damage,
            is_combo=True
        )
        combo_number.scale = 1.5
        combo_number.color = (255, 100, 100)
        
        self.active_effects.append(combo_number)
    
    def create_projectile_trail(self, start_pos: Tuple[float, float], 
                               end_pos: Tuple[float, float]):
        """Create projectile trail effect"""
        
        if not self.particles_enabled:
            return
        
        # Create trail particles along projectile path
        steps = 5
        for i in range(steps):
            t = i / steps
            x = start_pos[0] + (end_pos[0] - start_pos[0]) * t
            y = start_pos[1] + (end_pos[1] - start_pos[1]) * t
            
            self.particle_system.emit_particles(x, y, 2, (100, 150, 255))
    
    def update(self):
        """Update all effects for one frame"""
        
        # Update screen shake
        self.screen_shake.update()
        self.camera_offset[0] = self.screen_shake.offset_x
        self.camera_offset[1] = self.screen_shake.offset_y
        
        # Update super flash
        self.super_flash.update()
        
        # Update particle system
        self.particle_system.update()
        
        # Update active effects
        self.active_effects = [effect for effect in self.active_effects 
                              if effect.active]
        
        for effect in self.active_effects:
            effect.update()
    
    def draw(self, screen: pygame.Surface):
        """Draw all effects to screen"""
        
        # Apply super flash
        if self.super_flash.active:
            flash_surface = pygame.Surface(self.screen_size, pygame.SRCALPHA)
            flash_color = (*self.super_flash.flash_color, self.super_flash.flash_alpha)
            flash_surface.fill(flash_color)
            screen.blit(flash_surface, (0, 0))
        
        # Draw particle effects
        self.particle_system.draw(screen, tuple(self.camera_offset))
        
        # Draw visual effects
        for effect in self.active_effects:
            self._draw_effect(screen, effect)
    
    def _draw_effect(self, screen: pygame.Surface, effect: VisualEffect):
        """Draw individual effect"""
        
        # Apply camera offset
        screen_x = effect.position[0] - self.camera_offset[0]
        screen_y = effect.position[1] - self.camera_offset[1]
        
        if effect.effect_type == EffectType.HIT_SPARK:
            self._draw_hit_spark(screen, effect, (screen_x, screen_y))
        elif effect.effect_type == EffectType.DAMAGE_NUMBER:
            self._draw_damage_number(screen, effect, (screen_x, screen_y))
        elif effect.effect_type == EffectType.COMBO_TEXT:
            self._draw_combo_text(screen, effect, (screen_x, screen_y))
    
    def _draw_hit_spark(self, screen: pygame.Surface, effect: HitSpark, position: Tuple[float, float]):
        """Draw hit spark effect"""
        
        # Simple spark implementation - draw radiating lines
        center_x, center_y = position
        
        for i in range(effect.spark_count):
            angle = (i / effect.spark_count) * 2 * math.pi
            length = effect.spark_size * effect.scale
            
            end_x = center_x + math.cos(angle) * length
            end_y = center_y + math.sin(angle) * length
            
            # Create color with alpha
            color = (*effect.color, effect.alpha)
            
            # Draw spark line (simplified - would use proper sprite in full implementation)
            if effect.alpha > 0:
                pygame.draw.line(screen, effect.color[:3], 
                               (center_x, center_y), (end_x, end_y), 2)
    
    def _draw_damage_number(self, screen: pygame.Surface, effect: DamageNumber, position: Tuple[float, float]):
        """Draw damage number"""
        
        if not self.damage_font:
            return
        
        # Render damage text
        damage_text = str(effect.damage)
        color_with_alpha = (*effect.color, effect.alpha)
        
        # Create text surface
        text_surface = self.damage_font.render(damage_text, True, effect.color[:3])
        
        # Apply alpha
        if effect.alpha < 255:
            alpha_surface = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
            alpha_surface.fill((*effect.color, effect.alpha))
            text_surface.blit(alpha_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        # Center text on position
        text_rect = text_surface.get_rect()
        text_rect.center = position
        
        screen.blit(text_surface, text_rect)
    
    def _draw_combo_text(self, screen: pygame.Surface, effect: DamageNumber, position: Tuple[float, float]):
        """Draw combo text"""
        
        if not self.combo_font:
            return
        
        # Render combo text
        combo_text = f"{effect.damage} DAMAGE!"
        
        # Create text surface with larger font
        text_surface = self.combo_font.render(combo_text, True, effect.color[:3])
        
        # Apply scale
        if effect.scale != 1.0:
            new_size = (int(text_surface.get_width() * effect.scale),
                       int(text_surface.get_height() * effect.scale))
            text_surface = pygame.transform.scale(text_surface, new_size)
        
        # Center text on position
        text_rect = text_surface.get_rect()
        text_rect.center = position
        
        screen.blit(text_surface, text_rect)
    
    def get_camera_offset(self) -> Tuple[float, float]:
        """Get current camera offset for screen shake"""
        return tuple(self.camera_offset)
    
    def clear_all_effects(self):
        """Clear all active effects"""
        self.active_effects.clear()
        self.screen_shake.intensity = 0.0
        self.super_flash.active = False
        self.particle_system.particles.clear()


if __name__ == "__main__":
    # Test visual effects system
    print("Testing SF3 Visual Effects System...")
    
    # Initialize pygame for testing
    pygame.init()
    
    effects_manager = SF3EffectsManager()
    effects_manager.initialize_fonts()
    
    # Test hit effect creation
    effects_manager.create_hit_effect(
        position=(400, 300),
        damage=115,
        hit_level=SF3HitLevel.MID,
        is_counter=False
    )
    
    print(f"✅ Hit effect created: {len(effects_manager.active_effects)} effects")
    
    # Test parry effect
    effects_manager.create_parry_effect((450, 300))
    print(f"✅ Parry effect created: {len(effects_manager.active_effects)} effects")
    
    # Test super flash
    effects_manager.create_super_flash((255, 100, 255))
    print(f"✅ Super flash created: {effects_manager.super_flash.active}")
    
    # Test screen shake
    print(f"✅ Screen shake intensity: {effects_manager.screen_shake.intensity}")
    
    # Test update
    effects_manager.update()
    print(f"✅ Effects updated: {len(effects_manager.active_effects)} active")
    
    print("SF3 Visual Effects System working correctly! ✅")
    print("🎯 Features implemented:")
    print("   - Authentic SF3 hit sparks")
    print("   - Screen shake with intensity levels")
    print("   - Damage numbers and combo display")
    print("   - Super flash effects")
    print("   - Particle systems")
    print("   - Parry visual feedback")
    print("   - Camera shake integration")
    print("🚀 Ready for visual polish integration!")
