#!/bin/bash
# The posting and safety guard against fixtures/guard-cases.txt: one `expected-exit[ VAR=value…]|command` per line.
# Run: bash tests/test_pre_bash_guard.sh (exit 0 = all pass). The watcher check is off unless a case sets
# MERGEWORTHY_WATCHER=on; fixtures/bin/gh answers `gh api user` as test-login.
guard=$(readlink -f "$(dirname "$0")/../hooks/pre-bash-guard.py"); cd "$(dirname "$0")/fixtures"; fails=0
while IFS='|' read -r exp c; do
  read -r exp vars <<<"$exp"
  c=${c//\$D/$PWD/drafts/x.md}; c=${c//\$T\//$PWD/drafts/}
  rm -f drafts/*.posted  # each case posts fresh; the duplicate-post check has its own cases
  printf '%s' "$c" | python3 -c 'import json,sys;print(json.dumps({"tool_input":{"command":sys.stdin.read()},"cwd":sys.argv[1]}))' "$PWD" | PATH=$PWD/bin:$PATH env -u MERGEWORTHY_MERGE MERGEWORTHY_WATCHER=off $vars python3 "$guard" 2>/dev/null; rc=$?
  [ "$rc" = "$exp" ] || { fails=$((fails+1)); echo "MISMATCH exp=$exp got=$rc: $c"; }
done < guard-cases.txt
echo "$(( $(wc -l < guard-cases.txt) - fails ))/$(wc -l < guard-cases.txt) passed"
[ "$fails" = 0 ]
