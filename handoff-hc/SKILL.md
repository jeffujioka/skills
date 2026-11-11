---
name: handoff-hc
description: "Use when handing off the current conversation to a fresh session started through hc (herdr-core), on the same harness or another one (opencode, claude, omp), optionally with a chosen model (opus, sonnet, haiku, or a name) and reasoning level. Triggers on: handoff with hc, handoff in herdr-app, handoff to a new terminal/tab, handoff to claude/opencode/omp, continue in a new session. Requires running inside an hc terminal (HC_TERMINAL_ID set)."
---

# Handoff to a new hc session

Write a handoff document, start a harness in a new `hc` terminal, and prompt it to continue. The new session reads the document and continues.

Supported harnesses: `opencode`, `claude`, `omp`. Details per harness: [references/opencode.md](references/opencode.md), [references/claude.md](references/claude.md), [references/omp.md](references/omp.md). Model matching rules: [references/model-matching.md](references/model-matching.md). `hc --skill` is the authority on `hc` syntax.

`hc` runs programs in persistent terminals and does not arrange windows. It has no command for a tab or a workspace. The new terminal joins the caller's workspace through the `herdr.space` label (step 5).

By default the new session has **no parent**: it is a top-level agent in the herdr sidebar. Only when the user asks for a child (`child`, `sub-agent`, `with parent`) does the calling terminal become its parent.

## Stops

Run steps 1-8 without pausing. Stop early only for these:

- Not inside an hc terminal (step 1).
- The user named an unsupported harness (step 2).
- The model or reasoning level needs a pick from the user (step 3). Show the list and wait.
- The `handoff` skill cannot be loaded or read (step 4). Ask the user to run `/handoff` and wait for the path.

When the report (step 8) is printed, stop. Add nothing else.

## Steps

Copy this checklist and tick each step:

```text
- [ ] 1 Calling terminal  - [ ] 2 Target harness  - [ ] 3 Model, reasoning
- [ ] 4 Handoff doc       - [ ] 5 Placement       - [ ] 6 Start (top-level or child)
- [ ] 7 Confirm prompt    - [ ] 8 Report
```

1. **Resolve the calling terminal.** Read `$HC_TERMINAL_ID`. If it is empty, tell the user you are not inside an hc terminal and stop. Run `hc get $HC_TERMINAL_ID --json` and read `.labels["herdr.space"]` (may be absent). Done when `<terminal>` is known.
2. **Resolve the target harness.** If the user names one (`opencode`, `claude`, `omp`), use it. If they name any other harness, stop and say: supported are opencode, claude, omp. If they name none, the target is the current harness: `OPENCODE=1` is opencode, `CLAUDECODE=1` is claude, otherwise read `.foreground.name` of `hc get $HC_TERMINAL_ID --json`. Read `references/<target>.md` now. Done when the target is one of the three and its file is read.
3. **Resolve model and reasoning.** Never guess a value: omit a flag whose value is unknown and say so in the report.
   - **Wanted model**: the model the user named (a full name, a family name `opus`/`sonnet`/`haiku`, or a family with a version), else the current model. The current model comes from your own system prompt.
   - **Wanted reasoning**: the level the user named (`low`, `medium`, `high`, `xhigh`, `max`; they may call it effort or thinking), else the current level from the session config or system prompt.
   - **Match** the wanted model with the target's file and `references/model-matching.md`. A family name alone selects its newest version. One match: use the candidate's full value unchanged. Several matches left: show only those and ask the user to pick. No match: show the full list and ask the user to pick.
   - **Reasoning check**: the target's file says which values it accepts. A level the user named that the chosen model does not accept: show what it accepts and ask the user to pick. A carried-over current level that is not accepted: omit the flag and say so in the report. Do not ask.
   - Done when one model is chosen, or the user says default (omit the model flag), and the reasoning flag is set or omitted.
4. **Write the handoff document.** Load the `handoff` skill and follow it. If the load is refused or the skill is not found, read `~/.claude/skills/handoff/SKILL.md` and follow it directly. If that file does not exist either, stop: ask the user to run `/handoff` and give you the saved path, then continue from step 5. Pass the user's focus description as the skill's argument. Done when the file exists and its absolute path is known.
5. **Pick placement.** Name: `handoff-<slug>` (1-32 of `a-z 0-9 - _`, not in `hc ls`), where `<slug>` is two or three lowercase words from the focus, joined by `-`. Space and directory: default is the caller's `herdr.space` from step 1 and `$PWD`. If the user names a target space (`on <space>`, `in the <space> space`), find a live terminal in it: run `hc ls --json`, `hc get` each address, and keep those whose `.labels.where` starts with `<space> / `. Take `herdr.space` from the first match and `<cwd>` from the match's `.cwd` (several matches with different cwds: use the most common one). No match: stop and ask the user for the space's directory and tell them no label can be resolved. Labels: pass `--label herdr.space=<value>`; the app then places the terminal in that workspace. Copy the value from a live terminal, never invent one. Without any `herdr.space` label the app does not place the terminal: pass none and tell the user in the report to attach it with `hc attach`. Done when name, cwd and label list are fixed.
6. **Start the target harness and give it the first task in one command**, using the recipe in the target's file. Common flags: `hc run --bg --json --name handoff-<slug> --cwd "<cwd>" <mode flags> [--label ...] <harness argv> "Read <handoff-path> and continue from it."`. Mode flags: default (top-level) `--no-parent`, which makes `--outlive-parent` and `--no-notify` moot, so omit them; child (user asked) `--outlive-parent --no-notify`, no `--no-parent`: `--outlive-parent` keeps it alive after this session ends, `--no-notify` keeps exit notes out of this session. If the harness rejects a flag, start without it, set the model inside the new session, and tell the user. Done when `hc run` exits 0 and `hc get handoff-<slug> --json` has `.state` of `live` and `.parent` null (top-level) or `$HC_TERMINAL_ID` (child). If any fails, report that, not "started".
7. **Confirm the prompt arrived.** Run `hc wait handoff-<slug> --json --output "<handoff-file-name>" --timeout 30`, where `<handoff-file-name>` is the file name without its directory. `reason: output` means the harness printed the prompt: arrived. Any other reason: run `hc read handoff-<slug> --lines 40` and decide from the screen. Prompt text present: arrived. A dialog (claude asks to trust the folder): leave it and tell the user to run `hc attach handoff-<slug>`. Prompt text absent and the harness at its input box: `hc send handoff-<slug> "Read <handoff-path> and continue from it."`. Leave out `--wait`. Never poll or sleep. `hc get` status stays empty for claude, so use the screen. Done when the prompt is confirmed or the screen shows why not.
8. **Report** the address (`t<N>`), the name, whether it is a top-level agent or a child of `<calling terminal>`, the cwd, the `herdr.space` label used (or that none was), the harness, the model and reasoning level used (or that the default was used; for claude, the header line from `hc read handoff-<slug> --lines 15` that shows the resolved model and effort), and `hc attach <name>` (Ctrl+\ detaches). Done when the user can attach to or close the session from that report.

Steps 2-3 run before anything is created, so a stop or a pick leaves no orphan terminal.

## Ownership

Close nothing. The new terminal belongs to the user from here on; the report gives them its name and address.
