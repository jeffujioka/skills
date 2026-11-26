# README craft

Read this in step 2 (directions) and step 5 (build).

## Page order

1. Hero banner: image, animated SVG preferred.
2. One-line value statement: what the reader gets, not how it works.
3. Badges: only ones the repo backs (license, version from the manifest, platforms). Static shields.io badges.
4. Pitch: 2-3 short sentences. Second person.
5. Demo: GIF or animated SVG, right under the pitch.
6. Features: 3-6 blocks. Heading names the outcome. One screenshot or illustration each.
7. Name story: only when the repo or the user's notes explain the name. Puns allowed there.
8. Install: the main path in at most 3 lines. Link to `docs/` for the rest.
9. Docs index: one link per moved topic.
10. License line.

## Copy rules

- Open with the benefit. Put mechanism second.
- Use short sentences and concrete verbs.
- Take every number, platform, version and feature from the repo. Cite its source in the plan.
- Write no testimonial, user count, star count, benchmark, award or "trusted by" line unless a repo file states it.
- Keep the project's own vocabulary. The target repo's `GLOSSARY.md` (if any) lists words to avoid.
- Keep known limits in the docs. Never hide them behind a claim that contradicts them.

## Looks to avoid

Name these in each direction's brief so the three differ from the default:

- Purple-to-blue gradient on white.
- Inter, Roboto, Arial or the system font as the only type.
- A wall of emoji bullets.
- Stock 3D blobs and generic laptop mockups.
- Eight centered badges in a row.
- Words like "supercharge", "blazing fast", "seamless", "revolutionary".

## What GitHub renders

- Allowed HTML: `<p align>`, `<div align>`, `<img width>`, `<picture>`, `<source>`, `<a>`, `<details>`, `<summary>`, `<kbd>`, `<br>`, tables.
- Stripped: `<script>`, `<style>`, `<iframe>`, inline CSS. Color and type come from images only.
- Use relative image paths.
- Dark and light: either give the banner its own background, or use `<picture>` with `<source media="(prefers-color-scheme: dark)" srcset="...">`.
- Give every image alt text.

## Moving technical content to docs

- Technical content: install details, configuration, flags, architecture, build, release, troubleshooting.
- Destination: `docs/<section>/<topic>.md`. Reuse the repo's `docs/` subfolders. With none, use `guide/`, `development/`, `troubleshooting/`.
- Move text word for word. Add an H1 and a `<- README` link at the top of each new file.
- Add `docs/README.md` as an index when `docs/` gains two or more files.
- Search the repo for references to the moved sections: `grep -rn "README" --include="*.md" .`. Fix Markdown references. List references in source code in the report and edit none.
- Leave CHANGELOG.md alone: a README rebuild changes no behavior, unless the repo's own rules say otherwise.
