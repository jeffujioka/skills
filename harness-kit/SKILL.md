---
name: harness-kit
description: Use when installing, checking or removing harness-kit, the agent environment that logbook, captain-away and hc-handoff need on claude, omp and opencode, or when a skill stops with "agent-env not found".
---

# harness-kit

harness-kit gives every shell command an agent runs the variable `AGENT_HARNESS`, and installs `agent-env`, which prints the harness, the session id and the root session id. logbook, captain-away and hc-handoff read them from `agent-env`.

`<skill dir>` is the absolute path of this skill's folder. The scripts need `bash`; `install.sh` also needs `jq` when claude is found, and `agent-env` needs `sqlite3` on opencode. Check them with `command -v jq sqlite3`. `install.sh` edits `~/.claude/settings.json` through `scripts/claude-settings.sh`, which keeps every other key.

Local, reversible actions (run `plan` or `check`) proceed. Before an action that is destructive, hard to reverse, or visible to others (install, replace, remove), show it and wait for the developer's approval. When blocked, never use a destructive shortcut: no bypassing checks, no discarding files you did not create.

## Artefacts

Install writes these, only for the harnesses found on `PATH`:

| Artefact                                                                                                    | Harness  | What it does                                                                                                                                                                                                                                         |
| ----------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `~/.local/bin/agent-env`                                                                                    | any      | prints `AGENT_HARNESS`, `AGENT_SESSION_ID` and `AGENT_ROOT_SESSION_ID`                                                                                                                                                                               |
| a `SessionStart` entry in `~/.claude/settings.json`, running `~/.claude/hooks/harness-kit-session-start.sh` | claude   | sets `AGENT_HARNESS=claude` for the session's shell commands and names the logbook after compaction and shows a notice that it did                                                                                                                   |
| `~/.omp/agent/extensions/harness-kit.ts`                                                                    | omp      | sets `AGENT_HARNESS=omp` on commands that run `agent-env` or a skills script, adds the logbook reminder to the session after compaction and shows a notice, and asks GitHub Copilot for 1h prompt-cache entries on Claude models in the main session |
| `~/.config/opencode/plugins/harness-kit/index.ts`                                                           | opencode | sets `AGENT_HARNESS=opencode` for the session's shell commands and adds the logbook reminder as a session instruction after compaction                                                                                                               |
| `~/.config/opencode/plugins/harness-kit/tui.ts`                                                             | opencode | shows a toast that the reminder was added                                                                                                                                                                                                            |

Each installed file carries a `harness-kit <version>` marker line. A target without it is foreign: install keeps it unless the developer confirms replacing it.

## Install

1. Run `bash "<skill dir>/scripts/install.sh" plan`. It writes nothing. Show its output whole. Done when the plan is shown.
2. Ask one question: install or not, and, for each file the plan lists as foreign, whether to replace it. Done when the developer answers.
3. On yes, run `bash "<skill dir>/scripts/install.sh" install`, adding `--replace <path>` for each foreign file the developer confirmed, with the path as the plan printed it. On no, run nothing more and write nothing. Done when install exits 0, or the developer said no.
4. Tell the developer to start a new session: the hooks apply only to sessions started after the install. Done when said.

## Check

Run `bash "<skill dir>/scripts/install.sh" check`. It reports each artefact as installed, missing, older, newer or foreign, and exits 1 unless all are current. When it says to repair, follow Install. Install keeps a newer artefact and never downgrades it.

## Remove

1. Run `bash "<skill dir>/scripts/install.sh" check` and show its output: remove deletes the artefacts it reports as installed, older or newer. Done when the output is shown.
2. Ask one question: remove them or not. Done when the developer answers.
3. On yes, run `bash "<skill dir>/scripts/install.sh" remove`. It deletes only the files harness-kit installed and its `SessionStart` entry; foreign files and the other settings stay. On no, run nothing more. Done when remove exits 0, or the developer said no.

## Copilot 1h cache (omp)

The omp extension changes the cache lifetime of the main session on GitHub Copilot Claude models from 5 minutes to 1 hour. omp sends 5-minute entries there because its model catalog marks those models as not supporting the 1h entry; Copilot accepts it.

- A 1h cache write costs 1.6 times a 5-minute write. A read costs the same either way, so a session that pauses 5 to 60 minutes pays less overall.
- Subagents keep 5-minute entries: they rarely pause.
- Opt out for one run with `HARNESS_KIT_COPILOT_CACHE=5m omp`. Opt out for good by exporting it in the shell profile.
- After Copilot answers 400 or 422 to a request that carried a 1h entry, the extension stops sending it for the rest of the session and shows a notice.
- When the plan lists the omp extension, tell the developer about this change in one sentence before asking install or not.
- Details and the measurement: [references/omp.md](references/omp.md).

## Harness notes

- [references/claude.md](references/claude.md): the settings entry, the `SessionStart` hook, `CLAUDE_ENV_FILE` and the reminder after compaction.
- [references/omp.md](references/omp.md): the extension and its compaction route.
- [references/opencode.md](references/opencode.md): the plugin and its compaction event.
