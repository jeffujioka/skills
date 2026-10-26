#!/usr/bin/env bash
# Creates the GitHub PR for the current branch with gh, using an approved
# description file. Stops unless the branch is pushed. Never pushes.
# usage: create-pr.sh <title> <description-file> [base-branch]
set -euo pipefail

usage="usage: create-pr.sh <title> <description-file> [base-branch]"
title=${1:?$usage}
desc=${2:?$usage}
base=${3:-}

here=$(cd "$(dirname "$0")" && pwd)

if [ ! -f "$desc" ]; then
  echo "description file not found: $desc" >&2
  exit 1
fi

bash "$here/check-pushed.sh"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "uncommitted changes to tracked files are not in the PR. Commit first, then rerun." >&2
  exit 1
fi

branch=$(git branch --show-current)

args=(
  --title "$title"
  --body-file "$desc"
  --head "$branch"
  --assignee "@me"
)
if [ -n "$base" ]; then
  args+=(--base "$base")
fi

echo "creating PR: $branch -> ${base:-<gh default base>}"

if ! out=$(gh pr create "${args[@]}" 2>&1); then
  printf '%s\n' "$out" >&2
  exit 1
fi

printf '%s\n' "$out"
url=$(printf '%s\n' "$out" | grep -oE 'https://github\.com/[^ ]+/pull/[0-9]+' | tail -n 1 || true)
echo "PR URL: ${url:-not found in gh output}"
