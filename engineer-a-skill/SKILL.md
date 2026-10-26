---
name: engineer-a-skill
description: "Create, edit or audit an agent skill against binding authoring rules, model notes and guardrails: batched intake, scaffold, write, validate with a script. Call by hand with `@engineer-a-skill`."
disable-model-invocation: true
---

# engineer-a-skill

Builds, edits or audits one skill in a directory the user picks. Paths below are relative to this skill dir. Scripts run with `python3`. Pass `<target-dir>` and `<skill-dir>` as absolute paths.

## Core: the three references

These files define a correct skill. Every step below exists only to apply them.

- [rules](references/rules.md): frontmatter, structure, content, embedded commands, safety. Each checked rule has an id.
- [model notes](references/model-notes.md): how the 5.5 models read skill text.
- [guardrails](references/guardrails.md): snippets a skill must carry when their trigger applies.

They are binding, with no exceptions:

- Read all three in full before step 1, in every mode. After a context reset, read them again; never work from memory.
- They override the steps below, the user's style preferences and your own habits. A step that seems to conflict with a reference: follow the reference and name the conflict in the report.
- A user request that would break a rule, note or guardrail: do not apply it. Name the rule id or section, say why it exists, and offer a version that complies.
- Every rule applies. Every note under "All 5.5 models" applies. The per-model notes apply for each model the skill may run on; unknown means all three.
- Every guardrail whose trigger matches goes in. None whose trigger does not match.

The steps cite the reference sections they apply.

Modes:
- Create: steps 1-7.
- Edit or audit: ask for the skill dir, read it, skip step 2, apply the user's change, then steps 4-7.

## 1. Intake

If the target dir is not given, ask for it first. Then look up facts yourself: target dir contents, sibling skills, existing scripts, README presence. Ask only what is still missing, one message, max 7 questions:

1. Purpose and the one-line "when".
2. Auto or manual-only? (rules: Definitions.) Undecided: manual-only if the skill has side effects, auto if it is read-only reference.
3. Inputs and outputs. Fixed output format means template plus example.
4. Per step: high, medium or low freedom (rules: Definitions).
5. Scripts needed? Language: the user's pick, else the one common in the target repo.
6. Reads untrusted content, states facts from documents, or takes irreversible or shared actions? The answers pick the guardrails.
7. Target dir, if not already given.

*Done when:* all seven answered and the triggered guardrails are listed.

## 2. Scaffold

```bash
python3 scripts/scaffold.py <target-dir> <name> --invocation <auto|manual> --description "<text>"
```

Name and description follow rules: Frontmatter (R01, R02, W02). Manual-only ends with "Call by hand with `@<name>`"; auto lists trigger terms. The script fills `templates/SKILL.md.tmpl` and `templates/frontmatter-auto.txt` or `templates/frontmatter-manual.txt`. It refuses an existing name.

*Done when:* the script prints `created <path>/SKILL.md`.

## 3. Write

Fill `SKILL.md` and add files only when needed. Apply, line by line:

- rules: Structure, Content, Embedded commands, Safety.
- model notes: "All 5.5 models" plus the per-model sections that apply.
- guardrails: each triggered snippet, copied, with nouns adapted to the skill.

Detail beyond about 300 lines goes in `references/`, linked from `SKILL.md`, one level deep.

*Done when:* every step of the new skill is written and each triggered guardrail is in place.

## 4. Validate

```bash
python3 scripts/validate.py <skill-dir>
```

Covers the rules with ids. Fix every FAIL and re-run until exit 0. Fix each WARN or keep it with a one-line reason in the report, as rules allows.

*Done when:* exit 0.

## 5. Reference audit

The validator cannot check everything. Read the skill against each reference, line by line:

- rules: every manual rule.
- model notes: every note that applies.
- guardrails: each triggered snippet present; prompt-leak hardening absent.

Record each miss as file:line plus the rule or note it breaks. Fix, then re-run step 4.

*Done when:* zero misses.

## 6. README

Target dir has a `README.md`: read it. Entry for the skill exists: update it to match. Otherwise add one mirroring the existing format. No `README.md`: skip. Do not commit, push or install.

*Done when:* entry added or updated, or no `README.md` found.

## 7. Report

Print exactly:

```text
mode: <create | edit | audit>
path: <skill-dir>
findings: <none | one line each: file:line and problem>
validate: <OK | OK with warnings: ids and reasons>
rules: <pass | misses>
model notes: <sections applied>
guardrails: <added: names | none triggered>
conflicts: <none | step or request, and the reference that won>
evals: skipped
readme: <added | updated | none found>
```
