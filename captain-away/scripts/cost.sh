#!/usr/bin/env bash
# Print the cost in dollars of the run: the root session plus all its subagent sessions.
# The harness and the sources come from harness-kit's agent-env. claude: the last
# cost-state.totalCostUSD of the root transcript, which may leave out subagents, so it is
# printed as an estimate. omp: the sum of usage.cost.total over the root log and its subagent
# logs; omp logs cache reads of some models at $0, so its figure is a lower bound. claude and
# omp skip a line that is not valid JSON (a live log's half-written last line).
# opencode: sum(cost) of session_v2 over the root session and its descendants; a session
# missing from session_v2 stops the script.
# jq and sqlite3 print a dot decimal point, so printf reads it under LC_ALL=C whatever the
# user's locale.
set -euo pipefail
require=$(dirname "${BASH_SOURCE[0]}")/../../logbook/scripts/require-agent-env.sh
[[ -f "$require" ]] || { echo "cost.sh: needs the logbook skill beside captain-away" >&2; exit 1; }
source "$require"

harness=$("$AGENT_ENV" | sed -n 's/^AGENT_HARNESS=//p')
sources=$("$AGENT_ENV" root-source)
values() { printf '%s\n' "$sources" | sed -n "s/^$1=//p"; }

case "$harness" in
  claude)
    transcript=$(values TRANSCRIPT)
    amount=$(jq -rRn '[inputs | fromjson? | select(.type? == "cost-state") | .totalCostUSD | numbers] | last // empty' "$transcript")
    [[ -n "$amount" ]] || { echo "cost.sh: no cost-state.totalCostUSD in $transcript" >&2; exit 1; }
    LC_ALL=C printf '%.2f (estimate)\n' "$amount"
    ;;
  omp)
    mapfile -t files < <(values JSONL)
    amount=$(jq -rRn '[inputs | fromjson? | select(.type? == "message" and .message.role? == "assistant") | .message.usage.cost.total? | numbers] | if length == 0 then empty else add end' "${files[@]}")
    [[ -n "$amount" ]] || { echo "cost.sh: no usage.cost.total in ${files[0]}" >&2; exit 1; }
    LC_ALL=C printf '%.2f\n' "$amount"
    ;;
  opencode)
    db=$(values DB)
    ids=$(values SESSION | sed "s/'/''/g; s/.*/('&')/" | paste -sd,)
    # One read: the row "0|<sum>", then "1|<id>" for each listed session missing from
    # session_v2, in id order.
    rows=$(sqlite3 -readonly -cmd '.timeout 5000' "$db" "with wanted(id) as (values $ids)
      select 0, sum(cost) from session_v2 where id in (select id from wanted)
      union all
      select 1, id from wanted where id not in (select id from session_v2)
      order by 1, 2")
    amount=$(sed -n 's/^0|//p' <<<"$rows")
    missing=$(sed -n 's/^1|//p' <<<"$rows" | paste -sd' ')
    [[ -z "$missing" ]] || { echo "cost.sh: sessions not found in session_v2 of $db: $missing" >&2; exit 1; }
    LC_ALL=C printf '%.2f\n' "$amount"
    ;;
  *)
    echo "cost.sh: unknown harness $harness (claude, omp, opencode)" >&2
    exit 1
    ;;
esac
