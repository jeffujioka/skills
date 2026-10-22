#!/usr/bin/env bash
# Print the logbook folder for this session and create it.
set -euo pipefail
dir=~/.local/state/opencode/projects/$(pwd | tr '/ ' '--')/${OPENCODE_SESSION_ID:-$(date +%Y%m%d-%H%M)}
mkdir -p "$dir"
echo "$dir"
