# logbook on claude

- claude compacts automatically when the context nears its window, and on the user's `/compact`. The logbook never triggers it.
- After a compaction claude runs the `SessionStart` hook again with source `compact`. harness-kit's hook then adds the reminder `agent-env compact-reminder` prints, a line starting `Context was compacted. Read`, to the context, only when the logbook folder holds `progress.md`.
- A claude subagent shares its parent's session id, so it gets the parent's logbook folder.
