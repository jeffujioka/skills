#!/usr/bin/env bash
# Reports whether the current branch has anything to PR. Read-only; never fetches.
# Exit 0: not on the base branch and at least one commit ahead of origin/<base>.
# Exit 4: nothing to PR (reason: on-base-branch or no-commits-ahead).
# Exit 1: cannot tell (detached HEAD, base unresolved, origin/<base> missing).
# 4 differs from check-pushed.sh's 2 and check-clean.sh's 3 so the results never mix up.
# usage: check-ahead.sh [target-branch]   (run from inside the repo)
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)

branch=$(git branch --show-current)
if [ -z "$branch" ]; then
  echo "detached HEAD: checkout the source branch" >&2
  exit 1
fi

target=$(bash "$here/resolve-base.sh" "${1:-}")
base="origin/$target"
if ! git rev-parse --verify --quiet "$base" >/dev/null; then
  echo "$base not found locally: run 'git fetch origin $target' and rerun" >&2
  exit 1
fi

count=$(git rev-list --count --no-merges "$base..HEAD")
echo "branch: $branch"
echo "base: $target"
echo "ahead: $count"

if [ "$branch" = "$target" ]; then
  echo "reason: on-base-branch"
  exit 4
fi
if [ "$count" -eq 0 ]; then
  echo "reason: no-commits-ahead"
  exit 4
fi
