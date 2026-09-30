# gh Commands by Task

Body files (`--body-file`): write them outside the repository, or pass `-` and a quoted heredoc.

## Pull requests

| Task | Command |
|---|---|
| List | `gh pr list` |
| Details | `gh pr view <number>` |
| Diff | `gh pr diff <number>` |
| Changed files | `gh pr diff <number> --name-only` |
| Comments | `gh pr view <number> --comments` |
| Reviews | `gh pr view <number> --json reviews` |
| CI checks | `gh pr checks <number>` |
| Search | `gh search prs <query>` |
| Create | `gh pr create --title "..." --body-file - <<'EOF' ... EOF` |
| Review | `gh pr review <number> --approve \| --request-changes \| --comment --body-file review.md` |
| Merge | `gh pr merge <number> --squash \| --merge \| --rebase` |

## Issues

| Task | Command |
|---|---|
| List | `gh issue list` |
| Details | `gh issue view <number>` |
| Comments | `gh issue view <number> --comments` |
| Search | `gh search issues <query>` |
| Create | `gh issue create --title "..." --body-file body.md` |
| Comment | `gh issue comment <number> --body-file comment.md` |

## CI and workflow runs

| Task | Command |
|---|---|
| Workflows | `gh workflow list` |
| Runs | `gh run list` |
| Run details | `gh run view <run-id>` |
| Logs | `gh run view <run-id> --log` or `--log-failed` |
| Re-run failed jobs | `gh run rerun <run-id> --failed` |
| Artifacts | `gh run download <run-id>` |

## Repository and code

| Task | Command |
|---|---|
| File contents | `gh api repos/{owner}/{repo}/contents/{path}`, or read the local checkout |
| Branches | `gh api repos/{owner}/{repo}/branches`, or `git branch -r` |
| Commits | `git log` locally, or `gh api repos/{owner}/{repo}/commits` |
| One commit | `git show <sha>` locally, or `gh api repos/{owner}/{repo}/commits/<sha>` |
| Code search | `gh search code <query>` |
| Repository search | `gh search repos <query>` |

## Flags

| Flag | Purpose |
|---|---|
| `--json <fields>` | Structured JSON output |
| `--jq <expression>` | Filter JSON output |
| `-R owner/repo` | Target a repository from any directory |
| `--limit <n>` | Bound result counts |
| `--web` | Open in the browser |
