#!/usr/bin/env bash
# Lists open PRs assigned to me in the repo given as $1.
set -euo pipefail
gh pr list --repo "$1" --assignee @me --state open --json number,title,url --jq '.[] | "#\(.number) \(.title) \(.url)"'
