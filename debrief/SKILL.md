---
name: debrief
description: "Debrief the current session into an LLM-optimized summary saved to .agents/debriefs/"
argument-hint: "Optional: session name override"
disable-model-invocation: true
---

# Debrief — Session Context Extractor

Process the current conversation into a terse, LLM-consumable summary. The output becomes context for future sessions — preventing repeated troubleshooting, preserving decisions, tracking what failed and why.

## Steps

1. **Scan the conversation** — collect decisions made, things tried (success and failure), discoveries, unresolved items, files touched. Done when every decision and every attempt/failure in the transcript is accounted for — these are the highest-value sections.

2. **Determine session name** — slug from the main topic (e.g. `fix-auth-crash`, `setup-ci-pipeline`, `refactor-navigation`). If the user passed an argument, use that as the name.

3. **Determine metadata** — date, project name (from cwd basename), current git branch, tags (from content: bug-fix, feature, refactor, troubleshooting, arch-decision, config, ci, docs), status (resolved | partial | abandoned). Include session_id only if the runtime exposes it (e.g. session folder path); omit otherwise.

4. **Generate the debrief** — follow the Output Format and Style Rules below exactly.

5. **Save the file** — create `.agents/debriefs/` if needed, write to `.agents/debriefs/YYYY-MM-DD-<session-name>.md`. If that path already exists, append `-2`, `-3`, … to the name. Report the path.

## Output Format

```markdown
---
session_id: <uuid, if available>
date: YYYY-MM-DD
project: <project-name>
git_branch: <branch>
tags: [tag1, tag2]
status: resolved | partial | abandoned
related: [<prior debrief filenames this session continues, if any>]
---

# <Terse descriptive title>

## Summary
2-3 lines max. What happened. Caveman.

## Decisions
- <choice> → reason: <why> → rejected: <alternative considered, if any>

## Attempts & Failures
- tried <X> → failed: <error msg, version, config specifics> → cause: <root cause, if known>
- tried <Y> → worked: <what made it work> (include when it contrasts with a failure)

## Discoveries
- <finding as leading word + one-line consequence, e.g. "pnpm hoisting — breaks patch-package, must use .npmrc shamefully-hoist">

## Unresolved
- <what remains open> → next: <concrete resumption step, if obvious>

## Files Changed
- path/to/file — <what changed, terse>

## References
- <URL> — <one-word why it mattered>
```

## Style Rules

- Caveman/telegram — minimize tokens, maximize signal; optimize for LLM consumption
- Leading words over explanations — "vertical slices" not "we decided to develop in vertical slices because..."
- Bullet points only; one fact per bullet
- Arrow chains (`→`) for causality: attempt → outcome → cause. Keep key names stable (`failed:`, `worked:`, `reason:`, `cause:`, `next:`) — future LLMs grep these
- Attempts & Failures: include exact error messages, versions, configs that matter — verbatim beats paraphrase
- Decisions: always pair with reason; name the rejected alternative when one was weighed
- Omit sections with nothing to report — except Summary, Decisions, Attempts & Failures (always present; write "none" if truly empty)
- Omit `related` frontmatter when the session continues nothing
