#!/usr/bin/env bash
# Prints the base (target) branch name for PRs from this repo. Read-only; never fetches.
# Order: the argument, origin/HEAD, the default branch gh reports, the only one of
# origin/main and origin/master that exists. Never defaults blindly.
# usage: resolve-base.sh [target-branch]   (run from inside the repo)
set -euo pipefail

if [ -n "${1:-}" ]; then
  echo "$1"
  exit 0
fi

ref=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)
if [ -n "$ref" ]; then
  echo "${ref#origin/}"
  exit 0
fi

if command -v gh >/dev/null 2>&1; then
  name=$(gh repo view --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null || true)
  if [ -n "$name" ]; then
    echo "$name"
    exit 0
  fi
fi

found=()
for b in main master; do
  if git rev-parse --verify --quiet "refs/remotes/origin/$b" >/dev/null; then
    found+=("$b")
  fi
done
if [ "${#found[@]}" -eq 1 ]; then
  echo "${found[0]}"
  exit 0
fi

echo "cannot tell the default branch (origin/HEAD unset, gh found none): pass the target branch" >&2
exit 1
