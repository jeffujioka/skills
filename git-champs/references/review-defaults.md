# Review Defaults

Defaults:

- Commit messages: committed automatically; no review unless the user asks.
- Pushes: automatic after pre-push checks; no review unless the user asks.
- Pull request title and description: always shown for approval before create or update.

Rules:

- User asks to review the commit message: draft it, show it, wait for approval or edits before `git commit`.
- Draft the pull request title and description, show them, wait for approval or edits before `gh pr create` or `gh pr edit`.
- Approval of one artifact never approves another. A reviewed commit message does not approve the pull request text, and an approved pull request does not approve a rewritten commit message the user asked to review.
- Pull request automation needs explicit authorization. If the user automates only the pull request, keep any commit review they asked for, and the reverse.
- Authorization ambiguous: stop and ask.

## Examples

Pull request automation:

- `Open the PR without showing me the text`
- `No need to ask me to review the PR description`
- `Do everything automatically`

Commit-message review:

- `Show me the commit message before committing`
- `Draft the commit message and let me review it first`

Pull request review (matches the default):

- `Show me the PR description before creating it`
- `Before updating the PR, send me the title and description`

Push review:

- `Show me what will be pushed before pushing`
- `Show me the push summary before pushing`

Without wording like this, use the defaults: commit and push automatically, pull request review first.
