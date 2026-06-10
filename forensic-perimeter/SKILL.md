---
name: forensic-perimeter
description: Add known places to the tracker from Google Maps links (batch). Resolves short/full URLs, extracts name + coordinates, shows preview, then runs tracker.py add-place for each. Use when user wants to add places, register locations, says "add places", "forensic-perimeter", "registrar locais", or pastes multiple Google Maps links.
---

# Forensic Perimeter

Register known places in the tracker from Google Maps links — one or many at once.

## Input

Google Maps links (full or short `maps.app.goo.gl`). Passed inline in args or provided conversationally.

Optional:
- `--radius <N>` — global radius override (default: 150m)
- Per-link radius override via preview table editing

## Workflow

### 1. Collect links

If links are in the args, use them directly. Otherwise ask:
> "Cole os links do Google Maps (um por linha):"

### 2. Resolve each link

Run the resolve script for each URL:

```bash
~/projects/jeffujioka/skills/forensic-perimeter/resolve-places.sh <url1> [url2] ...
```

Output is TSV: `name\tlat,lng`

If a short URL fails to resolve, report the error and continue with the others.

### 3. Show preview table

Present a markdown table:

| # | Name | Coordinates | Radius |
|---|------|-------------|--------|
| 1 | Skatepark Liberty 2 | 52.5377989,13.5954429 | 150 |
| 2 | Bäckerei Müller | 52.5200000,13.4050000 | 150 |

If the user specified `--radius`, use that as the default instead of 150.

Ask: "Confirma? Edite nomes ou radius se necessário."

The user may:
- Confirm as-is
- Edit names (e.g., "rename #1 to skatepark")
- Edit radius (e.g., "#2 radius 200")
- Remove entries (e.g., "remove #1")

### 4. Execute

For each confirmed place, run:

```bash
uv run ~/projects/jeffujioka/tracker/tracker.py add-place "<name>" "<lat,lng>" --radius <N>
```

Report results: added, skipped (duplicate name), or errored.

### 5. Summary

Show final summary:
- N places added
- N skipped (already exist)
- N errors

## Key rules

- Resolve short URLs via `curl -sI` (follows 302 redirect).
- Extract name from `/place/<Name>/` path segment (URL-decoded).
- Extract coordinates from `!3d<lat>!4d<lng>` markers (pin position, not viewport).
- Fallback: `@lat,lng` from URL if `!3d/!4d` not present.
- If name extraction fails, ask the user for the name.
- Communicate in the user's language.
