#!/usr/bin/env bash
# Run herdr-app where the Herdr window is: here when herdr-app is on PATH, else over ssh on the
# destination named on one line in ~/.config/handoff-hc/herdr-app-host (ssh arguments, such as `me@desk`
# or `-p 2222 me@desk`). Usage: herdr-app.sh <herdr-app arguments>
# Exit 3: no way to reach herdr-app is set up. Other failures are herdr-app's or ssh's own.
set -euo pipefail

if command -v herdr-app >/dev/null; then
  exec herdr-app "$@"
fi

config="$HOME/.config/handoff-hc/herdr-app-host"
if [[ ! -s $config ]]; then
  echo "herdr-app.sh: herdr-app is not on PATH and $config does not exist. Ask the user for the ssh destination of the machine that shows the Herdr window, write it on one line into that file, then run this again." >&2
  exit 3
fi
read -r -a destination <"$config"
printf -v arguments '%q ' "$@"
# The remote shell is not a login shell: add the usual user bin folders to its PATH.
exec ssh -o BatchMode=yes "${destination[@]}" \
  "export PATH=\"\$HOME/.local/bin:\$HOME/.homebrew/bin:/opt/homebrew/bin:\$PATH\"; herdr-app $arguments"
