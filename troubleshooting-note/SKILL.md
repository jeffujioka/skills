---
name: troubleshooting-note
description: "Capture a solved problem as a note in the Obsidian vault's Troubleshooting/ folder"
disable-model-invocation: true
---

# Troubleshooting note

Write what was just solved into the vault, so a future session recalls it instead of re-diagnosing.

## 1. Resolve the vault

State file: `~/.local/state/skills/troubleshooting-note/vault-path` (one line, absolute path). The recall rule in the user's AGENTS.md reads the same file.

- File present: use its path.
- File missing, or the user asked to change the vault: ask the user for the vault path, confirm `<path>/.obsidian/` exists, then `mkdir -p` the state directory and write the path.

Done when you hold a vault path that contains `.obsidian/`.

## 2. Load formatting

Load the `obsidian-markdown` skill. Work through plain file tools; the `obsidian` CLI is not installed on the build servers.

## 3. Check before create

Grep `<vault>/Troubleshooting/` for the error text and the tool name; list inbound `[[wikilinks]]` for each candidate.

- Match: update that note in place. Keep its filename, refresh `Seen with`, extend `Ruled out`.
- No match: create a new note.

## 4. Write

Read `<vault>/Templates/Troubleshooting Note.md` and follow its structure and section order. Stop and tell the user if the template is missing.

- Filename: short, problem-first title (`Brew force-bottle Error and Bottle Relocation (Custom Prefix).md`), flat in `Troubleshooting/`.
- H1: the error text or symptom as it appears on screen.
- Frontmatter: `created` is today's date; `tags` are `subject/vault/troubleshooting` plus `subject/<domain>/<tool>` tags reused from existing notes (grep before inventing one); `related` links notes found in step 3.
- Language: English, unless the user asks for another.
- Core sections come first and in order; extras (a `> [!abstract]` callout, a short `## Background`) go after `Fix`.
- Index and hub notes stay out; the note is the only file written.

## Done

All of these hold:

- The note exists on disk under `<vault>/Troubleshooting/`.
- Frontmatter has no empty placeholder left from the template (`{{...}}`).
- `Seen with` carries a version captured by running the tool's `--version` (or equivalent) in this session.
- The `Verification` command was run in this session, and its real result is quoted.
- Every claim comes from this session's evidence; whatever was not observed is omitted.

Report the note's path to the user.
