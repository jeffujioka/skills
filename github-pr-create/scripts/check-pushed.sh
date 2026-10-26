#!/usr/bin/env bash
# Exit 0 when the current branch's upstream is at HEAD, i.e. pushed with nothing
# local ahead. Uses the upstream as last fetched. Read-only; never pushes.
set -euo pipefail

branch=$(git branch --show-current)
if [ -z "$branch" ]; then
  echo "detached HEAD: checkout the source branch" >&2
  exit 1
fi

if ! upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null); then
  echo "branch $branch has no upstream: not pushed. Stop; the user pushes it." >&2
  exit 2
fi

if [ "$(git rev-parse HEAD)" != "$(git rev-parse '@{u}')" ]; then
  echo "HEAD of $branch differs from $upstream: not fully pushed. Stop; the user pushes it." >&2
  exit 2
fi

echo "pushed: $branch is at $upstream"
