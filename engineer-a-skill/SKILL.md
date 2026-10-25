---
name: engineer-a-skill
description: "Create, edit or audit an agent skill: batched intake, scaffold, write, validate with a script. Call by hand with `@engineer-a-skill`."
disable-model-invocation: true
---

# engineer-a-skill

Builds, edits or audits one skill in a directory the user picks. Paths below are relative to this skill dir. Scripts run with `python3`. Pass `<target-dir>` and `<skill-dir>` as absolute paths.

Read before step 3: [rules](references/rules.md), [model notes](references/model-notes.md), [guardrails](references/guardrails.md).

Modes:
- Create: steps 1-7.
- Edit or audit: ask for the skill dir, read it, skip step 2, apply the user's change, then steps 4-7.

## 1. Intake

Look up facts yourself: target dir contents, sibling skills, existing scripts, README presence. Ask only what is still missing, one message, max 7 questions:

1. Purpose and the one-line "when".
2. Auto or manual-only? Undecided: manual-only if the skill has side effects, auto if it is read-only reference.
3. Inputs and outputs. Fixed output format means template plus example.
4. Per step: high, medium or low freedom (see rules).
5. Scripts needed? Language: the user's pick, else the one common in the target repo.
6. Reads untrusted content, or takes irreversible or shared actions?
7. Target dir. Always ask: no default, no guessing.

*Done when:* all seven answered.

## 2. Scaffold

```bash
python3 scripts/scaffold.py <target-dir> <name> --invocation <auto|manual> --description "<text>"
```

Name: lowercase, digits, hyphens; verb or gerund form. Description: third person, what plus when. Manual-only ends with "Call by hand with `@<name>`". Auto lists trigger terms. The script fills `templates/SKILL.md.tmpl` and `templates/frontmatter-auto.txt` or `templates/frontmatter-manual.txt`. It refuses an existing name.

## 3. Write

Fill `SKILL.md` and add files only when needed. Apply the rules and model notes. Add each guardrail whose trigger step 1 found.

- Fragments, imperative verbs, no filler. Keep negations, numbers, paths, exact strings.
- One-clause reason on every non-obvious rule.
- Fixed steps get exact commands. Longer than 3 lines or any loop, conditional or `&&`: write a script in `scripts/`, any shippable language.
- Name each script with its call line and say run or see.
- Detail beyond about 300 lines goes in `references/`, linked from `SKILL.md`, one level deep.

## 4. Validate

```bash
python3 scripts/validate.py <skill-dir>
```

Fix every FAIL and re-run until exit 0. Fix each WARN or keep it with a one-line reason in the report.

## 5. Checklist

Read the skill once and confirm:
- A reader with no context could follow every step.
- One term per concept.
- No fact that expires. Model-specific notes name the model family they apply to.
- Every non-obvious rule has its reason.
- Nothing Claude already knows.

Fix, then re-run step 4.

## 6. README

Target dir has a `README.md`: read it. Entry for the skill exists: update it to match. Otherwise add one mirroring the existing format. No `README.md`: skip. Do not commit, push or install.

## 7. Report

Print exactly:

```text
mode: <create | edit | audit>
path: <skill-dir>
findings: <none | one line each: file:line and problem>
validate: <OK | OK with warnings: ids and reasons>
checklist: <pass | failed items>
evals: skipped
readme: <added | updated | none found>
```
