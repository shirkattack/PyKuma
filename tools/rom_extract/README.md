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

Cross-check the extracted v_hb for st.LP / st.LK / st.MK against the Baston seed
already in `vhb_supplement.json`:
- LP `{left:-54,width:22,height:18,bottom:84}`
- LK `{left:-64,width:38,height:34,bottom:20}`
- MK `{left:-62,width:32,height:32,bottom:44}`
If those match (after conversion), the extractor is reading the boxes correctly
and you can trust the rest.
