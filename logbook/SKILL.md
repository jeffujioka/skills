---
name: logbook
description: "Use when a long or multi-step session needs its progress, decisions and next steps kept outside the context window, when the context was just compacted, or when another skill requires a logbook. Not for Obsidian notes, AGENTS.md or tool memory."
---

# logbook

Per harness: [claude](references/claude.md), [omp](references/omp.md), [opencode](references/opencode.md).

## Folder

```bash
LOGBOOK=$(bash "<skill dir>/scripts/path.sh")
```

- `<skill dir>` is the absolute path of this skill's folder.
- Its `/skills/logbook/scripts/` part makes omp treat the command as a skills script.
- Run the command from the project folder. The logbook is keyed by that folder.

The script:

- Creates the folder and prints its path.
- Needs harness-kit's `agent-env`, on PATH or at `~/.local/bin/agent-env`. `scripts/require-agent-env.sh` finds it, for this script and for captain-away's `cost.sh`.
- May name an older logbook of this project on stderr.

On a non-zero exit:

- Show its stderr to the user word for word.
- Create no logbook anywhere else. A second folder splits the session's state.

| File           | Content                                                                   | Written by              |
| -------------- | ------------------------------------------------------------------------- | ----------------------- |
| `progress.md`  | `## Report` (empty until the end), `## Done`, `## In progress`, `## Next` | parent, rewritten whole |
| `decisions.md` | one line each: time, decision, why, alternative rejected                  | anyone, append          |
| `needs-you.md` | skipped or blocked action, why, the exact command or step for the user    | anyone, append          |

## Cadence

Update `progress.md` after each finished task, plan step or subagent return. Append to `decisions.md` at the moment of deciding. The agent that finishes a step updates the files before it starts the next one.

## Resume

A context that opens with a summary, the line "Context was compacted. Read …", or a user saying the session was compacted or resumed: read the three files first, then continue from `## Next`. When they disagree with the summary, the files win.

## Compaction requests

The logbook never compacts. Asked to compact: bring `progress.md` up to date (or offer to, when the folder is not set up), then tell the user to run the harness's own `/compact`. Per harness detail is in the references above.

## Subagents

Give each subagent the `$LOGBOOK` path. They append to `decisions.md` and `needs-you.md`; only the parent rewrites `progress.md`.
