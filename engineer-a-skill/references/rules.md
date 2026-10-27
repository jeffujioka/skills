# Skill rules

Each rule is checked by `scripts/validate.py` unless marked "manual". FAIL blocks completion. WARN needs a fix or a stated reason. A user's request is not a reason until the user confirms it after seeing the compliant version. Rules marked "house rule" are local choices, not from the Anthropic docs.

## Contents

- Definitions
- Frontmatter
- Structure
- Content
- Embedded commands
- Safety
- Sources

## Definitions

- **Degrees of freedom:** how tightly a step is fixed. High: text guidance, many valid paths. Medium: template or parameterized script. Low: exact script, exact command, fixed order. Fragile or irreversible steps get low freedom; judgment steps get high.
- **Manual-only skill:** has `disable-model-invocation: true`. Only the user can call it, by name.
- **Auto skill:** no such flag. The model can fire it from its description.
- **Trivial command:** one command per line, pipes allowed, max 3 lines per fence. Anything else is a script under `scripts/`.
- **Reference file:** any `.md` besides `SKILL.md`. Linked from `SKILL.md` only.

## Frontmatter

| Id | Level | Rule |
|---|---|---|
| R00 | FAIL | Frontmatter block present. `disable-model-invocation`, if set, is `true` or `false`. |
| R01 | FAIL | `name`: lowercase letters, digits, hyphens; max 64; no "claude" or "anthropic"; equals the directory name. |
| R02 | FAIL | `description`: non-empty, max 1024, no XML tags, third person (no I/my/you/your/we/our). Says what the skill does and when. |
| W02 | WARN | Description has no "when" clause. Auto skill: trigger terms. Manual-only skill: end with "Manual-only: call it by name." |

Name style: prefer gerund or verb form. Avoid vague names (helper, utils, tools).

## Structure

| Id | Level | Rule |
|---|---|---|
| R03 | FAIL | `SKILL.md` body (after frontmatter) max 500 lines. |
| R04 | FAIL | References one level deep: a reference file never links to another `.md`. |
| R05 | FAIL | Reference file over 100 lines has a `## Contents` section. |
| R08 | FAIL | Every linked file or `scripts/`, `references/`, `templates/` path named in backticks exists. |
| R09 | FAIL | Script with a shebang is executable. |
| W05 | WARN | File under `references/`, `templates/` or `scripts/` is not mentioned in `SKILL.md`. |

Name reference files by content (`finance.md`), never `doc2.md`. Forward slashes only.

## Content

| Id | Level | Rule |
|---|---|---|
| R06 | FAIL | No backslash paths in prose. |
| R11 | FAIL | No time-sensitive phrases ("before <year>", "as of <year>"). |
| R12 | FAIL | No unfilled scaffold placeholders left in `.md` files. |
| W01 | WARN | House rule. Max 3 emphasis words in capitals per file. Plain imperatives otherwise. |
| W03 | WARN | No instruction to print reasoning in the output. |
| W04 | WARN | One term per concept across the skill. |

Manual rules:

- Fragments, imperative verbs, no filler. Keep `not`, `never`, `no`, `only`, `except`, numbers, paths and exact strings.
- Non-obvious rule gets a one-clause reason.
- Challenge every line: does Claude already know this? Cut it.
- Default plus one escape hatch, not a menu of options.
- Examples concrete, with real values, not abstract placeholders.
- Template when output format must be fixed. When the format is subtle or quality depends on style, add 3-5 diverse examples in `<example>` tags.
- Multi-step workflows end each step with an observable done condition.
- Workflow of more than five steps: a progress checklist the agent copies and ticks off, so no step is skipped.
- Batch or destructive work: plan, validate, execute. Write the plan to a file, check it with a script, then run it; errors surface before anything changes.
- Output-heavy or batch steps get a validate-then-fix loop.
- Colleague test: a reader with no context could follow each step.
- No fact that expires. Model-specific notes name the model family they apply to. A superseded method kept for context goes in a collapsed "Old patterns" section.
- Ships at least three evals in `evals/evals.json`, written after a baseline run without the skill where one can run: realistic queries, observable expected behaviors, covering the main path, an edge case and a refusal or hand-back. Evals show the skill solves real requests, not imagined ones.

## Embedded commands

| Id | Level | Rule |
|---|---|---|
| R07 | FAIL | House rule. In `SKILL.md`, a fenced code block has max 3 non-blank lines. Shell blocks: pipes allowed; no `&&`, `||`, `;`, heredocs, loops or conditionals. |

Fences tagged text, markdown, yaml, json, xml or diff are not code and are exempt. Untagged fences are checked as shell.

Scripts under `scripts/` may use any shippable language. They handle errors with explicit messages, justify every constant in a comment, and are run, not read. `SKILL.md` says "run" or "see" explicitly.

Manual rules:

- Packages and tools a script needs are listed in `SKILL.md` with the check that they are installed. The agent may run where they are missing.
- MCP tools are named in full, `ServerName:tool_name`, so the right server is picked when several are loaded.
- Scripts solve the problem; they do not hand errors back for the agent to work out.

## Safety

| Id | Level | Rule |
|---|---|---|
| R10 | FAIL | No secrets in any file: keys, tokens, private keys, `password=` values. Read secrets at runtime or ask the user. |

Conditional guardrails live in the guardrails file. Prompt-leak hardening is not added: it degrades task performance.

## Sources

- Skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Prompting best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- Reduce hallucinations: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations
- Increase consistency: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/increase-consistency
- Mitigate jailbreaks: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks
- Reduce prompt leak: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-prompt-leak
