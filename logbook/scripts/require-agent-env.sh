# shellcheck shell=bash
# shellcheck disable=SC2034  # AGENT_ENV is read by the script that sources this file
# Sourced: set AGENT_ENV to the agent-env command, or stop when harness-kit is missing.
if AGENT_ENV=$(command -v agent-env); then
  :
elif [ -x "$HOME/.local/bin/agent-env" ]; then
  AGENT_ENV=$HOME/.local/bin/agent-env
else
  echo "agent-env not found: harness-kit is not installed. Ask your agent to run the harness-kit skill, then start a new session." >&2
  exit 1
fi
