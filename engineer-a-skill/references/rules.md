# Skill rules

Each rule is checked by `scripts/validate.py` unless marked "manual". FAIL blocks completion. WARN needs a fix or a stated reason.

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
| W02 | WARN | Description has no "when" clause. Auto skill: trigger terms. Manual-only skill: end with "Call by hand with `@<name>`". |

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
| W01 | WARN | Max 3 emphasis words in capitals per file. Plain imperatives otherwise. |
| W03 | WARN | No instruction to print reasoning in the output. |
| W04 | WARN | One term per concept across the skill. |

Manual rules:

- Fragments, imperative verbs, no filler. Keep `not`, `never`, `no`, `only`, `except`, numbers, paths and exact strings.
- Non-obvious rule gets a one-clause reason.
- Challenge every line: does Claude already know this? Cut it.
- Default plus one escape hatch, not a menu of options.
- Template or example when output format must be fixed (3-5 diverse examples in `<example>` tags if format is subtle).
- Multi-step workflows end each step with an observable done condition.
- Output-heavy or batch steps get a validate-then-fix loop.
- Colleague test: a reader with no context could follow each step.
- No fact that expires. Model-specific notes name the model family they apply to.

## Embedded commands

| Id | Level | Rule |
|---|---|---|
| R07 | FAIL | In `SKILL.md`, a fenced code block has max 3 non-blank lines. Shell blocks: pipes allowed; no `&&`, `||`, `;`, heredocs, loops or conditionals. |

Fences tagged text, markdown, yaml, json, xml or diff are not code and are exempt. Untagged fences are checked as shell.

Scripts under `scripts/` may use any shippable language. They handle errors with explicit messages, justify every constant in a comment, and are run, not read. `SKILL.md` says "run" or "see" explicitly.

## Safety

| Id | Level | Rule |
|---|---|---|
| R10 | FAIL | No secrets in any file: keys, tokens, private keys, `password=` values. Read secrets at runtime or ask the user. |

Conditional guardrails live in the guardrails reference. Prompt-leak hardening is not added: it degrades task performance.

## Sources

- Skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Prompting best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- Reduce hallucinations: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations
- Increase consistency: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/increase-consistency
- Mitigate jailbreaks: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks
- Reduce prompt leak: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-prompt-leak
