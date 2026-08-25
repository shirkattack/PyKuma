# Baston ESN3S — Akuma (Gouki) frame data, "revised" tables

Vendored HTML of the three frame-data tables for Gouki (iChar=14) from
https://baston.esn3s.com/index.php?id=14, fetched 2026-08-25. The site renders
each table through a jQuery POST, so these were saved with:

    curl -sL "https://baston.esn3s.com/index.php" \
      --data "page=ajax_loadData.php&iChar=14&type=fd&id=<normals|specials|supers>&div=content_char&version=revised"

These are the COMMUNITY tier (damage / stun / frame advantage / Baston's own
startup-active-recovery). They are converted into
`data/characters/akuma/sf3_authentic_frame_data.yaml` by
`tools/framedata/baston_to_community.py`; box geometry and move timing in the
engine come from the ROM dump (`../gouki_framedata.json`), never from here.

Damage on Baston is on the game's per-hit scale (st. Fierce = 24). The yaml keeps
Akuma's 1050 vitality and converts with a single anchor, Fierce 24 -> 180
(x7.5); see the tool for the rationale and the provisional flag.
