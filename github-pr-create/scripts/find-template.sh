#!/usr/bin/env bash
# Lists the GitHub PR template files of the current repo, or prints "none".
# usage: find-template.sh   (run from inside the repo)
set -euo pipefail

root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)

shopt -s nullglob

dir="$root/.github/PULL_REQUEST_TEMPLATE"
files=("$dir"/*.md)
if [ "${#files[@]}" -gt 0 ]; then
  for f in "${files[@]}"; do
    echo ".github/PULL_REQUEST_TEMPLATE/$(basename "$f")"
  done
  exit 0
fi

for single in \
  "$root/.github/PULL_REQUEST_TEMPLATE.md" \
  "$root/PULL_REQUEST_TEMPLATE.md" \
  "$root/docs/PULL_REQUEST_TEMPLATE.md"; do
  if [ -f "$single" ]; then
    echo "${single#"$root"/} (Default)"
    exit 0
  fi
done

echo none
