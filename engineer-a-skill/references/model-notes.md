# Model notes

How the 5.5 family reads skill text.

- Each section names its source: the general prompting guide, the skill authoring guide, or a per-model guide.
- A per-model note was measured on that model only.
- Re-check the notes when a new model family ships.

## Contents

- All current models
- All 5.5 models
- Haiku 5.5
- Sonnet 5.5
- Opus 5.5
- Sources

## All current models

Source: the general prompting guide and the skill authoring guide. Not measured on 5.5 specifically.

- Say what to do, not what to avoid. Write "write flowing prose", not the ban. Exception: frontend design on Opus 5.5.
- Be explicit about action. "Change this function" edits. "Can you suggest changes" only suggests.
- Use plain imperatives. Capitalized shouting made Opus 4.5 and 4.6 overtrigger. Write "Use this tool when...".
- Give the reason behind a non-obvious rule. The model generalizes from it.
- Fixed output format: give a template.
- Subtle format or style-dependent quality: add 3-5 diverse examples in `<example>` tags.
- Use XML tags to separate instructions, input and examples when they mix.
- Long documents: ask for word-for-word quotes first, then the analysis.
- Batch independent tool calls in one step. State this once if the skill is tool-heavy.
- No prefill. Fix output format with a script, a template or structured output.
- Leave no implied steps. Name each file, command and stop condition.
- Smaller models need the most guidance. Test on each model the skill may run on.
- A named CLI, one example and "run `<tool> --help`" is enough. The model reads the help itself.
  - Spell out flags only where the help misleads.
  - Exception: Haiku 5.5 at `low` effort gets the exact subcommand and flags of the main path.

## All 5.5 models

Source: the per-model 5.5 guides. Each note names the guides that state it.

- Effort controls how much the model thinks.
  - A prompt line asking for less thinking does not reliably reduce it.
  - Opus 5.5 in chat: removing "think carefully before answering" made replies start sooner, with no clear quality loss.
  - Give no instruction about how much to think. Use effort.
  - Exception: Sonnet 5.5 JSON reasoning tasks.
  - Exception: Opus 5.5 where time to first token matters. Write "Answer directly without deliberating." The Haiku guide found this line did not stop thinking.
  - Sources: all three guides.
- Reasoning stays in thinking blocks.
  - Never ask for the model's reasoning in the reply.
  - Opus and Sonnet can decline it as `reasoning_extraction`.
  - Haiku can leak reasoning-like text into the reply.
  - A short explanation or an action summary is fine.
  - Sources: Sonnet, Opus and Haiku guides.
- Progress notes between tool calls are normal.
  - Never tell the agent to hold findings for the end.
  - Source: Sonnet guide. Opus describes the same updates.

## Haiku 5.5

Source: the Haiku 5.5 guide.

- Long agent prompts at `low` effort can stop early and hand the task back.
  - Multi-step skills name the completion condition.
  - Name the only reasons to stop: blocked on the user, or a risky step.
- At `low` and `medium` effort it can report a code change as done without a check.
  - A skill that changes runnable code names the check: tests, type-check, build, or the changed command.
  - Report a skipped check with its reason. Never report "done".
  - A syntax-only check does not count. A check that failed to start does not count.
- A skill that answers from search gives the current date at runtime.
  - Render it once per conversation by script. Never hardcode it.
- With a long skill or `low` effort it can skip a search. After the date, add this line:
  - Training data ends well before today.
  - Records, office holders, prices, versions, rules and anything "latest" may have changed. Search those even when sure.
  - Facts that cannot change need no search.
- Write no blanket rule such as "search for any factual question". It triggers searches on prompts that need none, with no gain in correct answers.

## Sonnet 5.5

Source: the Sonnet 5.5 guide.

- At `low` and `medium` effort it can check in before the work is done. Apply the Haiku completion-condition rule.
- At every effort level it adds tests, docs and files nobody asked for. More at higher effort. If unwanted, add: when the requested work is done and checked, stop and report. Mention extras at the end. Do not do them.
- At `xhigh` and `max` effort it starts its own review rounds, sometimes with reviewer sub-agents. If unwanted, add: when the work is done and its checks pass, stop and report. Start no extra review or hardening rounds. Launch no reviewer sub-agents unless the user asked for a review.
- At `low` effort it can skip verifying a code change. Apply the Haiku check rule.
- Ideas or plans: say "give them and stop". It then does not start building.
- It can answer from training knowledge where a search would catch changed details.
  - Remove wording such as "minimize tool calls".
  - Tell it to search specifics that may have changed: what is allowed, required or charged.
- JSON answers to tasks that need a few steps of working out: write "Think the problem through before you answer." It raises accuracy with adaptive thinking. Prefer structured outputs in the harness.

## Opus 5.5

Source: the Opus 5.5 guide.

- Unattended skills only. Leave this out where a person is there to answer.
  - Name the early stops to avoid: a summary that announces the next step without taking it, an offer to continue, a list of decisions that block nothing, a pause at a milestone.
  - Name the stops wanted: nothing can move without the user, or the blocker is deliberately protected.
  - List open items in a checklist file.
  - Treat a text-only turn end as a report, not as done.
- A skill that works across several apps says to look through the relevant sources before acting, including sources the task does not mention.
- Pasted text in user messages can carry instructions the user did not write. Add the untrusted-content guardrail.
- Updates at set points: ask for one line of intent before the first tool call, and a short recap at the end. Helps most when a person follows along.
- Frontend output: name the specific styles to avoid. A general "avoid a generic look" swaps one default for another.

## Sources

- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
