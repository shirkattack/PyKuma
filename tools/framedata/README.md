# Frame-data tooling

## NO INVENTED DATA

The converter in this directory exists to **replace eyeballed hitbox geometry
with ROM-accurate data**. It must never fabricate boxes, damage, stun, or
timing. Every value it emits is traceable to one of three provenance tiers,
and every box/move it writes is tagged with its tier:

| Tier        | What                                            | Source                                                                 |
|-------------|-------------------------------------------------|------------------------------------------------------------------------|
| `verified`  | box geometry + frame timing                     | SF3:3S ROM dump via [3rd_training_lua](https://github.com/Grouflon/3rd_training_lua) |
| `inferred`  | ROM-pointer → `CharacterState` (the move *name*) | matched timing/geometry against community data; the **name is a guess** |
| `community` | damage / stun / frame advantage                 | Baston ESN3S frame data + existing gameplay tuning; **NOT ROM-verified** |

## convert_3rd_training.py

Reads the vendored `data/sources/gouki_framedata.json` (see
`data/sources/SOURCE.txt` for provenance) and emits
`data/characters/akuma/hitboxes.yaml` in PyKuma offset coordinates.

```bash
python tools/framedata/convert_3rd_training.py data/sources/gouki_framedata.json \
    --name akuma \
    --names data/characters/akuma/move_names.json \
    --combat data/characters/akuma/sf3_authentic_frame_data.yaml \
    --out data/characters/akuma/hitboxes.yaml
```

Sensible defaults are derived from `--name`, so this also works:

```bash
python tools/framedata/convert_3rd_training.py data/sources/gouki_framedata.json --name akuma
```

The converter performs a self-check on the idle base boxes (pushbox / throwbox /
hurtbox) and refuses to run if the well-known values do not match the source.

### Coordinate conversion

Source boxes give the lower-left **edge** (`left`, `bottom`) with forward = −x.
PyKuma wants `offset_y` = the **top** edge (negative = up from the feet),
attack `offset_x` = **left** edge (forward-positive), and hurt/push/throw
`offset_x` = **center** (forward-positive). All of this lives in the single
`convert_box(box, *, centered)` function. No scale factor is applied
(native ≈ 107 px).
