#!/usr/bin/env bash
# Prints what a PR description is built from: branch, target, commit messages
# since the target, issue references (only when present), diff stat.
# Read-only; never fetches.
# usage: branch-context.sh [target-branch]
set -euo pipefail

branch=$(git branch --show-current)
if [ -z "$branch" ]; then
  echo "detached HEAD: checkout the source branch" >&2
  exit 1
fi

here=$(cd "$(dirname "$0")" && pwd)
target=$(bash "$here/resolve-base.sh" "${1:-}")

base="origin/$target"
if ! git rev-parse --verify --quiet "$base" >/dev/null; then
  echo "$base not found locally: run 'git fetch origin $target' and rerun" >&2
  exit 1
fi

count=$(git rev-list --count --no-merges "$base..HEAD")
if [ "$count" -eq 0 ]; then
  echo "no commits on $branch ahead of $base" >&2
  exit 1
fi

echo "branch: $branch"
echo "target: $target"
echo "commits ahead: $count"
echo

refs=$({ echo "$branch"; git log --no-merges --format=%B "$base..HEAD"; } \
  | grep -oE '(^|[[:space:](])#[0-9]+|[A-Z][A-Z0-9]+-[0-9]+' | sed -E 's/^[[:space:](]+//' | sort -u || true)
if [ -n "$refs" ]; then
  echo "issue references (branch name and commit messages):"
  echo "$refs" | sed 's/^/  /'
  echo
fi

echo "commit messages ($base..HEAD, oldest first):"
git log --reverse --no-merges --format='--- %h%n%B' "$base..HEAD"
echo "diff stat ($base...HEAD):"
git diff --stat "$base...HEAD"
