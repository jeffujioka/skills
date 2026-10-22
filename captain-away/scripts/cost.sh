#!/usr/bin/env bash
# Print the cost in dollars of the current session plus all its subagent sessions.
set -euo pipefail
: "${OPENCODE_SESSION_ID:?not set}"
sqlite3 -readonly ~/.local/share/opencode/opencode.db \
  "with recursive t(id) as (select '$OPENCODE_SESSION_ID' union all select s.id from session_v2 s join t on s.parent_id=t.id) select round(sum(cost),2) from session_v2 where id in (select id from t)"
