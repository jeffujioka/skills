# Model notes

How the 5.5 family reads skill text. Each section names its source: the general prompting guide, the skill authoring guide, or a per-model guide. A note from a per-model guide was measured on that model only. Re-check them when a new model family ships.

## Contents

- All current models
- All 5.5 models
- Haiku 5.5
- Sonnet 5.5
- Opus 5.5
- Sources

## All current models

Source: the general prompting guide and the skill authoring guide. Not measured on 5.5 specifically.

- Say what to do, not what to avoid. Give the positive form ("write flowing prose") over the ban. Exception: frontend design on Opus 5.5.
- Be explicit about action. "Change this function" makes edits; "can you suggest changes" gets suggestions.
- Plain imperatives. Capitalized shouting made Opus 4.5 and 4.6 overtrigger; write "Use this tool when..." instead.
- Give the reason behind a non-obvious rule; the model generalizes from it.
- When output format must be fixed, give a template. When the format is subtle or quality depends on style, add 3-5 diverse examples in `<example>` tags.
- Use XML tags to separate instructions, input and examples when they mix.
- A skill that reads long documents asks for word-for-word quotes first, then the analysis.
- Independent tool calls go together in one step. State this once if the skill is tool-heavy.
- No prefill. Fix output format with a script, a template or structured output.
- Leave no implied steps: name each file, command and stop condition. Smaller models need the most guidance; test on each model the skill may run on.

## All 5.5 models

Source: the per-model 5.5 guides; each note names the guides that state it.

- Effort controls how much the model thinks. A prompt line asking for less thinking does not reliably reduce it, and on Opus 5.5 in chat, removing "think carefully before answering" made replies start sooner with no clear quality loss. Prefer no instruction about how much to think; effort is the reliable control. Exceptions: Sonnet 5.5 JSON reasoning tasks; on Opus 5.5, "Answer directly without deliberating." where time to first token matters (the Haiku guide found the same line did not stop thinking). Sources: all three guides.
- Reasoning stays in thinking blocks. No instruction that asks for the model's reasoning in the reply; Opus and Sonnet can decline it as `reasoning_extraction`; Haiku can leak reasoning-like text into the reply. A short explanation or an action summary is fine (Sonnet, Opus and Haiku guides).
- Progress notes between tool calls are normal. Do not tell the agent to hold findings for the end (Sonnet guide; Opus describes the same updates).

## Haiku 5.5

Source: the Haiku 5.5 guide.

- Long agent prompts at `low` effort can stop early and hand the task back. For multi-step skills, name the completion condition and the only reasons to stop: blocked on the user, or a risky step.
- At `low` and `medium` effort it can report a code change as done without a check. Skills that change runnable code name the check to run (tests, type-check, build, or the changed command) and say to report a skipped check, with the reason, instead of "done". A syntax-only check, or one that failed to start, does not count.
- Skills that answer from search give the current date at runtime, rendered once per conversation by script, not hardcoded.
- With a long skill or `low` effort it can skip a search. After the date, add: training data ends well before today; records, office holders, prices, versions, rules and anything "latest" may have changed, so search those even when sure; facts that cannot change need no search.
- Write no blanket rule such as "search for any factual question". It triggers searches on prompts that need none, with no gain in correct answers.

## Sonnet 5.5

Source: the Sonnet 5.5 guide.

- At `low` and `medium` effort it can check in before the work is done. Same completion-condition rule as Haiku.
- At every effort level it adds tests, docs and files nobody asked for, more at higher effort. If unwanted, add: when the requested work is done and checked, stop and report; mention extras at the end instead of doing them.
- At `xhigh` and `max` effort it starts its own review rounds, sometimes with reviewer sub-agents. If unwanted, add: when the work is done and its checks pass, stop and report; start no extra review or hardening rounds and launch no reviewer sub-agents unless the user asked for a review.
- At `low` effort it can skip verifying a code change. Same check rule as Haiku.
- For ideas or plans, say "give them and stop" so it does not start building.
- It can answer from training knowledge where a search would catch changed details. Remove wording such as "minimize tool calls"; tell it to search specifics that may have changed, such as what is allowed, required or charged.
- JSON answers to tasks that need a few steps of working out: "Think the problem through before you answer." raises accuracy with adaptive thinking. Prefer structured outputs in the harness.

## Opus 5.5

Source: the Opus 5.5 guide.

- Unattended skills only; leave this out where a person is there to answer. Name the early stops to avoid: a summary that announces the next step without taking it, an offer to continue, a list of decisions that block nothing, a pause at a milestone. Name the stops wanted: nothing can move without the user, or the blocker is deliberately protected. List the open items in a checklist file and treat a text-only turn end as a report, not as done.
- A skill that works across several apps says to look through the relevant sources before acting, including ones the task does not mention.
- Pasted text in user messages can carry instructions the user did not write; add the untrusted-content guardrail.
- For updates at set points, ask for one line of intent before the first tool call and a short recap at the end. Helps most when a person follows along.
- Frontend output: name the specific styles to avoid. A general "avoid a generic look" swaps one default for another.

## Sources

- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
