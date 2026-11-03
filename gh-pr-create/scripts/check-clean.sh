#!/usr/bin/env bash
# Reports local changes that a new PR would not contain. Read-only.
# Exit 0: no uncommitted changes to tracked files (untracked files are listed, not blocking).
# Exit 3: tracked files have uncommitted changes; they are listed for the user.
# 3 differs from check-pushed.sh's 2 so the two results never mix up.
# usage: check-clean.sh   (run from inside the repo)
set -euo pipefail

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "not inside a git work tree: run from the repo" >&2
  exit 1
fi

tracked=$(git status --porcelain --untracked-files=no)
untracked=$(git ls-files --others --exclude-standard)

if [ -n "$untracked" ]; then
  echo "untracked files (not in the PR, not blocking):"
  printf '%s\n' "$untracked" | sed 's/^/  /'
fi

if [ -n "$tracked" ]; then
  echo "uncommitted changes to tracked files (not in the PR):"
  printf '%s\n' "$tracked" | sed 's/^/  /'
  exit 3
fi

echo "clean: no uncommitted changes to tracked files"
