#!/usr/bin/env python3
"""
Sprite asset auditor / contact-sheet generator.

Renders labeled filmstrips for sprite sets and writes markdown catalogs. Use it
after (re-)extracting sprites to spot mislabeled frames (a pose that doesn't
belong in a sequence), missing art, and empty/transparent frames.

Sources:
    --character akuma          a character's registered animations (default)
    --folder <path>            one folder of frame_NNN.png / numbered / gif files
    --range <dir> <lo> <hi>    a numbered range from a flat sprite dir
                               (add --segment to split on numbering gaps)
    --all-effects              every category under assets/vfx/ingame_effects/

Run headless:
    SDL_VIDEODRIVER=dummy uv run python scripts/audit_animations.py
    SDL_VIDEODRIVER=dummy uv run python scripts/audit_animations.py --all-effects

Outputs:
    docs/animation_audit/<animation>.png + docs/ANIMATIONS.md   (--character akuma)
    docs/asset_catalog/<set>/*.png + docs/asset_catalog/<SET>.md (other sources)
"""

import argparse
import glob
import os
import re
import statistics
import pygame

OUT_DIR = os.path.join("docs", "animation_audit")
MD_PATH = os.path.join("docs", "ANIMATIONS.md")
CATALOG_DIR = os.path.join("docs", "asset_catalog")
EFFECTS_DIR = os.path.join("assets", "vfx", "ingame_effects")

# Filmstrip layout
CELL_W = 110
CELL_H = 150
BASELINE_PAD = 22          # space below baseline for the height label
MAX_COLS = 12
MAX_CHAR_H = CELL_H - 40    # scale character down to fit a cell
BG = (38, 40, 52)
CELL_BG = (48, 50, 66)
FLAG_BG = (96, 42, 42)      # cell tint for a flagged (review) frame
MISSING_BG = (110, 70, 30)
BASELINE_COL = (0, 180, 0)


# --------------------------------------------------------------------------
# Generic helpers (source-agnostic)
# --------------------------------------------------------------------------

def init_pygame():
    """Init a headless display (needed for convert_alpha)."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((640, 480))


def natural_key(s):
    """Natural sort key so frame_2 < frame_10 and 2.gif < 10.gif."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def font(size):
    return pygame.font.Font(None, size)


def load_cropped(path):
    """Return (cropped_surface, opaque_height) or (None, 0) if missing/undecodable/empty."""
    if not os.path.exists(path):
        return None, 0
    try:
        img = pygame.image.load(path).convert_alpha()
    except pygame.error:
        return None, 0
    bb = img.get_bounding_rect()
    if bb.height == 0:
        return None, 0
    return img.subsurface(bb).copy(), bb.height


def flag_heights(heights):
    """Indices whose opaque height is a strong outlier vs the median (soft hint)."""
    nz = [h for h in heights if h > 0]
    if len(nz) < 3:
        return set()
    med = statistics.median(nz)
    flagged = set()
    for i, h in enumerate(heights):
        if h > 0 and (h > med * 1.5 or h < med * 0.45):
            flagged.add(i)
    return flagged


def compose_strip(name, frames):
    """frames: list of (label, cropped_surface_or_None, height, flagged_bool)."""
    n = max(1, len(frames))
    cols = min(MAX_COLS, n)
    rows = (n + cols - 1) // cols
    header_h = 30
    W = cols * CELL_W
    H = header_h + rows * CELL_H
    surf = pygame.Surface((W, H))
    surf.fill(BG)
    surf.blit(font(26).render(name, True, (255, 235, 120)), (8, 5))

    f_lbl, f_h = font(18), font(16)
    for i, (lbl, char, h, flagged) in enumerate(frames):
        r, c = divmod(i, cols)
        cx = c * CELL_W
        cy = header_h + r * CELL_H
        cell = pygame.Rect(cx + 2, cy + 2, CELL_W - 4, CELL_H - 4)
        if char is None:
            surf.fill(MISSING_BG, cell)
        else:
            surf.fill(FLAG_BG if flagged else CELL_BG, cell)
        baseline = cy + CELL_H - BASELINE_PAD
        pygame.draw.line(surf, BASELINE_COL, (cx + 6, baseline), (cx + CELL_W - 6, baseline), 1)
        surf.blit(f_lbl.render(lbl, True, (235, 235, 235)), (cx + 6, cy + 6))
        if char is None:
            surf.blit(f_h.render("MISSING", True, (255, 200, 160)), (cx + 6, baseline - 16))
        else:
            sc = min(1.0, MAX_CHAR_H / char.get_height())
            if sc < 1.0:
                char = pygame.transform.scale(
                    char, (max(1, int(char.get_width() * sc)), int(char.get_height() * sc)))
            cr = char.get_rect()
            cr.centerx = cx + CELL_W // 2
            cr.bottom = baseline
            surf.blit(char, cr)
            tint = (255, 180, 120) if flagged else (175, 175, 175)
            surf.blit(f_h.render(f"h{h}", True, tint), (cx + 6, baseline + 3))
    return surf


def render_filmstrip(name, items, out_path):
    """Render one filmstrip from items=[(label, path)]. Returns a stats dict.

    Single source of truth for strip rendering across all sources.
    """
    cells, heights, labels = [], [], []
    for label, path in items:
        char, h = load_cropped(path)
        cells.append([label, char, h])
        heights.append(h)
        labels.append(label)
    flagged = flag_heights(heights)
    missing = [i for i, h in enumerate(heights) if h == 0]
    for i, cell in enumerate(cells):
        cell.append(i in flagged)
    if cells:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        pygame.image.save(compose_strip(name, [tuple(c) for c in cells]), out_path)
    return {"name": name, "labels": labels, "heights": heights,
            "flagged": flagged, "missing": missing, "count": len(items),
            "png": out_path}


def segment_by_gaps(numbers, max_gap=1):
    """Group sorted ints into contiguous runs: [(lo, hi), ...]."""
    nums = sorted(numbers)
    if not nums:
        return []
    runs, lo, prev = [], nums[0], nums[0]
    for n in nums[1:]:
        if n - prev > max_gap:
            runs.append((lo, prev))
            lo = n
        prev = n
    runs.append((lo, prev))
    return runs


def numbered_pngs(directory):
    """Sorted list of integer stems for `<int>.png` files in a directory."""
    nums = []
    for p in glob.glob(os.path.join(directory, "*.png")):
        stem = os.path.splitext(os.path.basename(p))[0]
        if stem.isdigit():
            nums.append(int(stem))
    return sorted(nums)


def iter_frame_files(folder):
    """[(label, path)] for a folder, label = file stem, natural-sorted.

    Covers frame_NNN.png (folder animations), numbered, and gif (select art).
    Non-image files like description.txt are excluded by the glob.
    """
    files = glob.glob(os.path.join(folder, "*.png")) + glob.glob(os.path.join(folder, "*.gif"))
    files = sorted(files, key=lambda p: natural_key(os.path.basename(p)))
    return [(os.path.splitext(os.path.basename(p))[0], p) for p in files]


def read_description(folder):
    """Parse a folder's description.txt → short label, or '' if absent."""
    path = os.path.join(folder, "description.txt")
    if not os.path.exists(path):
        return ""
    move, desc = "", ""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("Move:"):
                move = line.split(":", 1)[1].strip()
            elif line and not line.startswith(("=", "-", "Technical", "Animation", "Files:", "Move")):
                desc = line
                break
    return f"{desc}" if desc else move


def status_of(stats, is_folder_missing_all=False):
    """Compute a status string + notes list from a render_filmstrip stats dict."""
    notes = []
    status = "OK"
    if is_folder_missing_all:
        return "❌ MISSING ART", ["source has no frames"]
    if stats["missing"]:
        status = "⚠️ missing frames"
        notes.append(f"{len(stats['missing'])} absent: " +
                     ", ".join(stats["labels"][i] for i in stats["missing"]))
    if stats["flagged"]:
        if status == "OK":
            status = "⚠️ review"
        notes.append("size-outlier frame(s): " +
                     ", ".join(f"{stats['labels'][i]} (h{stats['heights'][i]})"
                               for i in sorted(stats["flagged"])))
    return status, notes


def write_index(md_path, title, intro, entries):
    """Generic catalog markdown: legend, attention summary, one section per strip."""
    rel = os.path.dirname(md_path)
    md = [f"# {title}", "",
          "_Auto-generated by `scripts/audit_animations.py`._", "",
          intro, "",
          "Legend: a **red** cell = a size-outlier frame to review; an orange "
          "**MISSING** cell = the file/folder had no usable art.", ""]
    bad = [e for e in entries if e["status"] != "OK"]
    md.append("## Summary")
    md.append("")
    md.append(f"- **{len(entries)}** entries, **{len(bad)}** need attention")
    if bad:
        md += ["", "| entry | status |", "|---|---|"]
        md += [f"| `{e['name']}` | {e['status']} |" for e in bad]
    md.append("")
    for e in entries:
        md.append(f"### `{e['name']}`  —  {e['status']}")
        md.append("")
        if e.get("desc"):
            md.append(f"- {e['desc']}")
        md.append(f"- frames: {e['count']}")
        for note in e.get("notes", []):
            md.append(f"- ⚠️ {note}")
        png_rel = os.path.relpath(e["png"], rel)
        md.append("")
        md.append(f"![{e['name']}]({png_rel})")
        md.append("")
    os.makedirs(rel, exist_ok=True)
    with open(md_path, "w") as f:
        f.write("\n".join(md))


# --------------------------------------------------------------------------
# Source: character (back-compat — keeps docs/ANIMATIONS.md byte-stable)
# --------------------------------------------------------------------------

CHARACTERS = {}  # tool-local lookup, NOT a game registry; populated lazily


def _load_character(name):
    """Instantiate a character with its animation_controller populated.

    The game may boot a character on the folder-based 'simple sprite' path
    (use_sf3_sprites=True), which skips building the animation_controller. The
    audit always wants the registered animation definitions, so force the
    controller to exist here.
    """
    from street_fighter_3rd.data.constants import STAGE_FLOOR
    if name == "akuma":
        from street_fighter_3rd.characters.akuma import Akuma
        char = Akuma(200, STAGE_FLOOR, 1)
    else:
        raise SystemExit(f"Unknown character '{name}' (known: akuma)")

    if not getattr(char, "animation_controller", None):
        from street_fighter_3rd.systems.animation import SpriteManager, AnimationController
        char.use_sf3_sprites = False
        char.sprite_manager = SpriteManager("assets/sprites/akuma/sprite_sheets")
        char.animation_controller = AnimationController(char.sprite_manager)
        char._setup_animations()
    return char


def unique_frames_in_order(anim):
    """Unique frames in playback order: list of (key, loader_info)."""
    from street_fighter_3rd.systems.animation import Animation
    seen, out = set(), []
    for f in anim.frames:
        if isinstance(anim, Animation):
            key = f.sprite_number
            info = ("numbered", f.sprite_number)
        else:
            key = (f.folder_path, f.frame_index)
            info = ("folder", f.folder_path, f.frame_index)
        if key not in seen:
            seen.add(key)
            out.append((key, info))
    return out


def path_for(info):
    if info[0] == "numbered":
        return os.path.join("assets/sprites/akuma/sprite_sheets", f"{info[1]}.png")
    return os.path.join(info[1], f"frame_{info[2]:03d}.png")


def label_for(info):
    return str(info[1]) if info[0] == "numbered" else f"f{info[2]:03d}"


def cmd_character(name, out_dir, md_path):
    from street_fighter_3rd.systems.animation import Animation
    character = _load_character(name)
    anims = character.animation_controller.animations

    md = []
    md.append("# Akuma Animation Reference")
    md.append("")
    md.append("_Auto-generated by `scripts/audit_animations.py`. "
              "Regenerate after re-extracting sprites:_")
    md.append("")
    md.append("```")
    md.append("SDL_VIDEODRIVER=dummy uv run python scripts/audit_animations.py")
    md.append("```")
    md.append("")
    md.append("Filmstrips (one row per animation, frames in playback order) are in "
              "[`animation_audit/`](animation_audit/). A red cell = a frame whose size is a strong "
              "outlier vs the rest of the sequence (likely mislabeled — review it). "
              "An orange `MISSING` cell = the source file/folder has no art.")
    md.append("")

    numbered, folder = [], []
    total_missing = total_flagged = 0

    for anim_name in sorted(anims):
        anim = anims[anim_name]
        is_numbered = isinstance(anim, Animation)
        uniq = unique_frames_in_order(anim)
        items = [(label_for(info), path_for(info)) for _, info in uniq]

        stats = render_filmstrip(anim_name, items, os.path.join(out_dir, f"{anim_name}.png"))
        labels, heights = stats["labels"], stats["heights"]
        flagged, missing = stats["flagged"], stats["missing"]
        total_missing += len(missing)
        total_flagged += len(flagged)

        seq = [str(f.sprite_number) if is_numbered else f"f{f.frame_index:03d}" for f in anim.frames]
        src = ("assets/sprites/akuma/sprite_sheets"
               if is_numbered else anim.frames[0].folder_path if anim.frames else "?")

        status = "OK"
        notes = []
        if not is_numbered and len(missing) == len(uniq) and uniq:
            status = "❌ MISSING ART"
            notes.append(f"source folder `{src}` has no frames")
        elif missing:
            status = "⚠️ missing frames"
            notes.append(f"{len(missing)} frame(s) absent: " +
                         ", ".join(labels[i] for i in missing))
        if flagged:
            if status == "OK":
                status = "⚠️ review"
            notes.append("size-outlier frame(s) to review: " +
                         ", ".join(f"{labels[i]} (h{heights[i]})" for i in sorted(flagged)))

        entry = {
            "name": anim_name, "kind": "numbered" if is_numbered else "folder",
            "loop": anim.loop, "src": src, "total": len(anim.frames), "unique": len(uniq),
            "seq": seq, "status": status, "notes": notes, "png": f"animation_audit/{anim_name}.png",
        }
        (numbered if is_numbered else folder).append(entry)

    md.append("## Summary")
    md.append("")
    md.append(f"- **{len(numbered)+len(folder)}** animations "
              f"({len(numbered)} numbered, {len(folder)} folder-based)")
    bad = [e for e in numbered + folder if e["status"] != "OK"]
    md.append(f"- **{len(bad)}** need attention "
              f"({total_missing} missing/empty frame(s), {total_flagged} size-outlier frame(s))")
    if bad:
        md.append("")
        md.append("| animation | status |")
        md.append("|---|---|")
        for e in sorted(bad, key=lambda e: e["name"]):
            md.append(f"| `{e['name']}` | {e['status']} |")
    md.append("")

    def section(title, entries):
        md.append(f"## {title}")
        md.append("")
        for e in entries:
            md.append(f"### `{e['name']}`  —  {e['status']}")
            md.append("")
            md.append(f"- loop: `{e['loop']}` · frames: {e['total']} "
                      f"(unique: {e['unique']}) · source: `{e['src']}`")
            md.append(f"- sequence: `{', '.join(e['seq'])}`")
            for note in e["notes"]:
                md.append(f"- ⚠️ {note}")
            md.append("")
            md.append(f"![{e['name']}]({e['png']})")
            md.append("")

    section("Numbered animations (sprite_sheets)", numbered)
    section("Folder animations (tools/sprite_extraction/akuma_animations)", folder)

    with open(md_path, "w") as f:
        f.write("\n".join(md))

    print(f"Wrote {md_path}")
    print(f"Wrote {len(numbered)+len(folder)} filmstrips to {out_dir}/")
    print(f"Needs attention: {len(bad)} animations "
          f"({total_missing} missing/empty frames, {total_flagged} size outliers)")
    for e in sorted(bad, key=lambda e: e["name"]):
        print(f"  {e['status']:16} {e['name']}")


# --------------------------------------------------------------------------
# Source: arbitrary folder / numbered range / effects library
# --------------------------------------------------------------------------

def cmd_folder(folders, catalog):
    folders = [f.rstrip("/") for f in folders]
    if not catalog:
        if len(folders) > 1:
            raise SystemExit("--catalog NAME is required when cataloging multiple folders")
        catalog = os.path.basename(folders[0])
    out_dir = os.path.join(CATALOG_DIR, catalog)
    entries = []
    for folder in folders:
        name = os.path.basename(folder)
        items = iter_frame_files(folder)
        if not items:
            print(f"  skip (no images): {folder}")
            continue
        stats = render_filmstrip(name, items, os.path.join(out_dir, f"{name}.png"))
        status, notes = status_of(stats)
        entries.append({"name": name, "count": stats["count"], "status": status,
                        "notes": notes, "png": stats["png"], "desc": read_description(folder)})
    src = folders[0] if len(folders) == 1 else f"{len(folders)} folders"
    write_index(os.path.join(CATALOG_DIR, f"{catalog.upper()}.md"),
                f"{catalog} catalog", f"Source: `{src}`", entries)
    print(f"Cataloged {len(entries)} folders -> {out_dir}/")


def cmd_range(directory, lo, hi, segment, catalog):
    directory = directory.rstrip("/")
    catalog = catalog or os.path.basename(directory)
    out_dir = os.path.join(CATALOG_DIR, catalog)
    present = [n for n in numbered_pngs(directory) if lo <= n <= hi]
    if not present:
        raise SystemExit(f"No numbered PNGs in {directory} within [{lo},{hi}]")

    runs = segment_by_gaps(present) if segment else [(lo, hi)]
    entries = []
    for (rlo, rhi) in runs:
        block = [n for n in present if rlo <= n <= rhi]
        name = f"{catalog}_{rlo}-{rhi}"
        items = [(str(n), os.path.join(directory, f"{n}.png")) for n in block]
        stats = render_filmstrip(name, items, os.path.join(out_dir, f"{name}.png"))
        status, notes = status_of(stats)
        entries.append({"name": name, "count": stats["count"], "status": status,
                        "notes": notes, "png": stats["png"]})
    write_index(os.path.join(CATALOG_DIR, f"{catalog.upper()}.md"),
                f"{catalog} catalog",
                f"Source: `{directory}` range {lo}-{hi} "
                f"({len(present)} present frames, {len(runs)} segment(s)). "
                "Each segment (split on numbering gaps) is a candidate animation to name.",
                entries)
    print(f"Cataloged {catalog}: {len(present)} frames in {len(runs)} segments -> {out_dir}/")


def cmd_effects():
    if not os.path.isdir(EFFECTS_DIR):
        raise SystemExit(f"Effects dir not found: {EFFECTS_DIR}")
    out_dir = os.path.join(CATALOG_DIR, "effects")
    entries = []
    for cat in sorted(os.listdir(EFFECTS_DIR)):
        cat_dir = os.path.join(EFFECTS_DIR, cat)
        if not os.path.isdir(cat_dir):
            continue
        present = numbered_pngs(cat_dir)
        if not present:
            continue
        for (rlo, rhi) in segment_by_gaps(present):
            block = [n for n in present if rlo <= n <= rhi]
            name = f"{cat}_{rlo}-{rhi}"
            items = [(str(n), os.path.join(cat_dir, f"{n}.png")) for n in block]
            stats = render_filmstrip(name, items, os.path.join(out_dir, f"{name}.png"))
            status, notes = status_of(stats)
            entries.append({"name": name, "count": stats["count"], "status": status,
                            "notes": notes, "png": stats["png"]})
    write_index(os.path.join(CATALOG_DIR, "EFFECTS.md"),
                "In-game effects catalog",
                f"Source: `{EFFECTS_DIR}`. Each category is split into sequences "
                "on numbering gaps — identify which runs are light/medium/heavy/special "
                "hit sparks, block sparks, fireballs, super-art effects, etc.",
                entries)
    print(f"Cataloged effects: {len(entries)} sequences -> {out_dir}/")


def main():
    ap = argparse.ArgumentParser(description="Sprite asset auditor / contact-sheet generator")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--character", metavar="NAME", help="audit a character's registered animations")
    g.add_argument("--folder", nargs="+", metavar="PATH", help="catalog one or more folders of sprites")
    g.add_argument("--range", nargs=3, metavar=("DIR", "LO", "HI"),
                   help="catalog a numbered range from a flat sprite dir")
    g.add_argument("--all-effects", action="store_true",
                   help="catalog every category under assets/vfx/ingame_effects/")
    ap.add_argument("--segment", action="store_true", help="(with --range) split on numbering gaps")
    ap.add_argument("--catalog", metavar="NAME", help="catalog name / output subdir")
    ap.add_argument("--out", metavar="DIR", help="(--character) filmstrip output dir")
    ap.add_argument("--md", metavar="PATH", help="(--character) markdown output path")
    args = ap.parse_args()

    init_pygame()

    if args.folder:
        cmd_folder(args.folder, args.catalog)
    elif args.range:
        d, lo, hi = args.range
        cmd_range(d, int(lo), int(hi), args.segment, args.catalog)
    elif args.all_effects:
        cmd_effects()
    else:
        # default + --character akuma: byte-stable existing behavior
        cmd_character(args.character or "akuma", args.out or OUT_DIR, args.md or MD_PATH)


if __name__ == "__main__":
    main()
