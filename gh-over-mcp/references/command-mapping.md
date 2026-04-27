# Full MCP-to-gh Command Mapping

## Pull Requests

| Instead of MCP | Use gh |
|---|---|
| `list_pull_requests` | `gh pr list` |
| `pull_request_read` (get) | `gh pr view <number>` |
| `pull_request_read` (get_diff) | `gh pr diff <number>` |
| `pull_request_read` (get_files) | `gh pr diff <number> --stat` |
| `pull_request_read` (get_comments) | `gh pr view <number> --comments` |
| `pull_request_read` (get_reviews) | `gh pr view <number> --json reviews` |
| `pull_request_read` (get_check_runs) | `gh pr checks <number>` |
| `search_pull_requests` | `gh search prs <query>` |

## Issues

| Instead of MCP | Use gh |
|---|---|
| `list_issues` | `gh issue list` |
| `issue_read` (get) | `gh issue view <number>` |
| `issue_read` (get_comments) | `gh issue view <number> --comments` |
| `search_issues` | `gh search issues <query>` |

## Workflow Runs / CI

| Instead of MCP | Use gh |
|---|---|
| `actions_list` (list_workflows) | `gh workflow list` |
| `actions_list` (list_workflow_runs) | `gh run list` |
| `actions_get` (get_workflow_run) | `gh run view <run-id>` |
| `get_job_logs` | `gh run view <run-id> --log` or `--log-failed` |

## Repository & Code

| Instead of MCP | Use gh |
|---|---|
| `get_file_contents` | `gh api repos/{owner}/{repo}/contents/{path}` or `cat` for local |
| `list_branches` | `gh api repos/{owner}/{repo}/branches` or `git branch -r` |
| `list_commits` | `git log` (local) or `gh api repos/{owner}/{repo}/commits` |
| `get_commit` | `git show <sha>` (local) or `gh api repos/{owner}/{repo}/commits/<sha>` |
| `search_code` | `gh search code <query>` |
| `search_repositories` | `gh search repos <query>` |

## Useful gh Flags

| Flag | Purpose |
|---|---|
| `--json <fields>` | Structured JSON output for scripting |
| `--jq <expression>` | Filter JSON output directly |
| `-R owner/repo` | Target a specific repo without being in its directory |
| `--limit <n>` | Control result count |
| `--web` | Open in browser instead of terminal |
