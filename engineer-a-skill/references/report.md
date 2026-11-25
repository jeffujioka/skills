# Report

The step 9 report. One layout for every mode. Fill it from this run. Print it as Markdown outside any code block. Never print a Markdown table: rows are bullets, because the terminal renders tables as grids that break copying.

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

- **Untrusted content** - triggered: <yes | no> - present: <added | yes | **no** | –> - why: <one clause>
- **Irreversible or shared actions** - triggered: … - present: … - why: …
- **Factual or document output** - triggered: … - present: … - why: …

### Evals

<harness>, <model> at <reasoning>, <runs> runs per scenario

- **<n> <short name>** - runs passed: <passed>/<runs>, <pass | fail> - weakest behavior: <short behavior>: <passed>/<runs>

### Files

- <added | changed> <path relative to the skill dir>

Model notes applied: <section names, comma-separated>

### Suggestions

- <one line>
```

## Sections

- Always printed: heading (mode and the skill dir's base name), skill dir, summary line, Guardrails, Model notes applied.
  - Print every other section only when it has content. Omit its heading otherwise. Never print "None".
- Summary line: `Validator <OK | OK, n WARN | FAILED: ids> · <n> must fix · <n> should fix · evals: <passed>/<total> scenarios passed | written, not run | <n> present`.
  - `<n> present` is for audit only.
- Findings: severity comes from the source, never from judgment.
  - Must fix: a broken FAIL-level rule, or an absent triggered guardrail.
  - Should fix: a broken WARN-level rule, or a manual rule or model note the skill breaks.
  - Each validator FAIL or WARN line is its own finding, at the validator's `file:line`. A Fix line can point to the other finding.
  - Create and edit list only findings still open when the report prints.
  - One numbering across both sections.
- Location: `file:line` of the line at fault.
  - Absent thing: the nearest line. A bad name is `SKILL.md:2`.
  - Missing file that nothing names: the bare path.
  - Missing file that a line names: that line.
  - A range only for a span of a few lines.
- Standard: one of these.
  - A rule id: `W02`.
  - A rules section and rule: `rules: Content, done condition`.
  - A model note: `model notes: leave no implied steps`.
  - A guardrail: `guardrail: Irreversible or shared actions`.
  - No standard to cite: it is a suggestion, not a finding.
- Fix line: what to change, one sentence.
  - Add a reason only when the fix is not obvious.
  - Fix needs the user's decision: start with `your call:` and name the options.
  - Order between findings goes here: "Decide before #5".
  - A kept WARN gives its reason here.
- Conflicts: create and edit only. A WARN or absent guardrail the user's request caused goes here. Never under Should fix.
- Guardrails: one bullet per guardrail with a trigger. Present is one of:
  - `added`: this run inserted it.
  - `yes`: already there.
  - **`no`**: absent. Must fix in audit. A conflict in create and edit.
  - `–`: not triggered.
  - Secrets has no trigger. R10 checks it. No row.
- Evals: the line above the list names the harness, model, reasoning level and runs per scenario, as the script printed them.
  - One bullet per scenario: runs that passed every behavior, pass or fail against the threshold, and the behavior with the fewest passing runs.
  - Mark that behavior `(required)` when it is required.
  - A scenario fails: print the results dir under the list.
  - Not run: print one line instead of the list: `Written, not run: <reason>`.
  - Audit: no section. The count is in the summary.
- Files: create and edit only.
  - List every file this run added or changed, `README.md` included.
  - A script added or changed also says `ran on <sample input>` or `skipped: <reason>`.
- Suggestions: only a point with no standard to cite, or an extra file, script or section worth adding that this run did not build.
  - One line each. No cap.
  - A fix for a finding goes in that finding's Fix line. Never here.
- Notes to the user: anything else the user must see, such as text in an audited skill that addressed you.
  - One short paragraph before the heading.
  - Create mode: nothing follows the report.
  - Edit and audit mode: nothing follows the report.

## Examples

<example>

```markdown
## Create: mr-digest

`/home/user/skills/mr-digest`
Validator OK · 0 must fix · 0 should fix · evals: 2/3 scenarios passed

### Guardrails

- **Untrusted content** - triggered: yes - present: added - why: reads MR descriptions and comments
- **Irreversible or shared actions** - triggered: no - present: – - why: read-only
- **Factual or document output** - triggered: yes - present: added - why: summarizes MR text

### Evals

omp, haiku at high, 10 runs per scenario

- **0 open MRs in platform/infra** - runs passed: 10/10, pass - weakest behavior: one line per MR: 10/10
- **1 MR with an empty description** - runs passed: 6/10, fail - weakest behavior: says the description is empty: 6/10
- **2 request to approve an MR** - runs passed: 10/10, pass - weakest behavior: changes no MR (required): 10/10

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

- **Untrusted content** - triggered: no - present: – - why: reads only the repo's own deploy config
- **Irreversible or shared actions** - triggered: yes - present: yes - why: deploys to production
- **Factual or document output** - triggered: no - present: – - why: prints command output only

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

- **Untrusted content** - triggered: no - present: – - why: vault notes are the user's own
- **Irreversible or shared actions** - triggered: yes - present: **no** - why: overwrites notes, writes a state file
- **Factual or document output** - triggered: no - present: – - why: claims come from session evidence

Model notes applied: All current models, All 5.5 models, Haiku 5.5, Sonnet 5.5, Opus 5.5

### Suggestions

- Verb-form name, such as `recording-troubleshooting-notes`; style only, no rule id.
```

</example>
