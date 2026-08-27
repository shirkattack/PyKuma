# ROM box extractor (per-move vulnerability + all box types)

**Status: documented data-gen procedure — you run it on your machine** (needs an
emulator + the `sfiii3nr1` ROM; the cloud/dev env has neither). It backfills the
authoritative per-move data that the existing dump is missing.

## Why this exists

`data/sources/gouki_framedata.json` (from `Grouflon/3rd_training_lua`) carries
`vulnerability` boxes on **only** `idle` + `wakeup_to_idle` — every *attacking*
move records only its `attack` boxes. So a limb that becomes hittable during a
move (per-move "v_hb") is missing. Until this extractor runs, those are seeded
from Baston in `data/characters/akuma/vhb_supplement.json` (status `baston`) for
st.LP/st.LK/st.MK only.

The data **is** in the ROM at runtime — it's just not persisted by that dump.
Static parsing of `sfiii3nr1.zip` is impractical (CPS3 SH-2 encryption); the
authoritative route is **reading live RAM in an emulator**.

## What to read (P1 RAM, CPS3 / `sfiii3nr1`)

```
hb_base_address            0x02068C6C
hb_active_base_address      0x02068F34   -> attack boxes
hb_vulnerability_pointer    0x02068F14   -> per-move hurt boxes  (the missing data)
hb_push_base_address        0x02068F40   -> pushbox
hb_throw_base_address       0x02068F24
hb_throwable_base_address   0x02068F2C
state      0x02068E75   anim_frame 0x02068E86
pos_x      0x02068CD0   pos_y      0x02068CD4   facing_dir 0x02068C76
```
Each box is four signed words (X, WIDTH, HEIGHT, Y) — same `{left,width,height,
bottom}` meaning as the JSON (see `docs/HITBOX_PIPELINE_NOTES.md` §3-§5 for the
exact convention and the PyKuma conversion).

## Ready-to-run tooling in this folder

You don't have to write the hook — it's here:

- **`dump_framedata.lua`** — a standalone FBNeo/fba-rr Lua dumper. Its memory
  layout is verbatim from `3rd_training_lua` @73ec4c06 `src/gamestate.lua`
  (`read_game_object` / `read_box`): the box pointer at `(base+offset)` is
  dereferenced, boxes are 8 bytes `left,width,bottom,height` (s16). Each frame it
  writes one JSON object (pos, facing, posture, anim id, anim frame, all box
  types) to `pykuma_dump.jsonl`. Press **R** to start/stop recording.
- **`ingest.py`** — reshapes the dump (no emulator needed; unit-tested in
  `tests/test_rom_ingest.py`): `validate` (cross-check vs Baston), `merge`
  (enrich `gouki_framedata.json` with per-move v_hb), `physics` (derive
  walk/jump/dash → `physics.yaml`).
- **`CAPTURE.md`** — the exact moves/movement to drive, step by step.

Drive every move once (training-mode record, or scripted inputs) so each move's
animation plays through its active frames; see `CAPTURE.md`.

## Output format (so the Python pipeline just works)

Emit an **enriched** `gouki_framedata.json` in the *same schema* as the current
file — each move keyed by ROM pointer, `frames[].boxes[]` with
`{type,left,bottom,width,height}` — but now including `type:"vulnerability"`
boxes on the attacking frames. Drop it at `data/sources/gouki_framedata.json`
and run:

```
python tools/framedata/convert_3rd_training.py data/sources/gouki_framedata.json --name akuma
```

The converter **already** reads per-frame `vulnerability` boxes
(`build_move`), so no code change is needed — the supplement just becomes
redundant once real data lands (delete `vhb_supplement.json` or leave it as a
fallback).

## Validate the extractor

`ingest.py validate` cross-checks the extracted per-move box against the Baston
seed in `vhb_supplement.json` (LP / LK / MK, each also checked against its
close/far variant since Baston labels those separately):
- LP `{left:-54,width:22,height:18,bottom:84}` (this is the *close* jab, 13a8)
- LK `{left:-64,width:38,height:34,bottom:20}`
- MK `{left:-62,width:32,height:32,bottom:44}`

**Validated 2026-08-26:** LK's `ext_vulnerability` box is pixel-exact to the
seed, so `ext_vulnerability` is the per-move v_hb array and the extractor reads
it correctly. (Far LP, 1438, reads `{-76,44,74,20}`; 13a8 was not driven.)

`merge` only annotates a move whose captured attack boxes line up frame-for-frame
with the vendored framedata and reports the rest as `misaligned` /
`no_attack_boxes` — a connect freezes the attacker (hitstop) and the ROM does not
resume the cel timeline in a way the dump can reproduce for every move, so
**drive moves on whiff for the hurtbox pass**.


## Sprite (cel) extraction — probe

The sprites themselves can be read out of the emulator too. `dump_cels.lua`
dumps, for one frame, the CPS3 sprite list (every object's parts: tile
numbers, flips, palette, offsets from the object's origin) and the palettes
(`0x04080000`, 15-bit RGB), and writes a **savestate** on the same frame: the
8 MB character RAM holding the 16x16 tiles is only reachable from Lua through
a 1 MB bank window whose bank register the Lua API cannot write, but FBNeo
states are uncompressed and carry it whole (entry "Sprite ROM").
`cel_decode.py` takes the tiles from the state and rebuilds each object as a
PNG whose origin is the object's own axis, so a character cel comes out
pixel-exact with the true sprite/axis offset (formats: MAME `cps3.cpp`,
FBNeo `cps3run.cpp` / `statec.cpp`).

    # Fightcade: Misc > Lua Scripting > Browse > fbneo-training-mode/dump_cels.lua > Run
    # stand still in stance, press C  ->  pykuma_cels.jsonl next to the script
    uv run python tools/rom_extract/cel_decode.py \
        ~/.var/app/com.fightcade.Fightcade/data/fbneo-training-mode/pykuma_cels.jsonl --out /tmp/cels

The table it prints lists every object with its origin and bbox. The players
are the objects whose `xpos` equals their `pos_x` (the camera is applied by
the PPU), ~35 tiles each; the two 7-tile objects at the same x are their
shadows.

**Verified 2026-08-27** (stance cel, P1 and the x-flipped P2 pixel-exact,
axis between the feet). What the two probe rounds established:
- Lua `memory.write*` goes through FBNeo's *byte* handler; the char-RAM bank
  register is word-only, so it cannot be switched from Lua. The savestate is
  the way to the tiles.
- Fightcade's FBNeo state: `FB1 ` + `FS1 ` chunk with a 0x44-byte header,
  then a zlib stream starting 4 bytes in; the scanned areas are concatenated
  with no per-area headers (current FBNeo writes `[id][len][hash]` entries,
  which the decoder also reads). The 8 MB char RAM is anchored by a bank-0
  tile the Lua read (shadow tiles 128-131); the 0x40000-byte palette RAM sits
  right before it.
- Tile pixel x is byte `x ^ 3` of its 16-byte row, both in the state (host
  order, FBNeo renders `source[x ^ 3]`) and via the Lua reads.
- The Lua-read palette is in rendering (CPU) order; the state stores it with
  adjacent words swapped (`RamPal[i ^ 1]`), which the decoder swaps back.
- Part offsets are 10-bit signed; a part's position is its centre.

Next: dump automatically on every new ROM cel id (`anim_frame`) during a
whiff pass and key the PNGs by cel -- sprites, axis offsets and durations all
from the ROM.
