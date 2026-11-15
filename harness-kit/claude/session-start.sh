#!/usr/bin/env bash
# harness-kit @VERSION@
# claude SessionStart hook: export AGENT_HARNESS=claude through CLAUDE_ENV_FILE, once,
# and after compaction pass on agent-env's logbook reminder as additionalContext,
# with a systemMessage that shows the user it was sent.
set -euo pipefail

payload=$(cat)
line='export AGENT_HARNESS=claude'
if [[ -n "${CLAUDE_ENV_FILE:-}" ]] && ! grep -qxF "$line" "$CLAUDE_ENV_FILE" 2>/dev/null; then
  printf '%s\n' "$line" >>"$CLAUDE_ENV_FILE"
fi

[[ "$(jq -r '.source // empty' <<<"$payload")" == compact ]] || exit 0
cd "$(jq -r '.cwd' <<<"$payload")"
reminder=$(AGENT_HARNESS=claude CLAUDE_CODE_SESSION_ID="$(jq -r '.session_id' <<<"$payload")" \
  "$HOME/.local/bin/agent-env" compact-reminder)
[[ -n "$reminder" ]] || exit 0
logbook=$(sed -n 's/.*`\([^`]*\)\/progress\.md`.*/\1/p' <<<"$reminder" | head -n 1)
notice='harness-kit: logbook reminder sent to the model'
[[ -z "$logbook" ]] || notice="$notice ($logbook)"
jq -n --arg context "$reminder" --arg notice "$notice" \
  '{systemMessage: $notice, hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $context}}'
