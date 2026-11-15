# claude reference (claude 2.1.325)

Verified by the skills repo's `tests/harness-kit/test_e2e_install.py` and `tests/harness-kit/test_e2e_reminder.py`, which run `claude -p` in a temporary HOME, so nothing touches the real `~/.claude`.

## Settings entry

Install adds one entry to `~/.claude/settings.json` with `jq` and keeps every other key:

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "bash \"$HOME/.claude/hooks/harness-kit-session-start.sh\""}]}]}}
```

- The command text is the entry's fixed id: install adds the entry only when no `SessionStart` hook runs that command, and remove drops only that command, then any list or `hooks` object it leaves empty.
- When `~/.claude/settings.json` does not exist, install creates it holding only this entry.

## SessionStart hook

`~/.claude/hooks/harness-kit-session-start.sh` carries the marker line `# harness-kit <version>`. claude runs it at session start with a JSON payload on stdin; the hook reads the payload's `source`, `cwd` and `session_id`.

## `CLAUDE_ENV_FILE`

- claude gives `SessionStart` hooks the variable `CLAUDE_ENV_FILE`, a file it sources before each shell command of the session.
- The hook appends `export AGENT_HARNESS=claude` to it once. The export overrides an `AGENT_HARNESS` inherited from an outer harness, such as omp.
- Without `CLAUDE_ENV_FILE` the hook exits 0 and writes nothing.

## After compaction

claude runs the `SessionStart` hook again with `source: "compact"`. The hook runs `agent-env compact-reminder` in the payload's `cwd` and returns its output as `hookSpecificOutput.additionalContext`, which only the model sees. The hook adds a top-level `systemMessage`, `harness-kit: logbook reminder sent to the model (<logbook folder>)`, which claude shows to the user as a warning line; per the hooks docs it is "shown to the user" and is not documented as part of the model's context. The session jsonl records it as a `hook_additional_context` attachment after the `compact_boundary` entry.

## Session-only threshold

- `CLAUDE_CODE_AUTO_COMPACT_WINDOW` has a floor of 100000: `50000` is read as 100k, whose threshold is about 67k tokens after the 33k summary buffer.
- Set `CLAUDE_CODE_AUTO_COMPACT_WINDOW=100000` and `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=30` in the environment. A context of about 48k tokens then compacts.
- claude keeps at most 30000 characters of bash output inline and saves the rest to a file. `--settings '{"bashOutputMaxChars": 128000}'` raises it to the 128000 ceiling; a longer output is still saved to a file. So `head -n 2000` of the 3000-line filler (122000 characters) fills the context, and `cat` of all of it does not.

## Check by hand

In a new claude session started after the install, ask it to run `agent-env`. It prints `AGENT_HARNESS=claude` and the session id twice, as `AGENT_SESSION_ID` and `AGENT_ROOT_SESSION_ID`.

For the reminder, write `progress.md` into the folder `bash ~/.agents/skills/logbook/scripts/path.sh` prints, let a compaction run, for example with the threshold above, then ask the agent to quote the line of its context that starts with `Context was compacted.`. It quotes the reminder naming that folder.
