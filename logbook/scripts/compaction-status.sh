#!/usr/bin/env bash
# Print the latest compaction of the current session as "id|status". Status completed means done.
set -euo pipefail
: "${OPENCODE_SESSION_ID:?not set}"
sqlite3 -readonly ~/.local/share/opencode/opencode.db \
  "select id, json_extract(data,'\$.status') from session_message where session_id='$OPENCODE_SESSION_ID' and type='compaction' order by time_created desc limit 1"
