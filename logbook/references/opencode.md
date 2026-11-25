# logbook on opencode

- opencode compacts on its own when the free context falls to `compaction.buffer` in `~/.config/opencode/opencode.jsonc`, and on the user's `/compact`. The logbook never triggers it.
- After a compaction harness-kit's opencode plugin adds the reminder `agent-env compact-reminder` prints, a line starting `Context was compacted. Read`, to the session, only when the logbook folder holds `progress.md`.

## Older logbooks

- Logbooks under `~/.local/state/opencode/projects/` stay where they are.
- `scripts/path.sh` names the newest of this project on stderr.

<details><summary>Old patterns</summary>

The logbook no longer ships its `compact.sh` or `compaction-status.sh` script. A command that calls them, such as a `compact.md` command under `~/.config/opencode/commands/`, no longer works. Use opencode's own `/compact` or its automatic compaction instead.

</details>
