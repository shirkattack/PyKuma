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

## Easiest path: reuse `3rd_training_lua`

It already follows `hb_vulnerability_pointer` and *draws* v_hb live — it just
doesn't persist them per move. Run it in FBNeo/MAME on `sfiii3nr1` and either:
1. extend its frame-data dump to also write the `vulnerability` boxes per frame, or
2. add a tiny dump hook (Lua) that, each frame, records `{state/anim pointer,
   anim_frame, [boxes by type]}` to a file.

Drive every move once (training-mode record, or scripted inputs) so each move's
animation plays through its active frames.

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
