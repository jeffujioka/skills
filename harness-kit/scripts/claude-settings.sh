#!/usr/bin/env bash
# Edit the harness-kit entry of a claude settings file with jq, keeping every other key.
#   claude-settings.sh add <settings file> <command>
#   claude-settings.sh has <settings file> <command>   exit 0 when a SessionStart entry runs <command>, else 1
#   claude-settings.sh remove <settings file> <command> drop <command>, then any SessionStart list or hooks object left empty
set -euo pipefail

[[ (${1:-} == add || ${1:-} == has || ${1:-} == remove) && $# -eq 3 ]] || {
  echo "usage: claude-settings.sh add|has|remove <settings file> <command>" >&2
  exit 2
}
action=$1
file=$2
command=$3

current='{}'
[[ -e $file ]] && current=$(<"$file")
if [[ $action == has ]]; then
  jq -e --arg command "$command" \
    'any(.hooks.SessionStart[]?.hooks[]?; .command == $command)' \
    <<<"$current" >/dev/null || exit 1
  exit 0
fi
if [[ $action == add ]]; then
  filter='.hooks.SessionStart += [{"hooks": [{"type": "command", "command": $command}]}]'
else
  filter='.hooks.SessionStart |= map(.hooks |= map(select(.command != $command)) | select(.hooks != []))
    | if .hooks.SessionStart == [] then del(.hooks.SessionStart) else . end
    | if .hooks == {} then del(.hooks) else . end'
fi
mkdir -p "$(dirname "$file")"
updated=$(jq --arg command "$command" "$filter" <<<"$current")
# Write into the existing file, so its mode, owner and any symlink stay.
printf '%s\n' "$updated" >"$file"
