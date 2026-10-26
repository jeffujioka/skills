---
name: github-pr-create
description: "Create a GitHub pull request with gh from the current branch: find the repo's PR template, fill it, show the draft, create only after approval. Use when opening a GitHub PR, creating a pull request, or the user asks for a GitHub PR on the current branch."
---

# GitHub PR Create

## Overview

Creates one GitHub PR for the current branch. Two hard rules: nothing is published before the user approves the draft, and nothing is pushed. The user commits and pushes; this skill checks that the branch is pushed and stops if not.

GitHub and `gh` only. Scripts live in `scripts/`, the fallback template in `templates/`; paths below are relative to this skill dir. Run the scripts with the target repo as working directory and the skill dir as the script path (`bash <skill-dir>/scripts/<name>.sh`).

Steps 1 and 2 run independent, read-only scripts: call both in the same step, before reading either output.

## Steps

### 1. Find the template

Run `bash scripts/find-template.sh`.

- Prints `none`: the repo has no PR template. Use `templates/fallback.md`.
- Prints files under `.github/PULL_REQUEST_TEMPLATE/`: several named templates with no default convention. Ask the user which one.
- Prints a single file marked `(Default)` (`.github/PULL_REQUEST_TEMPLATE.md`, root, or `docs/`): use it.

Read the chosen template in full with the read tool.

*Done when:* you hold the full template text and know which one it is.

### 2. Gather context

Run `bash scripts/branch-context.sh` (add the target branch as argument if the user named one). It prints the branch, the target, the commit messages since the target, Jira key candidates, and the diff stat.

If it stops with a missing `origin/<target>`, tell the user to run `git fetch origin <target>`. Do not fetch yourself.

*Done when:* you have read every commit message on the branch.

### 3. Fill the template

Fill only what the commits, the diff, or the branch name support. Leave everything else the way the template has it.

- **Repo template:** keep its structure exactly: headings, `<details>` blocks, checkboxes, HTML comments. Fill the prose parts and leave all checkboxes unchecked.
- **Fallback template:** `## Why` is prose: the problem or motivation, from commit bodies. `## What` is terse bullets of the change, no code snippets unless essential. `## Verification` is how it was tested or can be verified, with no test statistics (say "`npm test` passes", not "2431 of 2431"); state any model-call cost as a percentage of the eval budget, never dollars or token counts; delete it for docs-only changes. Delete `## Notes` unless there is something worth flagging — breaking changes, caveats, or what is not yet verified; do not keep it empty just to fill it. Delete `## Breaking change` unless a commit has `!` after its type or a `BREAKING CHANGE:` footer. Keep `## Screenshots` only for UI changes and mark it as a gap; otherwise delete it. Use `## Related issues` for issue or Jira keys from the branch name or commit footers (`Fixes #123`, `Issue-ID:`).
- **Gaps:** where the source does not support a part, leave a visible `TODO: <what is missing>` in the description. Never invent issue numbers, checkboxes, or PR links. Examples of typical gaps: a project checkbox, a definition ticket, related PRs, a motivation nothing in the commits states.
- **Issue keys:** if there are several candidates or none, do not pick one. Make it a gap.

<example>
Commits: `fix(auth): reject expired refresh tokens` plus a body explaining the prior check used `<=` instead of `<`. No issue key in branch name or commits.

## Why

The refresh-token check accepted tokens at their exact expiry instant, letting one extra request through.

## What

- Change the expiry comparison from `<=` to `<` in the refresh-token check.

## Verification

`go test ./auth/...` passes.

## Related issues

TODO: no issue or Jira key found in the branch name or commits.
</example>

*Done when:* every section is either filled from a source or holds a `TODO:` that you will list in step 4.

### 4. Draft, then ask

Run `bash scripts/check-pushed.sh` first. It is read-only. If it fails, stop and tell the user the branch is not pushed; do not continue to the draft.

Show the user, in this order:

1. **Title:** the subject of the branch's main commit, unchanged, in Conventional Commits form. The main commit is the one whose subject states the whole change; with one commit, that commit.
2. **Base branch:** from step 2.
3. **Description:** the full filled text, exactly what would be created.
4. **Gaps:** a list of every `TODO:` the user must fill before or after creation.

Then ask for approval. Accept edits and show the changed draft again. Run nothing that creates or publishes until the user says yes in so many words.

*Done when:* the user has approved the exact title, base, and description.

### 5. Create

1. Write the approved description with the write tool to a file outside the repo, e.g. `/tmp/pr-description-<branch>.md`, with `/` in the branch name replaced by `-`.
2. Run:

   ```sh
   bash scripts/create-pr.sh "<approved title>" /tmp/pr-description-<branch>.md "<approved base>"
   ```

The script checks that the branch is pushed and that no tracked file has uncommitted changes, then runs `gh pr create` with `--title`, `--body-file`, `--head`, `--assignee @me`, and `--base` (omitted if the user did not name one, letting `gh` use the repo default).

*Done when:* the script prints `PR URL: <url>`. Give the user that URL and the gaps still open.

If the script fails, report the error text and stop. Do not retry on your own: `gh` may have created the PR before failing.

## Rules

- Reading templates, gathering context, and drafting are local and reversible; proceed without asking. Creating the PR is visible to others: never do it before the user approves the draft.
- Never push and never commit. A branch that is not pushed means: stop and tell the user.
- If `create-pr.sh` fails, report the error text and stop. Never bypass `check-pushed.sh` or retry with a forcing flag: `gh` may have already created the PR before failing.
- The description is normal prose, following the template structure. No emoji, no decorative formatting.
- Do not invent content the sources do not support. A `TODO:` is better than a guess.
