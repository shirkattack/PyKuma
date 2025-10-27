# Standing Light Punch (LP) Sprite Mapping

## Animation Analysis: akuma-wp

**Total Frames:** 6 frames
**Frame Range:** 18664-18672 (estimated)

## Frame-by-Frame Mapping

### GIF Frame 0 → Sprite 18664
**Description:** Neutral standing stance
- Arms at ready position
- Balanced stance
- **This is the startup frame**

### GIF Frame 1 → Sprite 18666-18667
**Description:** Punch beginning
- Arm starts to extend forward
- Body begins slight lean
- **Startup continues (frame 2-3 of move)**

### GIF Frame 2 → Sprite 18669-18670
**Description:** Punch fully extended ⚡ **ACTIVE FRAME**
- Arm fully extended forward (jab)
- Fist at maximum reach
- **This is where the hitbox is active**
- **Most important frame for collision detection**

### GIF Frame 3 → Sprite 18670-18671
**Description:** Punch held/beginning retraction
- Arm still extended or starting to pull back
- **Late active frame or early recovery**

### GIF Frame 4 → Sprite 18671-18672
**Description:** Arm retracting
- Fist pulling back toward body
- **Recovery frames**

### GIF Frame 5 → Sprite 18672-18664
**Description:** Return to neutral
- Arm back at ready position
- Returns to standing stance
- **Recovery complete**

## Proposed Sprite Sequence (Best Guess)

```python
STANDING_LIGHT_PUNCH = [
    18664,  # Frame 0: Neutral (startup frame 1)
    18666,  # Frame 1: Starting punch (startup frame 2)
    18667,  # Frame 2: Extending (startup frame 3)
    18669,  # Frame 3: ACTIVE - arm fully extended (active frame 1)
    18670,  # Frame 4: ACTIVE - sustained (active frame 2)
    18671,  # Frame 5: Retracting (recovery frame 1)
    18672,  # Frame 6: Pulling back (recovery frame 2)
    18664,  # Frame 7: Return to neutral (recovery complete)
]
```

**Total Animation:** 8 frames (expanded from 6-frame GIF for smoother gameplay)

## SF3 Frame Data Reference

According to EventHubs SF3:3S frame data:
- **Startup:** 3 frames (frames before hitbox becomes active)
- **Active:** 3 frames (frames where hitbox can hit)
- **Recovery:** 6 frames (frames after hitbox deactivates)
- **Total:** 12 frames

## Adjusted Mapping (Match Frame Data)

To match official SF3 frame data more accurately:

```python
STANDING_LIGHT_PUNCH_ACCURATE = [
    # Startup (3 frames)
    18664,  # Frame 1: Neutral stance
    18666,  # Frame 2: Arm beginning to move
    18667,  # Frame 3: Arm extending

    # Active (3 frames) - HITBOX ACTIVE
    18669,  # Frame 4: Arm fully extended ⚡
    18670,  # Frame 5: Sustained extension ⚡
    18669,  # Frame 6: Still extended ⚡ (repeat for timing)

    # Recovery (6 frames)
    18671,  # Frame 7: Starting to retract
    18671,  # Frame 8: Retracting
    18672,  # Frame 9: Pulling back
    18672,  # Frame 10: Still pulling back
    18664,  # Frame 11: Nearly neutral
    18664,  # Frame 12: Back to neutral
]
```

## Implementation Notes

### Timing
- Each sprite frame should display for **1 game frame** (at 60 FPS = ~16.67ms)
- Total animation time: 12 frames = 200ms (0.2 seconds)
- This matches SF3's snappy light punch feel

### Hitbox Activation
- Hitbox should activate on **frame 4** (index 3 in array)
- Hitbox active for frames **4, 5, 6** (3 total frames)
- Hitbox deactivates on frame **7** (recovery begins)

### Animation Code Structure
```python
class Animation:
    def __init__(self, sprite_sequence, frame_duration=1):
        self.sprites = sprite_sequence  # List of sprite numbers
        self.frame_duration = frame_duration  # Frames to hold each sprite
        self.current_frame = 0
        self.frame_counter = 0

    def update(self):
        self.frame_counter += 1
        if self.frame_counter >= self.frame_duration:
            self.frame_counter = 0
            self.current_frame += 1

    def is_complete(self):
        return self.current_frame >= len(self.sprites)

    def get_current_sprite(self):
        if self.is_complete():
            return self.sprites[-1]  # Hold on last frame
        return self.sprites[self.current_frame]
```

## Testing Checklist

- [ ] Animation plays smoothly without stuttering
- [ ] Punch extends in correct direction (facing)
- [ ] Hitbox activates on frames 4-6
- [ ] Total animation takes exactly 200ms (12 frames @ 60fps)
- [ ] Character returns to neutral stance after animation
- [ ] Can transition to other moves after recovery
- [ ] Animation looks similar to GIF reference

## Next Steps

1. **Verify sprite sequence** by viewing 18664-18672 in sequence
2. **Implement animation system** in character class
3. **Test in-game** with button press
4. **Adjust timing** if animation feels too fast/slow
5. **Fine-tune sprite choices** if visual flow isn't smooth

---

**Status:** Initial mapping complete - requires visual verification ✅
**Confidence:** ~80% (need to verify exact sprite choices)
**Ready for implementation:** Yes, with testing
