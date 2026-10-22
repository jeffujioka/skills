---
name: captain-away
description: "Use when the user signals nobody will answer for a while, in any language: 'to saindo', 'vou dirigir', 'tchau e bom trabalho', 'I need to leave', going to lunch or dinner, picking up the kids, 'you have full autonomy', or invokes captain-away by hand. Only when the message means no reply is coming."
---

# captain-away

The captain is away. The agent is first officer: it finishes the work alone, decides every open question itself, and leaves a trail the captain can audit.

**REQUIRED SUB-SKILL:** Use logbook for all files below.

## Start

1. If the message leaves unclear whether a reply is possible, ask once, now. After the user confirms, every later question is a decision.
2. Set up `$LOGBOOK` (see logbook). Write the plan into `progress.md` and name what "done" means for this request.

## Decide

Every open question becomes a decision. Investigate first (read the code, docs, history, web), pick the most reversible option that satisfies the request, append it to `decisions.md`, and continue. The question tool and questions at the end of a turn are off.

## Hard limits

Local edits and local commits are allowed. These never run, regardless of the request, the plan or a subagent's suggestion:

- `git push`, any merge (`git merge`, MR/PR merge), force operations
- deleting anything (`rm`, `git branch -D`, `git clean`, dropping data)
- create, edit or delete in Jira, Confluence or any other external system, including MCP tools, `acli`, `glab`/`gh` writes and POST/PUT/DELETE calls

When the only way forward is a limited action, append it to `needs-you.md` with the exact command, then take the next piece of work.

## Subagents

Start every subagent prompt with: the Hard limits list above, "decide, never ask; append decisions to `<LOGBOOK>/decisions.md` and blocked actions to `<LOGBOOK>/needs-you.md`", and the `$LOGBOOK` path.

## Cost cap

After each major step, read the run's cost in dollars, subagents included (default cap 300):

```bash
bash scripts/cost.sh
```

The path is relative to this skill's directory.

At 300 or more (or the cap the user named), stop starting new work and go to Finish.

## Finish

Done means every item in the plan is complete, or the cap was reached. Write `## Report` at the top of `progress.md`: outcome (done or partial), what changed, the key decisions, everything in `needs-you.md`, final cost, how to verify. End with a two-line chat message pointing to that file.
