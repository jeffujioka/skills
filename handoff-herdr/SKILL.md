---
name: handoff-herdr
description: "Use when handing off the current conversation to a fresh session in a new Herdr tab, pane, or workspace. Triggers on: handoff in herdr, handoff to a new tab/pane/workspace, continue in a new session on herdr. Requires running inside a Herdr pane."
---

# Handoff to a new Herdr session

Write a handoff document, open a new Herdr location, and start the same harness there with the same model and reasoning level. The new session reads the document and continues.

Load the `herdr` skill first. It is the authority on CLI syntax, IDs, and agent states. This skill overrides only its default of sibling pane, current tab, and no new topology: here the user asked for new topology.

## Steps

1. **Resolve the calling pane.** If `HERDR_PANE_ID` is set, use it with `HERDR_WORKSPACE_ID`. Tool shells of some harnesses (opencode) do not inherit these, so otherwise run `herdr agent list` and select the entry whose `.agent_session.value` equals your own session ID (`$OPENCODE_SESSION_ID` for opencode); read its `pane_id`, `tab_id`, `workspace_id`. Use these resolved IDs below as `<pane>`, `<tab>`, `<workspace>`. If neither route yields a pane, tell the user you are not inside Herdr and stop.
2. **Write the handoff document.** Load the `handoff` skill and follow it. Pass the user's focus description as its argument. Note the saved absolute path. Done when the file exists and the path is known.
3. **Pick the location** from the user's words:
   - none given, or "tab": `herdr tab create --workspace <workspace> --cwd "$PWD" --label <slug> --no-focus`. Read `.result.root_pane.pane_id`.
   - "pane" or "split": `herdr pane split <pane> --direction <right|down> --cwd "$PWD" --no-focus`. Choose direction as in the `herdr` skill (`herdr pane layout`). Read `.result.pane.pane_id`.
   - "workspace": `herdr workspace create --cwd "$PWD" --label <slug> --no-focus`. Read `.result.root_pane.pane_id`.
   - Add `--focus` only when the user asks to jump over.
4. **Identify the current harness, model, and reasoning level** (see table). Done when all three are known, or the unknown reasoning level is reported to the user.
5. **Start the same harness** in the new pane. Name it `handoff-<slug>` (`[a-z][a-z0-9_-]{0,31}`, unique among live agents):
   `herdr agent start handoff-<slug> --kind <kind> --pane <pane-id> -- <model-flags>`
   For `opencode`, the TUI has no model flag, so seed a session that carries the model and open it: `opencode run -m <provider/model>[#variant] --title handoff-<slug> --format json "ready"`, read `sessionID` from the first JSON line, then `herdr agent start handoff-<slug> --kind opencode --pane <pane-id> -- --session <sessionID>`.
6. **Prompt it** with `herdr agent prompt handoff-<slug> "Read <handoff-path> and continue from it."` (no `--wait`).
7. **Report** the workspace, tab, and pane IDs, the agent name, and the model and reasoning level used. Done when the user can attach to or close the session from that report.

## Harness, model, reasoning

The harness comes from env vars (or the `agent` field of your `herdr agent list` entry): `OPENCODE=1` is opencode, `CLAUDECODE=1` is claude, `PI_CODING_AGENT` set is pi. For anything else, run `herdr agent list`, find your own pane, and read its kind. The model comes from your own system prompt. The reasoning level comes from the session config or your system prompt. Never guess any of them: omit a flag whose value is unknown and say so in the report.

| kind | model flags |
|------|-------------|
| `opencode` | none on the TUI (`agent start` rejects `--model`); the model rides on the seeded session, see step 5 |
| `claude` | `--model <model> --effort <level>` |
| `pi` | `--model <provider/model> --thinking <level>` |

If `agent start` rejects the flags for a kind, start the agent without them, set the model inside the new session, and tell the user.

## Ownership

Close nothing. The new workspace, tab, pane, and agent belong to the user from here on; the report gives them the IDs.
