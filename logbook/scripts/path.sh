#!/usr/bin/env bash
# Print the logbook folder for this session and create it.
# Session id: OpenCode's OPENCODE_SESSION_ID, else omp's PI_SESSION_ID, else the start minute.
set -euo pipefail
dir=~/.local/state/opencode/projects/$(pwd | tr '/ ' '--')/${OPENCODE_SESSION_ID:-${PI_SESSION_ID:-$(date +%Y%m%d-%H%M)}}
mkdir -p "$dir"
echo "$dir"
