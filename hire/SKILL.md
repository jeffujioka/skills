---
name: hire
description: Run a task on a subagent pinned to a chosen model and reasoning level, on opencode, claude or omp, e.g. `@hire senior fix the flaky test` or `@hire opus#medium review this diff`. Manual-only: call it by name.
disable-model-invocation: true
---

# hire

Run one auxiliary task (implementation, code exploration, research) on a subagent pinned to the model and effort the user named. Works on opencode, claude and omp.

## Input

`<rank> <task>`, `<model>#<effort> <task>` or `<model> <effort> <task>`, or the same spread over the user's words ("research X with a sonnet low subagent").

- **rank**: a preset from the table below. It fixes model and effort.
- **model**: `haiku`, `sonnet`, `opus` or `fable`.
- **effort**: `low`, `medium`, `high`, `xhigh` or `max`, joined to the model by `#` or separated by a space.
- **task**: everything after the rank, or after the model and effort, verbatim. It becomes the subagent's prompt.

A first word that is not a rank is read as a model. A missing model or effort is a question for the user. Ask, then continue.

## Ranks

| rank | model#effort |
| --- | --- |
| `intern` | `haiku#low` |
| `junior` | `haiku#medium` |
| `mid` | `haiku#high` |
| `senior` | `sonnet#medium` |
| `lead` | `sonnet#high` |
| `staff`, `principal` | `opus#medium` |
| `head` | `opus#high` |
| `vp` | `opus#xhigh` |
| `cso` | `opus#max` |
| `cto` | `fable#medium` |
| `yoda` | `fable#max` |

## Steps

1. **Find the harness** from the tool you dispatch subagents with: `subagent` is opencode, `Agent` is claude, `task` is omp. Done when you know which one.
2. **Resolve the model.** Done when you hold the value step 4 passes.
   - opencode: run `opencode models` and take the highest version of `github-copilot/claude-<model>-<version>` (`-fast` variants excluded unless the user typed `fast`).
   - claude: the alias itself (`haiku`, `sonnet`, `opus`, `fable`); it names the latest version. The `Agent` tool accepts no full id, so 1M-context variants are out of reach.
   - omp: run `omp models github-copilot --json` and take the highest version of `github-copilot/claude-<model>-<version>`, its `-1m` variant when one exists. Check that `<effort>` is in its `thinking` list; if not, name the levels it has and let the user pick.
3. **Build the prompt.** The subagent starts with fresh context, so the prompt carries everything it needs: the task verbatim, working directory, relevant file paths, constraints the user stated, and the expected output (a short summary, plus a file path for long results). Done when someone with no access to this conversation could execute it.
4. **Dispatch.** Use background only when the user asked for it or has independent work to continue. Done when the subagent's result is in.
   - opencode: call `subagent` with `agent: "general"`, `model: "github-copilot/<id>#<effort>"`, a 3 to 5 word `description`, and the prompt. A `VariantUnavailableError` means the model lacks that effort: name it and let the user pick.
   - claude: call `Agent` with `subagent_type: "general-purpose"`, `model: "<alias>"`, `effort: "<effort>"`, a 3 to 5 word `description`, and the prompt.
   - omp: run `bash "<skill dir>/scripts/omp-agent.sh" create <provider/id> <effort>`; it prints an agent name. Call `task` with that name as the item's `agent` and the prompt as its `task`. Never pass `effort` or `model`: they override the pin. When the result is in, run `bash "<skill dir>/scripts/omp-agent.sh" remove <name>`, also when the subagent failed. The file lives only during the run, so the agent never enters the agent list of later sessions; follow-ups to the idle agent still work.
5. **Relay.** Report the subagent's answer, the model and effort it ran on, and how to continue it: the `sessionID` on opencode, the agent id on claude, `agent://<id>` on omp.

## Parallel tasks

Several tasks with independent scope become one dispatch each, all issued in the same response. Each keeps its own rank or `<model>#<effort>`; tasks without one inherit the nearest preceding one. On omp, create one agent per task and put them all in one `task` call.
