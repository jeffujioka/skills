---
name: gh-over-mcp
description: "Use when interacting with GitHub — pull requests, issues, workflow runs, repository info, searches, commits, branches, or any GitHub API call. Triggers on: PRs, issues, CI, GitHub Actions, repo browsing, GitHub search, gh CLI."
---

# GitHub CLI Over MCP

Use `gh` CLI instead of GitHub MCP server tools for all GitHub operations. Faster, cleaner output, and pipes naturally with other shell commands.

## When to Use

- Any GitHub operation: PRs, issues, CI, searches, repo info
- Even when MCP tools are available — reach for `gh` first

## When NOT to Use

- `gh` genuinely can't accomplish the task — read `references/mcp-fallback.md` for examples

## Command Mapping

For the full MCP-to-gh equivalents table, read `references/command-mapping.md`.

```bash
gh pr list                     # list PRs
gh pr view <number>            # view PR details
gh pr diff <number>            # view PR diff
gh pr checks <number>          # CI status for a PR
gh issue list                  # list issues
gh issue view <number>         # view issue details
gh run list                    # list CI runs
gh run view <id> --log-failed  # failed CI logs
gh search prs <query>          # search PRs
gh search issues <query>       # search issues
gh search code <query>         # search code
```

## Output Tips

- `--no-pager` or `| cat` to avoid interactive pagers
- `--json <fields>` + `--jq <expr>` for structured output
- `-R owner/repo` to target a specific repo
- `--limit <n>` to control result count
