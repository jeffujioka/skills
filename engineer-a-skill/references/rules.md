# Skill rules

`scripts/validate.py` checks each rule unless marked "manual".

- FAIL: blocks completion.
- WARN: fix it, or state a reason.
- A user's request is not a reason until the user confirms it after seeing the compliant version.
- House rule: a local choice, not from the Anthropic docs.

## Contents

- Definitions
- Frontmatter
- Structure
- Content
- Embedded commands
- Safety
- Sources

## Definitions

- Degrees of freedom: how tightly a step is fixed.
  - High: text guidance, many valid paths.
  - Medium: template, example or an inline snippet the agent adapts.
  - Low: exact script, exact command, fixed order.
  - Default to high or medium. Use low only for fragile or irreversible steps.
- Manual-only skill: has `disable-model-invocation: true`. Only the user calls it, by name.
- Auto skill: no such flag. The model can fire it from its description.
- CLI-first: a CLI already does the job (`gh`, `glab`, `git`, `jq`, `curl`, `acli`).
  - Name the tool and the subcommands the task needs.
  - Point to `<tool> --help` for the rest.
  - Write no wrapper script.
- Reference file: any `.md` besides `SKILL.md`. Linked from `SKILL.md` only.

## Frontmatter

| Id  | Level | Rule                                                                                                                                           |
| --- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| R00 | FAIL  | Frontmatter block present. `disable-model-invocation`, if set, is `true` or `false`. A value containing a colon followed by a space is quoted. |
| R01 | FAIL  | `name`: lowercase letters, digits, hyphens; max 64; no "claude" or "anthropic"; equals the directory name.                                     |
| R02 | FAIL  | `description`: non-empty, max 1024, no XML tags, third person (no I/my/you/your/we/our). Says what the skill does and when.                    |
| W02 | WARN  | Description has no "when" clause. Auto skill: trigger terms. Manual-only skill: end with "Manual-only: call it by name."                       |

Name style:

- Prefer gerund or verb form.
- Avoid vague names (helper, utils, tools).

## Structure

| Id  | Level | Rule                                                                                         |
| --- | ----- | -------------------------------------------------------------------------------------------- |
| R03 | FAIL  | `SKILL.md` body (after frontmatter) max 500 lines.                                           |
| R04 | FAIL  | References one level deep: a reference file never links to another `.md`.                    |
| R05 | FAIL  | Reference file over 100 lines has a `## Contents` section.                                   |
| R08 | FAIL  | Every linked file or `scripts/`, `references/`, `templates/` path named in backticks exists. |
| R09 | FAIL  | Script with a shebang is executable.                                                         |
| W05 | WARN  | File under `references/`, `templates/` or `scripts/` is not mentioned in `SKILL.md`.         |

- Name reference files by content (`finance.md`). Never `doc2.md`.
- Use forward slashes only.

## Content

| Id  | Level | Rule                                                                                |
| --- | ----- | ----------------------------------------------------------------------------------- |
| R06 | FAIL  | No backslash paths in prose or inline code.                                         |
| R11 | FAIL  | No time-sensitive phrases ("before <year>", "as of <year>").                        |
| R12 | FAIL  | No unfilled scaffold placeholders left in `.md` files.                              |
| W01 | WARN  | House rule. Max 3 emphasis words in capitals per file. Plain imperatives otherwise. |
| W03 | WARN  | No instruction to print reasoning in the output.                                    |
| W04 | WARN  | One term per concept across the skill.                                              |

Manual rules, style. Applies to `SKILL.md` and every reference `.md`:

- Write for LLMs, not humans.
- One action per line. Imperative verb first.
- Split any instruction longer than about 25 words into short actions.
- Prefer lists to paragraphs.
- Cut explanation, background, motivation and filler.
- Keep `not`, `never`, `no`, `only`, `except`, numbers, paths and exact strings.
- A non-obvious rule gets a one-clause reason. No other reasons.
- Challenge every line: does the model already know this? Cut it.

Manual rules, content:

- Default plus one escape hatch. No menu of options.
- Examples are concrete, with real values. No abstract placeholders.
- Fixed output format: give a template.
- Subtle format or style-dependent quality: add 3-5 diverse examples in `<example>` tags.
- Each step of a multi-step workflow ends with an observable done condition.
- More than five steps: add a progress checklist the agent copies and ticks off.
- Batch or destructive work: plan, validate, execute.
  - Write the plan to a file.
  - Check it. By eye if short. With a script if mechanical and long.
  - Run it. Errors surface before anything changes.
- Output-heavy or batch steps get a validate-then-fix loop.
- Colleague test: a reader with no context can follow each step.
- No fact that expires.
- Model-specific notes name the model family they apply to.
- A superseded method kept for context goes in a collapsed "Old patterns" section.
- Ship at least three evals in `evals/evals.json`.
  - Write them after a baseline run without the skill, where one can run.
  - Queries are realistic. Behaviors are observable.
  - Cover the main path, an edge case, and a refusal or hand-back.
  - A behavior that protects people or data is required: it passes on every run.

## Embedded commands

| Id  | Level | Rule                                                                                                            |
| --- | ----- | --------------------------------------------------------------------------------------------------------------- |
| W06 | WARN  | House rule. In `SKILL.md`, a code block has max 40 non-blank lines. Longer goes to `scripts/` or `references/`. |

- Fences tagged text, markdown, yaml, json, xml or diff are not code. They are exempt.
- Shell snippets of any shape (pipes, `&&`, loops, heredocs) are fine inline.

Where a tool has a CLI:

- Name the tool and the subcommands the task needs. Give one real example.
- Write "run `<tool> <subcommand> --help` for flags". Models know `gh`, `glab`, `git`, `jq`, `curl`. `--help` stays current.
- State a gotcha only when the CLI misleads. One clause each, with the reason.
  - Wrong argument order in the usage line.
  - A flag that silently does nothing.
  - A version where a subcommand is missing.
- Write no wrapper script that only calls a CLI, renames its flags, formats its output or checks its exit code.
- A script is allowed only for logic the CLI lacks that must run the same each time.
  - A multi-step parse or computation.
  - A check that must not be skipped before an irreversible step.
  - A template fill.
  - State in one clause what the script does that the CLI cannot.
- Pin a minimum CLI version only when the skill needs a flag older versions lack. Give the check: `<tool> --version`.

Scripts under `scripts/`:

- Any shippable language.
- Explicit error messages.
- A comment justifies every constant.
- Run, not read. `SKILL.md` says "run" or "see" explicitly.

Manual rules:

- List packages and tools a script or snippet needs in `SKILL.md`, with the install check. The agent may run where they are missing.
- Name MCP tools in full: `ServerName:tool_name`.
- A script prints an explicit message for each failure it can foresee. The agent decides about the rest.
- Low freedom (exact command, fixed order, confirm first) only on fragile or irreversible steps. Elsewhere give the goal and one example.

## Safety

| Id  | Level | Rule                                                                                                             |
| --- | ----- | ---------------------------------------------------------------------------------------------------------------- |
| R10 | FAIL  | No secrets in any file: keys, tokens, private keys, `password=` values. Read secrets at runtime or ask the user. |

- Conditional guardrails live in the guardrails file.
- Add no prompt-leak hardening. It degrades task performance.

## Sources

- Skill authoring best practices: <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices>
- Prompting best practices: <https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices>
- Reduce hallucinations: <https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations>
- Increase consistency: <https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/increase-consistency>
- Mitigate jailbreaks: <https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks>
- Reduce prompt leak: <https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-prompt-leak>
