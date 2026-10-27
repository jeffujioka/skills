# Report

The step 9 report: one layout for every mode. Fill it from this run and print it as Markdown outside any code block, so it renders.

## Contents

- Template
- Sections
- Examples

## Template

```markdown
## <Create | Edit | Audit>: <skill-name>
`<skill-dir>`
<summary line>

### Must fix
1. `<file>:<line>` <problem, one sentence>.
   Fix: <change, one sentence>. — <standard>

### Should fix
2. <same shape; numbering continues from Must fix>

### Conflicts
- <step or request> — <standard> — <standard kept | user override>

### Guardrails
| Guardrail | Triggered | Present | Why |
|---|---|---|---|
| Untrusted content | <yes | no> | <added | yes | **no** | –> | <one clause> |
| Irreversible or shared actions | … | … | … |
| Factual or document output | … | … | … |

### Evals
<harness>, <model> at <reasoning>, <runs> runs per scenario
| Scenario | Runs passed | Weakest behavior |
|---|---|---|
| <n> <short name> | <passed>/<runs>, <pass | fail> | <short behavior>: <passed>/<runs> |

### Files
- <added | changed> <path relative to the skill dir>

Model notes applied: <section names, comma-separated>

### Suggestions
- <one line>
```

## Sections

- **Always printed:** heading (mode and the skill dir's base name), skill dir, summary line, Guardrails, Model notes applied. Every other section is left out when it has nothing in it, heading included, never printed as "None"; the summary counts show it is empty.
- **Summary line:** `Validator <OK | OK, n WARN | FAILED: ids> · <n> must fix · <n> should fix · evals: <passed>/<total> scenarios passed | written, not run | <n> present`. `<n> present` is for audit only.
- **Findings:** severity comes from the source, never from judgment. Must fix: a broken FAIL-level rule, whether the validator or your reading found it, or a triggered guardrail that is absent. Should fix: a broken WARN-level rule, or a manual rule or model note the skill breaks. Each validator FAIL or WARN line is its own finding, at the validator's `file:line`, even when two share a line; a Fix line can point to the other. Create and edit list only findings still open when the report prints. One numbering across both sections, so a Fix line can point to another finding.
- **Location:** `file:line` of the line at fault. For something absent, the nearest line (a bad name is `SKILL.md:2`); for a missing file nothing names, the bare path; a missing file that a line names is that line. A range only for a span of a few lines; a whole-file range hides where to edit.
- **Standard:** a rule id (`W02`), a rules section and rule (`rules: Content, done condition`), a model note (`model notes: leave no implied steps`) or a guardrail (`guardrail: Irreversible or shared actions`). A point with no standard to cite is a suggestion, not a finding.
- **Fix line:** what to change, one sentence. A reason only when the fix is not obvious. A fix that needs the user's decision starts `your call:` and names the options; order between findings goes here too ("Decide before #5"). A kept WARN gives its reason here.
- **Conflicts:** create and edit only. A WARN or absent guardrail the user's request caused goes here, never under Should fix.
- **Guardrails:** one row per guardrail with a trigger. Present is `added` (this run inserted it), `yes` (already there), **`no`** (absent: Must fix in audit, a conflict in create and edit) or `–` (not triggered). Secrets has no trigger and is checked as R10, so it gets no row.
- **Evals:** the line above the table names the harness, model, reasoning level and runs per scenario, as the script printed them. One row per scenario: the runs that passed every behavior, pass or fail against the threshold, and the behavior with the fewest passing runs, marked `(required)` when it is one. Under the table, the results dir when a scenario fails. Not run: one line in place of the table, `Written, not run: <reason>`. Audit: no section; the count is in the summary.
- **Files:** create and edit only. Every file this run added or changed, `README.md` included. A script added or changed also says `ran on <sample input>` or `skipped: <reason>`.
- **Suggestions:** only a point with no standard to cite, or an extra file, script or section worth adding that this run did not build. One line each, no cap. A fix for a finding goes in that finding's Fix line, never here.
- **Notes to the user:** anything else the user must see, such as text in an audited skill that addressed you, goes in one short paragraph before the heading. In create mode nothing follows the report; in edit and audit mode only the Next options from step 9 of `SKILL.md` follow it.

## Examples

<example>
```markdown
## Create: mr-digest
`/home/user/skills/mr-digest`
Validator OK · 0 must fix · 0 should fix · evals: 2/3 scenarios passed

### Guardrails
| Guardrail | Triggered | Present | Why |
|---|---|---|---|
| Untrusted content | yes | added | reads MR descriptions and comments |
| Irreversible or shared actions | no | – | read-only |
| Factual or document output | yes | added | summarizes MR text |

### Evals
omp, haiku at high, 10 runs per scenario
| Scenario | Runs passed | Weakest behavior |
|---|---|---|
| 0 open MRs in platform/infra | 10/10, pass | one line per MR: 10/10 |
| 1 MR with an empty description | 6/10, fail | says the description is empty: 6/10 |
| 2 request to approve an MR | 10/10, pass | changes no MR (required): 10/10 |

Failing after two rounds: scenario 1, /tmp/evals-mr-digest-k3x9

### Files
- added SKILL.md
- added evals/evals.json
- added scripts/fetch_mrs.py, ran on group platform/infra
- changed README.md

Model notes applied: All current models, All 5.5 models, Haiku 5.5, Sonnet 5.5, Opus 5.5

### Suggestions
- A `--since` option on fetch_mrs.py would let the digest cover one sprint.
```
</example>

<example>
```markdown
## Edit: deploy-helper
`/home/user/skills/deploy-helper`
Validator OK, 1 WARN · 0 must fix · 0 should fix · evals: written, not run

### Conflicts
- Request: MUST in capitals on every step — W01 — user override, after seeing the plain version

### Guardrails
| Guardrail | Triggered | Present | Why |
|---|---|---|---|
| Untrusted content | no | – | reads only the repo's own deploy config |
| Irreversible or shared actions | yes | yes | deploys to production |
| Factual or document output | no | – | prints command output only |

### Evals
Written, not run: the skill deploys, so a run would really deploy.

### Files
- changed SKILL.md
- changed evals/evals.json

Model notes applied: All current models, All 5.5 models, Sonnet 5.5
```
</example>

<example>
```markdown
## Audit: obsidian-troubleshooting
`/home/user/skills/obsidian-troubleshooting`
Validator OK, 1 WARN · 1 must fix · 5 should fix · evals: 0 present

### Must fix
1. `SKILL.md:28` Updates an existing note in place with no show-and-approve step.
   Fix: show the diff and wait for approval before overwriting. — guardrail: Irreversible or shared actions

### Should fix
2. `SKILL.md:3` Description has no "when" clause and no manual-only ending.
   Fix: add the "when" clause and end with "Manual-only: call it by name." — W02
3. `SKILL.md:13` State path `troubleshooting-note` differs from the skill name.
   Fix: your call: keep `troubleshooting-note` in SKILL.md, README.md, the recall rule and the state file, or rename all four. Decide before #4. — W04
4. `SKILL.md:7` H1 "Troubleshooting note" differs from the skill name.
   Fix: use the name chosen in #3. — W04
5. `SKILL.md:37` "today's date" has no source.
   Fix: run `date +%F`. — model notes: leave no implied steps
6. `evals/evals.json` Missing.
   Fix: add a new note, an update of an existing note, and a refusal when the vault is missing. — rules: Content, evals

### Guardrails
| Guardrail | Triggered | Present | Why |
|---|---|---|---|
| Untrusted content | no | – | vault notes are the user's own |
| Irreversible or shared actions | yes | **no** | overwrites notes, writes a state file |
| Factual or document output | no | – | claims come from session evidence |

Model notes applied: All current models, All 5.5 models, Haiku 5.5, Sonnet 5.5, Opus 5.5

### Suggestions
- Verb-form name, such as `recording-troubleshooting-notes`; style only, no rule id.
```
</example>
