---
name: obsidian-capture-troubleshooting
description: "Capture a solved problem as a note in the Obsidian vault's Troubleshooting/ folder, so a later session recalls the fix. Use after a problem is solved. Manual-only: call it by name."
disable-model-invocation: true
---

# Obsidian capture troubleshooting

Write what was just solved into the vault, so a future session recalls it instead of re-diagnosing.

Work through all four steps without pausing. Stop only when:

- The user must give the vault path.
- The note template is missing.
- An existing note needs the user's approval before an update (step 3).

Local, reversible actions proceed. Before an action that overwrites an existing note, show it and wait for the user's approval. When blocked, never use a destructive shortcut: no bypassing checks, no discarding files you did not create.

## 1. Resolve the vault

State file: `~/.local/state/skills/obsidian-capture-troubleshooting/vault-path` (one line, absolute path). The recall rule in `~/.claude/CLAUDE.md` reads the same file, so it must keep this path.

- File present and `<path>/.obsidian/` exists: use its path.
- File missing, `<path>/.obsidian/` absent, or the user asked to change the vault: ask the user for the vault path, confirm `<path>/.obsidian/` exists, then `mkdir -p` the state directory and write the path.

Done when you hold a vault path that contains `.obsidian/`.

## 2. Load formatting

Load the `obsidian-markdown` skill. Use file tools only; the `obsidian` CLI may be missing.

Done when the `obsidian-markdown` skill is loaded.

## 3. Check before create

Grep `<vault>/Troubleshooting/` for the error text and the tool name. A note matches when it holds the same error text, or the same tool with the same cause.

- Match: show the user the note and the planned changes, then wait for approval. With several matches, show the closest and ask which to update. After approval, update the note in place: keep its filename, refresh `Seen with`, extend `Ruled out`. If the user declines, stop and report; write nothing.
- No match: create a new note.

Done when you hold either an approved matching note path or the decision to create a new note.

## 4. Write

Read `<vault>/Templates/Troubleshooting Note.md` and follow its structure and section order. Stop and tell the user if the template is missing. Run `mkdir -p <vault>/Troubleshooting` if the folder is missing.

- Filename: short, problem-first title (`Brew force-bottle Error and Bottle Relocation (Custom Prefix).md`), flat in `Troubleshooting/`. If `<vault>/Troubleshooting/<filename>` already exists, treat it as a match: show it and wait for approval, as in step 3.
- H1: the error text or symptom as it appears on screen.
- Frontmatter: `created` is today's date from `date +%F`; `tags` are `subject/vault/troubleshooting` plus `subject/<domain>/<tool>` tags reused from existing notes, such as `subject/rust/cargo` (grep before inventing one); `related` links the other notes the step 3 grep found that did not match, and stays `[]` when there are none; leave `source`, `area` and `project` as the template has them.
- `Seen with`: `<tool> <version> (checked <date>)`, with the date from `date +%F`.
- Language: English, unless the user asks for another.
- Core sections come first and in order; extras (a `> [!abstract]` callout, a short `## Background`) go after `Fix`.
- Write only this note. The user curates index and hub notes (notes that list other notes), so a write there changes shared structure.

Done when the note is on disk and every check in "Done" holds.

## Done

All of these hold:

- The note exists on disk under `<vault>/Troubleshooting/`.
- No `{{...}}` or `<...>` placeholder and no `<!-- -->` template comment is left in the note. An optional section with nothing to say, such as `Ruled out`, is dropped.
- `Seen with` carries a version captured by running the tool's `--version` (or equivalent) in this session. If it cannot run here, write `version not captured` and report why.
- The `Verification` command was run in this session, and its real result is quoted. If it cannot run here, write `Not verified` in the section and report why.
- Every claim comes from this session's evidence; whatever was not observed is omitted.

Report the note's path to the user.
