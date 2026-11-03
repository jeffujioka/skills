# Review Defaults

Defaults:

- Commit messages: committed automatically; no review unless the user asks.
- Pushes: the push summary is shown for approval before every push.
- Repository creation: the `gh repo create` command, with owner and visibility, is shown for approval first.
- Pull request title and description: shown for approval before create or update.

Pushes, repository creation and pull requests are visible to others, so their approval is never skipped, even when the user asks for full automation.

Rules:

- User asks to review the commit message: draft it, show it, wait for approval or edits before `git commit`.
- Draft the pull request title and description, show them, wait for approval or edits before `gh pr create` or `gh pr edit`.
- Approval of one artifact never approves another. An approved commit message does not approve the push, and an approved push does not approve the pull request text.
- Approval ambiguous: stop and ask.

## Push Summary

Show this (explanations in the session language) and wait:

```text
Branch:  feature/add-login  ->  origin/feature/add-login
Commits: 2
  a1b2c3d feat(auth): add JWT token validation
  e4f5g6h test(auth): add unit tests for token expiry
Diff stat:
  src/auth.ts  | +45 -3
  test/auth.ts | +80

Push? [y/N]
```

## Examples

Commit-message review:

- `Show me the commit message before committing`
- `Draft the commit message and let me review it first`

Commit without review (matches the default):

- `Commit it directly`
- `If the commit message is good, just commit`

A request such as `Do everything automatically` or `Open the PR without showing me the text` still gets the push summary and the pull request draft; say why: both are visible to others.
