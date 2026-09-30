---
name: github-cli
description: "Use when working with GitHub: pull requests, GitHub issues, Actions runs and CI logs, releases, repository info, code search, or any GitHub API call. Triggers on: PR, GitHub issue, CI, gh CLI, gh api."
---

# GitHub CLI

Use `gh` for GitHub work. Its subcommands cover everyday tasks, `gh api` reaches the rest of the REST and GraphQL API, and `--json`/`--jq` keep output small before it reaches the context.

## Quick reference

```bash
gh pr list                       # list PRs
gh pr view <number> --comments   # PR details and comments
gh pr diff <number>              # PR diff
gh pr checks <number>            # CI status for a PR
gh issue list                    # list issues
gh issue view <number>           # issue details
gh run list                      # CI runs
gh run view <id> --log-failed    # logs of failed jobs
gh search prs <query>            # search PRs (all of GitHub unless scoped, e.g. --repo)
gh search issues <query>
gh search code <query>
```

Full list by task: `references/commands.md`. For a flag or field not listed there, run `gh <command> --help`; `--json` with no field names prints the available fields.

## Output

- `--json <fields>` + `--jq <expr>`: return only the fields the task needs
- `-R owner/repo`: target a repository from any directory
- Lists return 30 items by default (`gh run list`: 20). Raise the cap with `--limit <n>`.
- `GH_PAGER=cat` or `| cat`: avoid the interactive pager

## Markdown bodies

Pass PR, issue and comment bodies through a quoted heredoc or a body file outside the repository:

```bash
gh pr create --title "Fix login redirect" --body-file - <<'EOF'
Backticks and `$VARS` are safe inside a quoted heredoc.
EOF
```

Inline `--body "..."` breaks on backticks and `$`, because the shell expands them first.

## API and other tasks

| Need | Command |
|---|---|
| Any REST endpoint | `gh api repos/{owner}/{repo}/... --paginate` |
| GraphQL | `gh api graphql -f query='...' -F number=1` |
| Workflow artifacts | `gh run download <run-id> -D <dir>` |
| Copilot coding agent | `gh agent-task create` (preview) |

`gh api` has no `-R` and no `--json`. It fills `{owner}`, `{repo}` and `{branch}` from the current repository (or `GH_REPO`); filter its output with `--jq`. Use `-f` for string fields and `-F` for typed values and GraphQL variables.
