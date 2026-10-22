#!/usr/bin/env bash
# Request compaction of the current session. The id must start with msg_.
# Compaction runs at once and aborts the calling shell, so no output may arrive.
set -euo pipefail
: "${OPENCODE_SESSION_ID:?not set}"
opencode api post "/api/session/$OPENCODE_SESSION_ID/compact" --data "{\"id\":\"msg_logbook$(date +%s)\"}" 2>&1 | tail -2
