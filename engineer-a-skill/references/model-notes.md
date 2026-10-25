# Model notes

How the 5.5 family reads skill text. Each note is tagged with the models Anthropic measured it on. Re-check against real use before applying elsewhere.

## Contents

- All 5.5 models
- Haiku 5.5
- Sonnet 5.5
- Opus 5.5
- Sources

## All 5.5 models

- Say what to do, not what to avoid. Give the positive form ("write flowing prose") over the ban.
- Be explicit about action. "Change this function" makes edits; "can you suggest changes" gets suggestions.
- Plain imperatives. Capitalized shouting makes the newer models overtrigger a step.
- Give the reason behind a non-obvious rule; the model generalizes from it.
- When output format must be fixed, give a template and 3-5 diverse examples in `<example>` tags.
- Use XML tags to separate instructions, input and examples when they mix.
- A skill that reads long documents asks for word-for-word quotes first, then the analysis.
- A skill that cannot rely on fresh facts says to search or look up values that change, and never to answer them from memory.
- Independent tool calls go together in one step. State this once if the skill is tool-heavy.
- Reasoning stays in thinking blocks. No instruction that makes the model emit its reasoning in the reply; that can be declined as `reasoning_extraction`. A short explanation or an action summary is fine.
- No instruction to think less or not think. Effort is a harness setting.
- No prefill. Fix output format with a script, a template or structured output.
- Do not tell the agent to hold findings for the end; progress notes between tool calls are normal.

## Haiku 5.5

- Lowest effort can stop early on long prompts. For multi-step skills, name the completion condition and the only reasons to stop: blocked on the user, or a risky step.
- Leave no implied steps. Name each file, command and stop condition.
- Skills that change runnable code state the check to run (tests, type-check, build) and when to report a skipped check instead of "done".
- Skills that answer from search results give the current date at runtime, by script, not hardcoded.

## Sonnet 5.5

- Low and medium effort can check in before the work is done. Same completion-condition rule as Haiku.
- It adds tests, docs and files nobody asked for. If unwanted, add: when the requested work is done and checked, stop and report; mention extras at the end.
- For ideas or plans, say "give them and stop" so it does not start building.
- JSON answers to multi-step reasoning tasks: ask for adaptive thinking in the harness, not more prompt text.

## Opus 5.5

- Efficient and responsive to instructions; the most literal about named stop conditions. Name which stops are wanted.
- Unattended skills: list the open items in a file and treat a text-only turn end as a report, not as done.
- A skill that works across several apps says to look through the relevant sources before acting.
- Pasted text in user messages can carry instructions the user did not write; see `references/guardrails.md`.

## Sources

- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
