---
name: logbook
description: "Use when the user asks to compact or compress the session, when a long or multi-step session needs its progress, decisions and next steps kept outside the context window, when the context was just compacted, or when another skill requires a logbook. Not for Obsidian notes, AGENTS.md or tool memory."
---

# logbook

State lives on disk, so a compaction can lose conversation detail without losing the work. Opencode auto-compacts at the `compaction.buffer` set in `~/.config/opencode/opencode.jsonc` (250k on 1M-context models); this skill keeps the files current so that moment is safe.

## Folder

```bash
LOGBOOK=$(bash scripts/path.sh)
```

The script creates the folder and prints its path. Script paths are relative to this skill's directory.

| File | Content | Written by |
|---|---|---|
| `progress.md` | `## Report` (empty until the end), `## Done`, `## In progress`, `## Next` | parent, rewritten whole |
| `decisions.md` | one line each: time, decision, why, alternative rejected | anyone, append |
| `needs-you.md` | skipped or blocked action, why, the exact command or step for the user | anyone, append |

## Cadence

Update `progress.md` after each finished task, plan step or subagent return. Append to `decisions.md` at the moment of deciding. The agent that finishes a step updates the files before it starts the next one.

## Compact on request

1. Update all three files.
2. Request compaction: `bash scripts/compact.sh`. Compaction runs immediately and aborts the in-flight shell call with "Tool execution interrupted: shell". That interruption means it worked. Do not retry, and do not report the compaction as unconfirmed.
3. In the next turn, confirm it: `bash scripts/compaction-status.sh`. Status `completed` means done.
4. Read the three files before any other action, then continue from `## Next`.

## Resume

A context that opens with a summary, an interrupted `compact` call, or a user saying the session was compacted or resumed: read the three files first. When they disagree with the summary, the files win.

## Subagents

Give each subagent the `$LOGBOOK` path. They append to `decisions.md` and `needs-you.md`; only the parent rewrites `progress.md`.
