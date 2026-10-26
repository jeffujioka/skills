#!/usr/bin/env bash
# Prints what an MR description is built from: branch, target, commit messages
# since the target, Jira key candidates, diff stat. Read-only; never fetches.
# usage: branch-context.sh [target-branch]
set -euo pipefail

branch=$(git branch --show-current)
if [ -z "$branch" ]; then
  echo "detached HEAD: checkout the source branch" >&2
  exit 1
fi

target=${1:-}
if [ -z "$target" ]; then
  ref=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD || true)
  target=${ref#origin/}
fi
if [ -z "$target" ]; then
  echo "no target given and origin/HEAD unset: pass the target branch" >&2
  exit 1
fi

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

keys=$({ echo "$branch"; git log --no-merges --format=%B "$base..HEAD"; } \
  | grep -oE '[A-Z][A-Z0-9]+-[0-9]+' | sort -u || true)
if [ -n "$keys" ]; then
  echo "jira key candidates (branch name and commit messages):"
  echo "$keys" | sed 's/^/  /'
else
  echo "jira key candidates: none"
fi
echo

echo "commit messages ($base..HEAD, oldest first):"
git log --reverse --no-merges --format='--- %h%n%B' "$base..HEAD"
echo "diff stat ($base...HEAD):"
git diff --stat "$base...HEAD"
