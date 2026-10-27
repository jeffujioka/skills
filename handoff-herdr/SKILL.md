---
name: handoff-herdr
description: "Use when handing off the current conversation to a fresh session in a new Herdr tab, pane, or workspace, on the same harness or another one (opencode, claude, omp). Triggers on: handoff in herdr, handoff to a new tab/pane/workspace, handoff to claude/opencode/omp, continue in a new session on herdr. Requires running inside a Herdr pane."
---

# Handoff to a new Herdr session

Write a handoff document, open a new Herdr location, and start a harness there. The new session reads the document and continues.

Load the `herdr` skill first. It is the authority on CLI syntax, IDs, and agent states. This skill overrides only its default of sibling pane, current tab, and no new topology: here the user asked for new topology.

Supported harnesses: `opencode`, `claude`, `omp`. Details per harness: [references/opencode.md](references/opencode.md), [references/claude.md](references/claude.md), [references/omp.md](references/omp.md). Model matching rules: [references/model-matching.md](references/model-matching.md).

## Stops

Run steps 1-8 without pausing. Stop early only for these:

- Not inside Herdr (step 1).
- The user named an unsupported harness (step 2).
- The model needs a pick from the user (step 3). Show the list and wait.
- The `handoff` skill cannot be loaded or read (step 4). Ask the user to run `/handoff` and wait for the path.

When the report (step 8) is printed, stop. Add nothing else.

## Steps

Copy this checklist and tick each step:

```text
- [ ] 1 Calling pane    - [ ] 2 Target harness   - [ ] 3 Model, reasoning
- [ ] 4 Handoff doc     - [ ] 5 Location         - [ ] 6 Start
- [ ] 7 Prompt          - [ ] 8 Report
```

1. **Resolve the calling pane.** If `HERDR_PANE_ID` is set, use it with `HERDR_WORKSPACE_ID`. Tool shells of some harnesses (opencode) do not inherit these, so otherwise run `herdr agent list` and select the entry whose `.agent_session.value` equals your own session ID; read its `pane_id`, `tab_id`, `workspace_id`. Use these as `<pane>`, `<tab>`, `<workspace>`. If neither route yields a pane, tell the user you are not inside Herdr and stop. Done when `<pane>` and `<workspace>` are known.
2. **Resolve the target harness.** If the user names one (`opencode`, `claude`, `omp`), use it. If they name any other harness, stop and say: supported are opencode, claude, omp. If they name none, the target is the current harness: `OPENCODE=1` is opencode, `CLAUDECODE=1` is claude, otherwise read the `agent` field of your `herdr agent list` entry. Read `references/<target>.md` now. Done when the target is one of the three and its file is read.
3. **Resolve model and reasoning.** Never guess a value: omit a flag whose value is unknown and say so in the report.
   - **Current model and reasoning**: the model comes from your own system prompt, the reasoning level from the session config or system prompt.
   - **Wanted model**: the model the user named, else the current model.
   - **Match** it against the target's model list with the rules in `references/model-matching.md`. One match: use the candidate's full value unchanged. Several matches: show only those and ask the user to pick. No match: show the full list and ask the user to pick.
   - **Reasoning**: carry the current level over only if the target accepts that exact value (see the target's file). Otherwise omit the flag and say so in the report. Do not ask.
   - Done when one model is chosen, or the user says default (omit the model flag).
4. **Write the handoff document.** Load the `handoff` skill and follow it. If the load is refused or the skill is not found, read `~/.claude/skills/handoff/SKILL.md` and follow it directly. If that file does not exist either, stop: ask the user to run `/handoff` and give you the saved path, then continue from step 5. Pass the user's focus description as the skill's argument. Done when the file exists and its absolute path is known.
5. **Pick the location** from the user's words:
   - none given, or "tab": `herdr tab create --workspace <workspace> --cwd "$PWD" --label <slug> --no-focus`. Read `.result.root_pane.pane_id`.
   - "pane" or "split": `herdr pane split <pane> --direction <right|down> --cwd "$PWD" --no-focus`. Choose direction as in the `herdr` skill (`herdr pane layout`). Read `.result.pane.pane_id`.
   - "workspace": `herdr workspace create --cwd "$PWD" --label <slug> --no-focus`. Read `.result.root_pane.pane_id`.
   - Add `--focus` only when the user asks to jump over.
   - Done when the new pane ID is read from the JSON.
6. **Start the target harness** in the new pane, named `handoff-<slug>` (`[a-z][a-z0-9_-]{0,31}`, unique among live agents), using the recipe in the target's file. If `agent start` rejects the flags, start without them, set the model inside the new session, and tell the user. Done when `agent start` exits 0 and `herdr agent list` shows `handoff-<slug>`. If either fails, report that, not "started".
7. **Prompt it** with `herdr agent prompt handoff-<slug> "Read <handoff-path> and continue from it."`. Leave out `--wait`: a fast agent answers inside 5 s and Herdr then reports `agent_prompt_stalled` although the prompt arrived. Done when the command prints `agent_prompt` JSON, or an `agent_prompt_stalled` error (read the pane before resending).
8. **Report** the workspace, tab, and pane IDs, the agent name, the harness, and the model and reasoning level used (or that the default was used). Done when the user can attach to or close the session from that report.

Steps 2-3 run before anything is created, so a stop or a pick leaves no orphan tab.

## Ownership

Close nothing. The new workspace, tab, pane, and agent belong to the user from here on; the report gives them the IDs.
