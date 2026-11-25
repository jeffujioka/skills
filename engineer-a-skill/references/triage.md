# Triage

Gives each instruction of a skill a verdict. Keeps `SKILL.md` to what the model cannot work out and each run needs.

## Scope

- Create and Edit: triage each line you add or change, before you write it. Leave other lines as they are.
- Audit: triage every instruction in `SKILL.md` and in each reference. Report only.
- Text the user supplied word for word stays. List it under Suggestions when it would be a `remove`.

## Questions

Take each instruction (one bullet, sentence or rule). Apply in order:

1. Can the model work this out from the user's request, the repo, tool output, `<tool> --help` or general knowledge of the tool? Verdict `remove`.
   - Typical hits: a restated CLI behavior, a defined term the model knows, a spelled-out flag, background, motivation.
   - Unsure: verdict `keep`. Report it as "consider removing" under Should fix.
2. Does it apply to every run of the skill? Verdict `keep`.
   - A line that guards a silent failure, an irreversible or shared action, or a fixed output format counts as every run.
3. Only some runs, and a wrong guess costs real work or the model cannot discover the answer? Verdict `move`.
   - The full text goes to a file under `references/`. `SKILL.md` gets a pointer `<when>: <path>`.
4. Logic a CLI lacks that must run the same each time? Verdict `script candidate`.
   - Another skill's job? Verdict `split candidate`.
5. None of the above: verdict `remove`.

## Evidence

- Cite for each verdict: `file:line`, command output, or the eval behavior the line protects.
- A `remove` cites what lets the model derive the line.
- A `keep` on a risky step needs no citation beyond the guarded action.
- Disputed line: run `run_evals.py <skill-dir> --baseline` and compare. Behaviors that pass without the line show it is derivable. This run is optional and slow.

## Findings

- `remove` and `move` become Should fix findings: `rules: Content, triage`.
- `script candidate` becomes a finding under `rules: Embedded commands`.
- `split candidate` goes under Suggestions.
- The Fix line starts with the verdict.
