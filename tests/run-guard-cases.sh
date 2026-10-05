#!/bin/bash
# run-guard-cases.sh <guard.py>: expected-exit[ VAR=value…]|command per line in guard-cases.txt (run from tests/); the watcher check is off unless a case sets MERGEWORTHY_WATCHER=on; bin/gh answers `gh api user` as test-login
guard=$(readlink -f "$1"); cd "$(dirname "$0")"; fails=0
while IFS='|' read -r exp c; do
  read -r exp vars <<<"$exp"
  c=${c//\$D/$PWD/drafts/x.md}; c=${c//\$T\//$PWD/drafts/}
  rm -f drafts/*.posted  # each case posts fresh; the duplicate-post check has its own cases
  printf '%s' "$c" | python3 -c 'import json,sys;print(json.dumps({"tool_input":{"command":sys.stdin.read()},"cwd":sys.argv[1]}))' "$PWD" | PATH=$PWD/bin:$PATH env -u MERGEWORTHY_MERGE MERGEWORTHY_WATCHER=off $vars python3 "$guard" 2>guard-stderr.txt; rc=$?
  [ "$rc" = "$exp" ] || { fails=$((fails+1)); echo "MISMATCH exp=$exp got=$rc: $c"; }
done < guard-cases.txt
echo "$guard: $fails mismatches of $(wc -l < guard-cases.txt)"
