#!/usr/bin/env bash
# Stages chosen hunks of one tracked file without `git add -p` (which needs a TTY).
# Builds the file's unstaged diff, keeps the chosen hunks, applies them to the index
# with --recount (hunk line counts go stale once hunks are dropped). The working tree
# is never touched, so the unchosen hunks stay as uncommitted changes.
# usage: stage-hunks.sh [-U<n>] --list <file>             numbered hunks, one summary each
#        stage-hunks.sh [-U<n>] <file> <hunk-number>...   stage those hunks
# -U<n>: context lines (default 3). Nearby changes merge into one hunk; -U0 splits them.
set -euo pipefail

usage="usage: stage-hunks.sh [-U<n>] --list <file> | [-U<n>] <file> <hunk-number>..."
ctx=3
case "${1:-}" in -U[0-9]*) ctx=${1#-U}; shift ;; esac
list=0
if [ "${1:-}" = "--list" ]; then list=1; shift; fi
file=${1:?$usage}
shift

patch=$(mktemp)
sel=$(mktemp)
trap 'rm -f "$patch" "$sel"' EXIT

git diff -U"$ctx" --no-color -- "$file" > "$patch"
total=$(grep -c '^@@' "$patch" || true)
if [ "$total" -eq 0 ]; then
  echo "no unstaged hunks in $file" >&2
  exit 1
fi

if [ "$list" -eq 1 ]; then
  awk '/^@@/ { n++; printf "%d: %s\n", n, $0; first = 1; next }
       n && first && /^[-+]/ { print "     " $0; first = 0 }' "$patch"
  exit 0
fi

[ "$#" -gt 0 ] || { echo "$usage" >&2; exit 1; }
for n in "$@"; do
  case "$n" in ''|*[!0-9]*) echo "not a hunk number: $n" >&2; exit 1 ;; esac
  if [ "$n" -lt 1 ] || [ "$n" -gt "$total" ]; then
    echo "hunk $n out of range: $file has $total" >&2
    exit 1
  fi
done

awk -v keep=" $* " '/^@@/ { n++; on = index(keep, " " n " ") > 0 } n == 0 || on' "$patch" > "$sel"

flags=(--cached --recount)
[ "$ctx" -eq 0 ] && flags+=(--unidiff-zero)
git apply "${flags[@]}" "$sel"
echo "staged hunks $* of $file (of $total):"
git diff --cached --stat -- "$file"
