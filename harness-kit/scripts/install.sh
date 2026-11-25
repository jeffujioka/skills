#!/usr/bin/env bash
# Plan, install, check or remove the harness-kit artefacts for every harness found on PATH.
#   install.sh plan                          list what install would write; writes nothing
#   install.sh install [--replace <path>]... write it; a foreign target is kept unless named
#   install.sh check                         report each artefact; exit 1 unless all are current
#   install.sh remove                        delete what harness-kit installed; foreign files stay
set -euo pipefail

kit=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
version=$(<"$kit/VERSION")
harnesses=(claude omp opencode)
# shellcheck disable=SC2016  # $HOME must stay literal: the hook expands it when it runs
hook_command='bash "$HOME/.claude/hooks/harness-kit-session-start.sh"'
usage="usage: install.sh plan | install [--replace <path>]... | check | remove"

# The one copy of the install paths, one row per artefact:
#   name|harness|source under harness-kit/|target under ~|mode|explanation|what a foreign file there would do
# Harness "any" installs whenever a harness is found; source "settings" is the claude settings entry,
# which check reports under claude-hook.
artefacts=(
  "agent-env|any|bin/agent-env|.local/bin/agent-env|755|prints the harness and session ids that logbook, captain-away and hc-handoff read|the consumer skills would run it as agent-env"
  "-|claude|settings|.claude/settings.json|-|gains one SessionStart entry that runs the claude hook; other entries stay|-"
  "claude-hook|claude|claude/session-start.sh|.claude/hooks/harness-kit-session-start.sh|755|sets AGENT_HARNESS=claude for the session's shell commands and names the logbook after compaction and shows a notice that it did|the harness-kit SessionStart entry would run it at every claude session start"
  "omp-extension|omp|omp/harness-kit.ts|.omp/agent/extensions/harness-kit.ts|644|sets AGENT_HARNESS=omp on commands that run agent-env or a skills script, adds the logbook reminder to the session after compaction and shows a notice, and asks GitHub Copilot for 1h prompt-cache entries on Claude models in the main session (a cache write costs more, a read after a pause costs less; HARNESS_KIT_COPILOT_CACHE=5m opts out)|omp would load it as the harness-kit extension"
  "opencode-plugin|opencode|opencode/server.ts|.config/opencode/plugins/harness-kit/index.ts|644|sets AGENT_HARNESS=opencode for the session's shell commands and adds the logbook reminder as a session instruction after compaction|opencode would load it as the harness-kit plugin"
  "opencode-tui|opencode|opencode/tui.ts|.config/opencode/plugins/harness-kit/tui.ts|644|shows a toast that the logbook reminder was added after compaction|opencode would load it as the TUI part of the harness-kit plugin"
)

mode=${1:-}
[[ $mode == plan || $mode == install || $mode == check || $mode == remove ]] || {
  echo "$usage" >&2
  exit 2
}
shift
replace=()
while (($#)); do
  [[ $mode == install && $1 == --replace && $# -ge 2 ]] || {
    echo "$usage" >&2
    exit 2
  }
  replace+=("${2/#$HOME/\~}")
  shift 2
done

found=()
for harness in "${harnesses[@]}"; do
  command -v "$harness" >/dev/null && found+=("$harness")
done
if ((${#found[@]} == 0)); then
  echo "No harness found (claude, omp, opencode): nothing to install."
  exit 0
fi
if [[ " ${found[*]} " == *" claude "* ]] && ! command -v jq >/dev/null; then
  echo "harness-kit: jq not found; it is needed to edit ~/.claude/settings.json. Install jq, then run harness-kit again." >&2
  exit 1
fi

settings="$HOME/.claude/settings.json"
all_current=true
repair=false
[[ $mode == plan ]] && echo "harness-kit $version would write:"
for row in "${artefacts[@]}"; do
  IFS='|' read -r name harness source target file_mode explanation foreign_use <<<"$row"
  # shellcheck disable=SC2088  # shown is display text: the tilde stays literal
  shown="~/$target"
  path="$HOME/$target"
  # A file target is absent, foreign (no marker), current, older or newer than $version.
  state=absent
  marker=
  if [[ $source != settings && -e $path ]]; then
    marker=$(grep -Eo -m1 'harness-kit [0-9][^[:space:]]*$' "$path" || true)
    marker=${marker#harness-kit }
    if [[ -z $marker ]]; then
      state=foreign
    elif [[ $marker == "$version" ]]; then
      state=current
    elif printf '%s\n' "$marker" "$version" | sort -CV; then
      state=older
    else
      state=newer
    fi
  fi
  if [[ $mode == remove ]]; then
    case $state in
      absent) ;;
      foreign) echo "kept foreign $shown" ;;
      *)
        rm -- "$path"
        echo "removed $shown"
        ;;
    esac
    continue
  fi
  if [[ $harness != any && " ${found[*]} " != *" $harness "* ]]; then
    [[ $mode == check && $source != settings ]] && echo "$name: skipped, $harness not found"
    continue
  fi
  if [[ $mode == check ]]; then
    [[ $source == settings ]] && continue
    if [[ $state == absent ]] || { [[ $harness == claude ]] && ! bash "$kit/scripts/claude-settings.sh" has "$settings" "$hook_command"; }; then
      echo "$name: missing ($shown)"
      repair=true
      all_current=false
      continue
    fi
    case $state in
      current) echo "$name: installed $marker ($shown)" ;;
      older)
        echo "$name: older $marker ($shown)"
        repair=true
        all_current=false
        ;;
      newer)
        echo "$name: newer $marker ($shown)"
        all_current=false
        ;;
      foreign)
        echo "$name: foreign ($shown)"
        all_current=false
        ;;
    esac
    continue
  fi
  if [[ $source == settings ]] && bash "$kit/scripts/claude-settings.sh" has "$path" "$hook_command"; then
    state=current
  fi
  if [[ $mode == plan ]]; then
    case $state in
      absent) echo "$shown: $explanation" ;;
      current) echo "$shown: unchanged" ;;
      older) echo "$shown: replaced ($marker -> $version); $explanation" ;;
      newer) echo "$shown: newer (harness-kit $marker), kept" ;;
      foreign) echo "$shown: foreign (no harness-kit marker), kept unless you confirm replacing it; $foreign_use" ;;
    esac
    continue
  fi
  case $state in
    current)
      echo "unchanged $shown"
      continue
      ;;
    newer)
      echo "kept newer $shown ($marker)"
      continue
      ;;
    foreign)
      if [[ " ${replace[*]-} " != *" $shown "* ]]; then
        echo "kept foreign $shown"
        continue
      fi
      status="replaced foreign $shown"
      ;;
    older) status="replaced $shown ($marker -> $version)" ;;
    absent) status="installed $shown" ;;
  esac
  if [[ $source == settings ]]; then
    bash "$kit/scripts/claude-settings.sh" add "$path" "$hook_command"
  else
    mkdir -p "$(dirname "$path")"
    sed "s/@VERSION@/$version/" "$kit/$source" >"$path.tmp"
    chmod "$file_mode" "$path.tmp"
    mv "$path.tmp" "$path"
  fi
  echo "$status"
done

if [[ $mode == remove ]]; then
  if [[ -e $settings ]] && bash "$kit/scripts/claude-settings.sh" has "$settings" "$hook_command"; then
    bash "$kit/scripts/claude-settings.sh" remove "$settings" "$hook_command"
    echo "removed the SessionStart entry from ~/.claude/settings.json"
  fi
elif [[ $mode == check ]]; then
  $repair && echo "Run the harness-kit skill's install to repair."
  $all_current || exit 1
elif [[ $mode == plan ]]; then
  for harness in "${harnesses[@]}"; do
    [[ " ${found[*]} " == *" $harness "* ]] || echo "$harness not found: nothing is written for it"
  done
  if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    # shellcheck disable=SC2088,SC2016  # the message shows the path and the export line as text to copy, unexpanded
    echo '~/.local/bin is not on PATH; add this line to your shell profile: export PATH="$HOME/.local/bin:$PATH"'
  fi
fi
