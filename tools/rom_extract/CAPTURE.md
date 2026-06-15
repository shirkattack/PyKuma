# Capture recipe — ROM frame-data + physics (Akuma / Gouki)

You run this once in the emulator that runs `3rd_training_lua` (FBNeo / fba-rr)
on `sfiii3nr1`. It produces a JSON-Lines dump that `ingest.py` turns into
per-move hurtboxes and physics constants. **No data is invented** — everything is
read from live ROM memory using the exact layout `3rd_training_lua` uses.

## 0. Setup
1. Launch the emulator, load **sfiii3nr1**, choose **Gouki (Akuma)** as **P1**.
2. Enter **Training** (or Versus vs a dummy). P1 must be the character you drive.
3. Open the Lua console and run `tools/rom_extract/dump_framedata.lua`.
   - Output goes to `pykuma_dump.jsonl` in the emulator's working directory.
   - Press **R** to start/stop recording (an on-screen `REC <n>` shows frames).

Do **two separate recordings** (rename the file between them), then bring both
back to the repo.

## 1. Move-coverage capture  → `moves_dump.jsonl`
Goal: every attacking move plays through its **active frames** so we capture each
move's per-move vulnerability (v_hb) limb boxes.

With recording ON, perform each move once, pausing a beat between them so frames
are clean:
- Standing: LP, MP, HP, LK, MK, HK
- Crouching: LP, MP, HP, LK, MK, HK
- Jumping (neutral): LP, MP, HP, LK, MK, HK
- Specials: Gohadoken (all strengths), Shoryuken, Tatsumaki, plus SAs if easy
- Also stand idle a moment (re-confirms the base hurtbox stack)

Stop recording. Save as `moves_dump.jsonl`.

## 2. Movement-coverage capture  → `move_phys.jsonl`
Goal: clean position series to derive walk / jump / dash. Do each in isolation
with a short neutral pause between, recording ON:
- Walk **forward** ~2 seconds, return to neutral
- Walk **back** ~2 seconds, neutral
- **Forward dash**, neutral
- **Back dash**, neutral
- **Neutral jump** (let it fully land), neutral
- **Forward jump** (full), neutral
- **Back jump** (full), neutral

Stop recording. Save as `move_phys.jsonl`.

## 3. Ingest (back in the repo, via uv)
```
# Sanity-check the extractor read boxes correctly (must match Baston seed):
uv run python tools/rom_extract/ingest.py validate moves_dump.jsonl

# Per-move hurtboxes -> enriched framedata, then re-run the existing converter:
uv run python tools/rom_extract/ingest.py merge moves_dump.jsonl \
    --out data/sources/gouki_framedata.enriched.json
#   review the diff, then replace data/sources/gouki_framedata.json with it and:
uv run python tools/framedata/convert_3rd_training.py \
    data/sources/gouki_framedata.json --name akuma

# Physics constants -> physics.yaml (flagged for review):
uv run python tools/rom_extract/ingest.py physics move_phys.jsonl \
    --out data/characters/akuma/physics.yaml
```

## 4. What "correct" looks like
- `validate` prints, for st.LP / st.LK / st.MK, which ROM array
  (`vulnerability` vs `ext_vulnerability`) matches the Baston seed
  (LP `{-54,22,84,18}`, LK `{-64,38,20,34}`, MK `{-62,32,44,32}` as
  `{left,width,bottom,height}`). The matching array is the per-move v_hb source.
- `physics.yaml` lists a detected jump (gravity, initial velocity, airborne
  frames, apex), walk speed, and dash runs (distance + per-frame curve).

Hand both `*.jsonl` (or the generated files) back and I'll apply them in Phase 5.
