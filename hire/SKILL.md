---
name: hire
description: Run a task on a subagent pinned to a chosen model and reasoning level, e.g. `@hire senior <task>`, `@hire haiku#high <task>` or `@hire haiku high <task>`
disable-model-invocation: true
---

# hire

Run one auxiliary task (implementation, code exploration, research) on a subagent pinned to the model and effort the user named.

## Input

`<rank> <task>`, `<model>#<effort> <task>` or `<model> <effort> <task>`, or the same spread over the user's words ("research X with a sonnet low subagent").

- **rank**: a preset from the table below. It fixes model and effort.
- **model**: `haiku`, `sonnet` or `opus`.
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
| `head`, `vp` | `opus#high` |
| `cto` | `opus#max` |

## Steps

1. **Resolve the model.** Run `opencode models` and take the highest version of `github-copilot/claude-<model>-<version>` (`-fast` variants excluded unless the user typed `fast`). Done when you hold one exact id.
2. **Check the effort.** Confirm `<effort>` is among that model's `variants` (`openchamber` `models.search`, `provider` + `query` = the id). Done when it is listed. If not, name the variants it has and let the user pick.
3. **Build the prompt.** The subagent starts with fresh context, so the prompt carries everything it needs: the task verbatim, working directory, relevant file paths, constraints the user stated, and the expected output (a short summary, plus a file path for long results). Done when someone with no access to this conversation could execute it.
4. **Dispatch.** Call `subagent` with `agent: "general"`, `model: "github-copilot/<id>#<effort>"`, a 3 to 5 word `description`, and the prompt. Use `background: true` only when the user asked for it or has independent work to continue.
5. **Relay.** Report the subagent's answer, the `provider/id#variant` it ran on, and its `sessionID` so the user can continue it.

## Parallel tasks

Several tasks with independent scope become one dispatch each, all issued in the same response. Each keeps its own rank or `<model>#<effort>`; tasks without one inherit the nearest preceding one.
