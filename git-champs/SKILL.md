---
name: git-champs
description: "Git workflow for repositories on github.com: inspection, Conventional Commits, branches, rebases, pushes, repository creation and the hand-off to pull request creation. Use when committing, branching, rebasing, pushing, creating a repository (git init, gh repo create) or preparing a pull request for a repo whose target remote is github.com."
---

# Git Champs

## Scope

Applies only when the target remote is `github.com`, the remote a push or pull request goes to. Read the host from `git remote -v`, never from the repo name. Target remote on another host: say this skill does not cover it and stop. No remote yet: see [Repository Creation](references/repo-creation.md).

Use `git` for local work and `gh` for platform actions.

## Core Rules

1. Inspect before staging, committing, rebasing, pushing or handing off a pull request (see Inspect First).
2. Every commit follows Conventional Commits and has a body.
3. Keep history linear: rebase and fast-forward.
4. Never claim a validation that did not run.
5. Changes go through a feature branch and a pull request unless the user explicitly authorizes direct integration.
6. Never push to `main` or `master` without explicit authorization. Never force-push them.
7. Commit automatically once the diff is inspected and the message follows these rules. If the user asks to review the commit message, show it and wait.
8. Push automatically after pre-push checks pass. If the user asks to review before pushing, show the summary and wait.
9. Pull request text is reviewed by the user before it is published; silence does not waive this. See [Review Defaults](references/review-defaults.md).
10. No `Co-authored-by` trailer for any AI tool; trailers name human co-authors only.

## Language

- Committed or published text is English: commit messages, pull request title and description, files.
- Everything said to the user follows the session language: questions, drafts shown for review, push summaries, reports.

## Inspect First

Before staging, committing, rebasing, pushing or opening a pull request: check `git status`, the current branch and `git remote -v`. Read the diff before writing the commit message. Check recent history when branch context matters.

*Done when:* the target remote host, the branch and the full diff are known.

## Conventional Commits

```text
<type>[optional scope]: <description>

<body>

[footer(s)]
```

| Element | Max length |
|---|---|
| Title (first line) | 72 characters |
| Body lines | 75 characters |

Title over 72 characters: rewrite it shorter.

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

- Imperative mood: `add`, `fix`, `update`.
- Base the message on the actual diff; no vague titles like `misc updates`.
- Scope is the nearest meaningful context, never the folder path. Good: `feat(auth)`. Bad: `feat(src/modules/auth)`.
- Breaking change: `!` after the type (`feat!: remove deprecated endpoint`) or a `BREAKING CHANGE:` footer.
- No `Issue-ID:` footer.

## Commit Message Content

The subject serves changelog readers: what changed, in functional terms. The body serves archaeology: why, or what a reader cannot see at a glance.

| Information | Location |
|---|---|
| What changed (functionality) | Subject |
| Why it changed, key changes | Body |
| How it works technically | Code comments |
| Broad context, validation | Pull request description |

Every commit has a body: sharp and concise, never a restatement of the subject. Nothing non-obvious to record: one or two bullets with the key change. Breaking changes, migrations, security-relevant changes, or subtle trade-offs earn more depth; size alone does not. Squash commits summarize the functional change, not the development steps.

<example>
```text
fix(readme): correct install URL

- install URL pointed at the old repository path
```
</example>

<example>
```text
feat(cleanup): add glob-aware --exclude flag

- replaces hardcoded HARD_EXCLUDES with user-provided patterns
- guards ~/.agents/skills from self-deletion
- rejects ambiguous ~user patterns instead of silent no-match
```
</example>

<example>
```text
feat!: replace session-token storage with encrypted-at-rest model

Existing sessions are invalidated on deploy; users must re-authenticate.

Chose encrypt-at-rest over token rotation because rotation needs a
30-day parallel-run window the compliance deadline does not allow.
```
</example>

Too verbose: implementation detail, test counts and the TDD history in the body. Those belong in code comments or the pull request description.

## Staging

One logical change per commit. Stage named paths (`git add path/to/file`) or hunks (`git add -p`), never everything blindly.

## Safety Rules

- No secrets, credentials, private keys or personal data in commits or commit messages.
- Do not change Git config unless asked.
- No destructive commands (`git reset --hard`, `git clean`, branch deletion) without an explicit request.
- Force-push only with explicit authorization, only on feature branches, always `--force-with-lease`.
- Do not skip hooks with `--no-verify` unless asked. Hook fails: fix it and make a new commit; amend only when asked.

## Pull Requests

Push the feature branch first (see [Push and Pull Requests](references/push-and-pull-requests.md)), then create the pull request with the `gh-pr-create` skill. It finds the repo template, drafts, and creates only after approval. Not installed: draft the title and description, show them, and run `gh pr create` only after approval. Updates use `gh pr edit`, with the same approval gate.

## References

- [Review Defaults](references/review-defaults.md): commit, push and pull request review gates.
- [Repository Creation](references/repo-creation.md): `git init`, `gh repo create`, first push.
- [Push and Pull Requests](references/push-and-pull-requests.md): sync, pre-push checks, protected branches, hotfixes.
