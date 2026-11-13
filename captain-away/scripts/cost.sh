#!/usr/bin/env bash
# Print the cost in dollars of the current session plus all its subagent sessions.
# OpenCode: from its database (OPENCODE_SESSION_ID). omp: from the session log (PI_SESSION_FILE),
# whose subagent logs sit in a folder named like the log without `.jsonl`. omp logs cache reads
# of some models at $0, so its figure is a lower bound.
set -euo pipefail
if [ -n "${OPENCODE_SESSION_ID:-}" ]; then
  sqlite3 -readonly ~/.local/share/opencode/opencode.db \
    "with recursive t(id) as (select '$OPENCODE_SESSION_ID' union all select s.id from session_v2 s join t on s.parent_id=t.id) select round(sum(cost),2) from session_v2 where id in (select id from t)"
elif [ -n "${PI_SESSION_FILE:-}" ]; then
  python3 - "$PI_SESSION_FILE" <<'PY'
import glob, json, sys
log = sys.argv[1]
def cost(path):
    total = 0.0
    for line in open(path, errors="ignore"):
        try:
            message = json.loads(line).get("message")
        except ValueError:
            continue
        usage = message.get("usage") if isinstance(message, dict) else None
        if usage and isinstance(usage.get("cost"), dict):
            total += usage["cost"].get("total") or 0
    return total
subagents = glob.glob(log[: -len(".jsonl")] + "/**/*.jsonl", recursive=True)
print(round(cost(log) + sum(cost(p) for p in subagents), 2))
PY
else
  echo "no session id: neither OPENCODE_SESSION_ID nor PI_SESSION_FILE is set" >&2
  exit 1
fi
