#!/usr/bin/env bash
# Render every fixture through the statusline, so all degradation paths are
# visible at once for a by-eye check; the assertions live in tests/. Any
# non-zero exit means the script raised, which would show up in Claude Code as
# a blank status line.
set -uo pipefail
cd "$(dirname "$0")/.."

python3 scripts/make-fixtures.py >/dev/null

fail=0
for f in fixtures/*.json; do
  name=$(basename "$f" .json)
  printf '\033[1m── %s\033[0m\n' "$name"
  if ! COLUMNS="${COLUMNS:-120}" ./statusline.py <"$f"; then
    printf '\033[31mFAILED: %s exited non-zero\033[0m\n' "$name"
    fail=1
  fi
  echo
done

exit "$fail"
