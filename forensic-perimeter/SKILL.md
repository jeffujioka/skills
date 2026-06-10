---
name: forensic-perimeter
description: Batch-register known places in the tracker from Google Maps links. Resolves short/full URLs, extracts name + coordinates, shows preview table, then runs tracker.py add-place for each. Use when user wants to add places, register locations, says "add places", "forensic-perimeter", "registrar locais", or pastes Google Maps links.
---

# Forensic Perimeter

Batch-register known places in the tracker from Google Maps links.

## Input

One entry per line. Each line contains a Google Maps URL (required) plus optional name and radius, in any order.

```
Kaufpark Eich https://maps.app.goo.gl/xyz 300m
https://www.google.com/maps/place/Skatepark+Liberty+2/... Kaufpark Eich
https://maps.app.goo.gl/abc
https://www.google.com/maps/place/Bäckerei+Müller/... 200m
```

Parsing rules per line:
- **URL**: token starting with `http`
- **Radius**: token matching `\d+m` (e.g., `300m`)
- **Name**: all remaining tokens joined with spaces

Global option: `--radius <N>` sets the default radius for all entries.

**Radius precedence** (highest wins): inline per-line > `--radius` global > 150m.
**Name precedence** (highest wins): inline per-line > extracted from URL path (`/place/<Name>/`).

Entries are passed inline in args or provided conversationally. If no entries in args, ask:
> "Cole os links do Google Maps (um por linha):"

## Workflow

### 1. Parse entries

Split input into lines. For each line, extract URL, optional name, and optional radius using the parsing rules above.

### 2. Resolve URLs

For each URL, run:

```bash
~/projects/jeffujioka/skills/forensic-perimeter/resolve-places.sh <url>
```

Output: TSV `name\tlat,lng`. Use the script output only for coordinates and as fallback name.

If a URL fails to resolve, mark it as `ERROR` in the preview table — do not halt.

### 3. Preview table

| # | Name | Coordinates | Radius | Notes |
|---|------|-------------|--------|-------|
| 1 | Kaufpark Eich | 52.5366048,13.5732627 | 300 | |
| 2 | Skatepark Liberty 2 | 52.5377989,13.5954429 | 150 | |
| 3 | ??? | — | 150 | ERROR: could not resolve |

Rows with `???` as name require user input before proceeding.

Ask: "Confirma? Edite nomes ou radius se necessário."

The user may:
- Confirm as-is
- Edit names (e.g., "rename #2 to skatepark")
- Edit radius (e.g., "#1 radius 200")
- Remove entries (e.g., "remove #3")

### 4. Execute

For each confirmed entry (no `???`, no `ERROR`), run:

```bash
uv run ~/projects/jeffujioka/tracker/tracker.py add-place "<name>" "<lat,lng>" --radius <N>
```

### 5. Summary

```
Added: N | Skipped (duplicate): N | Errors: N
```

## Key rules

- Short URLs (`maps.app.goo.gl`): resolve via `curl -sI` (302 redirect).
- Coordinates: `!3d<lat>!4d<lng>` from URL (pin position). Fallback: `@lat,lng`.
- Name from URL: `/place/<Name>/` path segment, URL-decoded.
- Communicate in the user's language.
