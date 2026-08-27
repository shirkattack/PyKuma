--[[ ============================================================================
  PyKuma ROM frame-data dumper  (Street Fighter III: 3rd Strike, sfiii3nr1)

  Runs in the SAME emulator/Lua environment as Grouflon/3rd_training_lua
  (fba-rr / FBNeo Lua). It records, for Player 1, every frame: world position,
  facing, posture, the current animation id + frame, and ALL box types
  (push / throwable / vulnerability / ext. vulnerability / attack / throw),
  plus a combat snapshot of BOTH players ("c1"/"c2": life, applied damage
  and stun, hitstop, recovery, blocking, attack/defense multipliers) so
  `ingest.py combat` can derive ROM-exact damage / stun / hitstop / hitstun,
  read with the exact addresses + struct the training tool uses.

  Output: a JSON-Lines file (one JSON object per emulated frame) at OUT_PATH.
  Reconstruction into the converter schema + physics derivation happens in
  tools/rom_extract/ingest.py (so the Lua stays dumb and the Python is testable).

  Provenance: memory layout taken verbatim from
  github.com/Grouflon/3rd_training_lua @73ec4c06  src/gamestate.lua
  (read_game_object / read_box). Box pointer at (base+offset) is DEREFERENCED
  (readdword) then boxes are 8 bytes each: left,width,bottom,height (s16 each).

  USAGE (FBNeo Lua Script window — e.g. Fightcade on Linux):
    1. Load sfiii3nr1, pick Gouki (Akuma), enter training/versus (P1 = Akuma).
    2. Misc > Lua Scripting (or the Lua Script window) > Browse to this file >
       Run. Recording starts immediately (top-left shows "REC <n>").
    3. Drive every move once, then walk/dash/jump (see CAPTURE.md).
    4. Close the emulator (or Stop the script) — the file flushes automatically.
  Output `pykuma_dump.jsonl` is written in THIS script's folder (FBNeo uses the
  script's directory as the working dir). 'R' pauses/resumes if you want to skip
  menus. See tools/rom_extract/CAPTURE.md.

  Only one Lua script runs at a time, so Grouflon's training-mode script is NOT
  active while this one records: the round timer would run out and life would
  not refill. KEEP_ALIVE below does both itself (same writes as
  fbneo-training-mode.lua's games/sfiii3/sfiii3.lua): the timer is pinned at 99
  every frame, and a player's life is refilled to the 0xA0 bar only while that
  player is IDLE (no freeze, not busy), so the applied damage / hitstun the
  ingest reads during the hit reaction are untouched.

  The arcade ROM has no training menu, so the DUMMY is driven here too: press
  DUMMY_KEY ('B') to cycle  stand -> block -> block_always -> crouch_block ->
  jump  (shown top-left).  block / crouch_block hold "back" (relative to P2's
  facing) only while P1 is in a move or P2 is in blockstun, so the dummy stays
  put; block_always holds back permanently (it walks to the corner and blocks
  projectiles too); jump holds Up. Use stand for the hurtbox (whiff) pass and
  the hit pass, block for the on-block pass.
============================================================================ ]]

-- ---- config -----------------------------------------------------------------
local OUT_PATH = "pykuma_dump.jsonl"   -- written in the script's own folder
local KEEP_ALIVE = true                -- pin the round timer + refill life when idle
local DUMMY_KEY  = "B"                 -- cycle the dummy behaviour (P2)
local DUMMY_MODES = { "stand", "block", "block_always", "crouch_block", "jump" }
local P2_FACING  = 0x02068C77          -- byte: 1 = P2 faces left (P1 is on its left)
local TIMER_ADDR = 0x02011377          -- round timer (BCD); 0x63 = "99"
local FULL_LIFE  = 0xA0                -- the 160 life bar (VITAL.c)
local REC_KEY  = "R"                    -- optional: press to PAUSE/resume recording
local PLAYER_BASE = 0x02068C6C          -- P1 base (P2 is 0x02069104)
local P2_BASE     = 0x02069104

-- Combat capture (ROM-exact damage / stun / hitstop / hitstun). Every address
-- below is one 3rd_training_lua reads (src/gamestate.lua); the decomp
-- (crowded-street/3s-decomp, HITCHECK.c / Pow_Pow.c / VITAL.c) confirms the
-- semantics: dm_vital is the APPLIED damage after att_plus/def_plus, the life
-- bar is 0xA0 = 160 for everyone, hitstop is the freeze counter.
local COMBAT = {
  -- per-player WORK offsets
  vitality      = 0x9C,   -- word: internal vitality (the 0xA0 bar at +0x9E is derived from it)
  life          = 0x9F,   -- byte: remaining life bar (max 0xA0 = 160 px)
  dm_vital      = 0xA2,   -- word: dm_vital -- applied damage on the internal vitality scale
  dmg_next      = 0xA3,   -- byte: dm_vital -- damage this player is about to take
  stun_next     = 0x333,  -- byte: dm_piyo -- stun this player is about to take
  freeze        = 0x45,   -- byte: remaining freeze (hitstop) frames (>=127 => 256-v)
  recovery      = 0x187,  -- byte: recovery_time (counts down through stun)
  busy          = 0x3D1,  -- word: busy_flag (low byte != 0 while not idle)
  blocking_id   = 0x3D3,  -- byte: 1..4 while in blockstun
  hits_received = 0x33E,  -- word: total_received_hit_count (increments on HIT only)
  conn_marker   = 0x32E,  -- word: received_connection_marker (block/parry; 0xFFF1 = parry)
  input_cap     = 0x46C,  -- word: input_capacity (>0 when the player can act)
  att_bonus     = 0x43A,  -- word: att_plus (attack multiplier /8)
  stun_bonus    = 0x43E,  -- word
  def_bonus     = 0x440,  -- word: def_plus (defense multiplier /8)
}
-- stun gauge (global, per side): max / timer / bar (bar is the high byte of a dword)
local STUN_ADDR = { [1] = 0x020695F7, [2] = 0x0206960B }

-- Box arrays: a POINTER lives at (base+offset); each box is 8 bytes.
-- (number = max boxes of that type; inactive slots are filtered out below.)
local BOX_DEFS = {
  { offset = 0x2D4, type = "push",              number = 1 },
  { offset = 0x2C0, type = "throwable",         number = 1 },
  { offset = 0x2A0, type = "vulnerability",     number = 4 },
  { offset = 0x2A8, type = "ext_vulnerability", number = 4 },
  { offset = 0x2C8, type = "attack",            number = 4 },
  { offset = 0x2B8, type = "throw",             number = 1 },
}

-- ---- emulator memory shims (match 3rd_training_lua's API) --------------------
local rdword  = memory.readword
local rdwords = memory.readwordsigned
local rdbyte  = memory.readbyte
local rdbytes = memory.readbytesigned
local rddword = memory.readdword

-- ---- tiny JSON writer (records are flat: numbers, short strings, arrays) -----
local function jnum(n) return string.format("%d", n) end
local function jstr(s) return '"' .. s .. '"' end  -- ids are hex/ascii, no escapes

local function box_to_json(b)
  return "{" ..
    '"type":' .. jstr(b.type) .. "," ..
    '"left":' .. jnum(b.left) .. "," ..
    '"width":' .. jnum(b.width) .. "," ..
    '"bottom":' .. jnum(b.bottom) .. "," ..
    '"height":' .. jnum(b.height) .. "}"
end

-- ---- reads ------------------------------------------------------------------
local function read_box(ptr, btype)
  return {
    left   = rdwords(ptr + 0x0),
    width  = rdwords(ptr + 0x2),
    bottom = rdwords(ptr + 0x4),
    height = rdwords(ptr + 0x6),
    type   = btype,
  }
end

-- a box slot is "real" only when it has positive area and sane magnitude
local function box_ok(b)
  if b.width <= 0 or b.height <= 0 then return false end
  if math.abs(b.left) > 512 or math.abs(b.bottom) > 512 then return false end
  if b.width > 512 or b.height > 512 then return false end
  return true
end

local function read_boxes(base)
  local out = {}
  for _, def in ipairs(BOX_DEFS) do
    local arr = rddword(base + def.offset)       -- dereference the pointer
    if arr ~= 0 then
      for i = 1, def.number do
        local b = read_box(arr + (i - 1) * 8, def.type)
        if box_ok(b) then out[#out + 1] = b end
      end
    end
  end
  return out
end

local function unwrap_freeze(v)
  if v >= 127 then return 256 - v end   -- 3rd_training_lua: negative = "frozen by own hit"
  return v
end

-- One player's combat snapshot (+ its animation, so the defender's reaction
-- and the attacker's move can both be keyed by ROM animation id).
local function combat_json(base, side)
  local stun_base = STUN_ADDR[side]
  local bar = 0
  if bit and bit.rshift then bar = bit.rshift(rddword(stun_base + 0x6), 24)
  else bar = math.floor(rddword(stun_base + 0x6) / 16777216) end
  return "{" ..
    '"anim":' .. jstr(string.format("%04x", rdword(base + 0x202))) .. "," ..
    '"anim_frame":' .. jnum(rdword(base + 0x21A)) .. "," ..
    '"posture":' .. jnum(rdbyte(base + 0x20E)) .. "," ..
    '"pos_x":' .. jnum(rdwords(base + 0x64)) .. "," ..
    '"vitality":' .. jnum(rdwords(base + COMBAT.vitality)) .. "," ..
    '"life":' .. jnum(rdbyte(base + COMBAT.life)) .. "," ..
    '"dm_vital":' .. jnum(rdwords(base + COMBAT.dm_vital)) .. "," ..
    '"dmg_next":' .. jnum(rdbyte(base + COMBAT.dmg_next)) .. "," ..
    '"stun_next":' .. jnum(rdbyte(base + COMBAT.stun_next)) .. "," ..
    '"freeze":' .. jnum(unwrap_freeze(rdbyte(base + COMBAT.freeze))) .. "," ..
    '"recovery":' .. jnum(rdbyte(base + COMBAT.recovery)) .. "," ..
    '"busy":' .. jnum(rdword(base + COMBAT.busy)) .. "," ..
    '"blocking_id":' .. jnum(rdbyte(base + COMBAT.blocking_id)) .. "," ..
    '"hits_received":' .. jnum(rdword(base + COMBAT.hits_received)) .. "," ..
    '"conn_marker":' .. jnum(rdword(base + COMBAT.conn_marker)) .. "," ..
    '"input_cap":' .. jnum(rdword(base + COMBAT.input_cap)) .. "," ..
    '"att_bonus":' .. jnum(rdword(base + COMBAT.att_bonus)) .. "," ..
    '"stun_bonus":' .. jnum(rdword(base + COMBAT.stun_bonus)) .. "," ..
    '"def_bonus":' .. jnum(rdword(base + COMBAT.def_bonus)) .. "," ..
    '"stun_max":' .. jnum(rdbyte(stun_base)) .. "," ..
    '"stun_timer":' .. jnum(rdbyte(stun_base + 0x2)) .. "," ..
    '"stun_bar":' .. jnum(bar) .. "}"
end

local function frame_record(frame_num, base)
  local boxes = read_boxes(base)
  local parts = {}
  for _, b in ipairs(boxes) do parts[#parts + 1] = box_to_json(b) end
  return "{" ..
    '"f":' .. jnum(frame_num) .. "," ..
    '"pos_x":' .. jnum(rdwords(base + 0x64)) .. "," ..
    '"pos_y":' .. jnum(rdwords(base + 0x68)) .. "," ..
    '"flip":' .. jnum(rdbytes(base + 0x0A)) .. "," ..
    '"posture":' .. jnum(rdbyte(base + 0x20E)) .. "," ..
    '"anim":' .. jstr(string.format("%04x", rdword(base + 0x202))) .. "," ..
    '"anim_frame":' .. jnum(rdword(base + 0x21A)) .. "," ..
    '"boxes":[' .. table.concat(parts, ",") .. "]," ..
    '"c1":' .. combat_json(base, 1) .. "," ..
    '"c2":' .. combat_json(P2_BASE, 2) .. "}"
end

-- ---- recording loop ---------------------------------------------------------
-- AUTO-RECORD: recording starts the moment the script runs and writes one line
-- per frame to OUT_PATH (in the script's own folder, since FBNeo runs a script
-- with its directory as the working dir). Optionally PAUSE_KEY toggles a pause so
-- you can skip menus. The file is flushed periodically and on emulator exit, so
-- you can simply Run -> play the moves -> close, with no key juggling.
local paused = false
local prev_key = false
local frame_num = 0
local fh = io.open(OUT_PATH, "w")

-- Training-mode stand-ins (see the header). A player's life is written only
-- while idle: the ingest measures damage on the connect frame and hitstun until
-- idle, so a refill after that changes nothing it reads. Both the internal
-- vitality word (+0x9C) and the bar byte (+0x9F) are set, as a KO checks the
-- former.
local wbyte, wword = memory.writebyte, memory.writeword
local function player_idle(base)
  return rdbyte(base + COMBAT.freeze) == 0 and (rdword(base + COMBAT.busy) % 256) == 0
end
local function keep_alive()
  wbyte(TIMER_ADDR, 0x63)
  for _, base in ipairs({ PLAYER_BASE, P2_BASE }) do
    if player_idle(base) and rdbyte(base + COMBAT.life) < FULL_LIFE then
      wword(base + COMBAT.vitality, FULL_LIFE)
      wbyte(base + COMBAT.life, FULL_LIFE)
    end
  end
end

-- Dummy driver: feeds P2 directions through joypad.set (the same mechanism the
-- training script uses). "back" = away from P1, from P2's facing byte.
local dummy_mode = 1
local prev_dummy_key = false
local function p1_in_move()
  return (rdword(PLAYER_BASE + COMBAT.busy) % 256) ~= 0 or rdbyte(PLAYER_BASE + COMBAT.freeze) ~= 0
end
local function drive_dummy()
  local mode = DUMMY_MODES[dummy_mode]
  if mode == "stand" then return end
  local back = (rdbyte(P2_FACING) == 1) and "P2 Right" or "P2 Left"
  local threatened = p1_in_move()
      or rdbyte(P2_BASE + COMBAT.blocking_id) ~= 0
      or rdbyte(P2_BASE + COMBAT.freeze) ~= 0
  local pressed = {}
  if mode == "block_always" or ((mode == "block" or mode == "crouch_block") and threatened) then
    pressed[back] = true
  end
  if mode == "crouch_block" then pressed["P2 Down"] = true end
  if mode == "jump" then pressed["P2 Up"] = true end
  joypad.set(pressed)
end

local function on_frame()
  if KEEP_ALIVE then keep_alive() end
  local dk = input.get()[DUMMY_KEY] == true
  if dk and not prev_dummy_key then
    dummy_mode = dummy_mode % #DUMMY_MODES + 1
  end
  prev_dummy_key = dk
  if not emu.registerbefore then drive_dummy() end
  -- optional pause toggle on PAUSE_KEY edge
  local keys = input.get()
  local down = keys[REC_KEY] == true
  if down and not prev_key then
    paused = not paused
  end
  prev_key = down

  if fh and not paused then
    frame_num = frame_num + 1
    fh:write(frame_record(frame_num, PLAYER_BASE), "\n")
    if frame_num % 60 == 0 then fh:flush() end
  end

  if gui and gui.text then
    gui.text(8, 8, (paused and "PAUSED " or "REC ") .. frame_num .. (KEEP_ALIVE and "  [inf time / life]" or "")
             .. "  dummy: " .. DUMMY_MODES[dummy_mode] .. " (" .. DUMMY_KEY .. ")")
  end
end

local function close_file()
  if fh then fh:flush(); fh:close(); fh = nil end
end

-- FBNeo: run after each emulated frame; flush on exit.
emu.registerafter(on_frame)
-- inputs are applied to the frame about to run, so drive the dummy before it
if emu.registerbefore then emu.registerbefore(drive_dummy) end
if emu.registerexit then emu.registerexit(close_file) end

print("PyKuma dumper: RECORDING to " .. OUT_PATH ..
      " (press '" .. REC_KEY .. "' to pause/resume). Play the moves, then close.")
