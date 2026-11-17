#!/usr/bin/env bash
# Print the logbook folder of this session's root and create it.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/require-agent-env.sh"
dir=$("$AGENT_ENV" logbook-dir)
mkdir -p "$dir"
# opencode kept its logbooks in this folder before harness-kit moved them under agent-env's logbook-dir; a project with an old logbook gets a pointer to it.
old=$HOME/.local/state/opencode/projects/$(basename "$(dirname "$dir")")
if [ ! -e "$dir/progress.md" ] && [ -d "$old" ]; then
  newest=$(ls -td "$old"/*/ 2>/dev/null | head -n 1 || true)
  if [ -n "$newest" ]; then
    echo "Older logbook for this project: ${newest%/}; copy its files here to continue it." >&2
  fi
fi
echo "$dir"
