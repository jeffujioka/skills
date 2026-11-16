#!/usr/bin/env bash
# Short-lived omp agents for hire: one file per dispatch, pinned to one model and one level.
#   omp-agent.sh create <provider/model-id> <level>   write the agent, print its name
#   omp-agent.sh remove <name>                         delete an agent hire wrote
# create also deletes hire agents older than a day, left by a session that ended before remove.
set -euo pipefail

dir="$HOME/.omp/agent/agents"
usage="usage: omp-agent.sh create <provider/model-id> <low|medium|high|xhigh|max> | remove <hire-name>"

case ${1:-} in
  create)
    [[ $# -eq 3 && $2 == */claude-* && $3 =~ ^(low|medium|high|xhigh|max)$ ]] || {
      echo "$usage" >&2
      exit 2
    }
    mkdir -p "$dir"
    find "$dir" -maxdepth 1 -name 'hire-*.md' -mmin +1440 -delete
    name="hire-${2#*/claude-}-$3-$(od -An -N3 -tx1 /dev/urandom | tr -d ' \n')"
    cat >"$dir/$name.md" <<EOF
---
name: $name
description: Temporary hire agent on $2 at $3. Use only when the user named it.
model: $2
thinking-level: $3
---

You are a general-purpose subagent. Do the task you are given, then report the result.
EOF
    echo "$name"
    ;;
  remove)
    [[ $# -eq 2 && $2 =~ ^hire-[a-z0-9.-]+$ ]] || {
      echo "$usage" >&2
      exit 2
    }
    rm -f -- "$dir/$2.md"
    ;;
  *)
    echo "$usage" >&2
    exit 2
    ;;
esac
