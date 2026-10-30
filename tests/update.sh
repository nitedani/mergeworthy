#!/usr/bin/env bash
# Tests for bin/mergeworthy-update. Usage: tests/update.sh [repo root]
# Temp HOME, stub claude/codex/systemctl first on PATH. Prints "case: <got> (want <want>)"; exits 0 only when every case matches.
set -u
R=$(readlink -f "${1:-$(dirname "$0")/..}")
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; export HOME="$T/home"; mkdir -p "$HOME/.claude" "$HOME/.mergeworthy" "$T/bin"
fails=0
check() { echo "$1: $3 (want $2)"; [ "$2" = "$3" ] || fails=$((fails+1)); }

OLD="$T/cache/old"; NEW="$T/cache/new"; mkdir -p "$OLD" "$NEW"; touch "$OLD/always-on.md" "$NEW/always-on.md"
ln -s "$OLD" "$HOME/.mergeworthy/current"
cat > "$T/bin/claude" <<EOF
#!/bin/sh
echo "claude \$*" >> "$T/calls"
[ "\$*" = "plugin list --json" ] && echo '[{"id": "mergeworthy@mergeworthy", "installPath": "$NEW"}]'
exit 0
EOF
printf '#!/bin/sh\nexit 0\n' > "$T/bin/codex"  # lists no mergeworthy plugin
# stub systemctl: the units in $T/active are active; a restart of one in $T/breaks leaves it failed
cat > "$T/bin/systemctl" <<EOF
#!/bin/bash
echo "systemctl \$*" >> "$T/calls"
case "\$2" in
  show-environment) exit 0 ;;
  restart) grep -qxF "\$3" "$T/breaks" && { grep -vxF "\$3" "$T/active" > "$T/active.new"; mv "$T/active.new" "$T/active"; } ;;
  is-active) if grep -qxF "\$3" "$T/active"; then echo active; else echo failed; exit 3; fi ;;
esac
EOF
chmod +x "$T/bin/"*; export PATH="$T/bin:$PATH"

W="$HOME/.mergeworthy/work"; DASH="$W/claude-swap-resume"; BAD="$W/flaky"; IDLE="$W/retired-one"
printf '%s\n' "$DASH" "$BAD" "$IDLE" > "$HOME/.claude/gh-watch-dirs.txt"
unit() { echo "gh-watch@$(systemd-escape --path "$1").service"; }
printf '%s\n' "$(unit "$DASH")" "$(unit "$BAD")" > "$T/active"; unit "$BAD" > "$T/breaks"
: > "$T/calls"

bash "$R/bin/mergeworthy-update" > "$T/out" 2>&1; check "a unit that doesn't come back fails the update" 1 $?
check "the dashed folder's escaped unit restarted" 1 "$(grep -cxF "systemctl --user restart $(unit "$DASH")" "$T/calls")"
check "no unit restarted under the name list-units --plain prints (\\x2d lost)" 0 "$(grep -c 'restart gh-watch@.*claudex2dswap' "$T/calls")"
check "an inactive folder's unit not started" 0 "$(grep -cF "restart $(unit "$IDLE")" "$T/calls")"
check "each restarted unit's state printed" "$(unit "$DASH") active|$(unit "$BAD") failed" "$(grep '^gh-watch@' "$T/out" | paste -sd'|')"
check "the plugin updated" "claude plugin marketplace update mergeworthy|claude plugin update mergeworthy@mergeworthy" "$(grep '^claude plugin \(marketplace \)\?update' "$T/calls" | paste -sd'|')"
check "~/.mergeworthy/current points at the new version" "$NEW" "$(readlink "$HOME/.mergeworthy/current")"

: > "$T/breaks"; unit "$BAD" >> "$T/active"
bash "$R/bin/mergeworthy-update" > "$T/out" 2>&1; check "every unit back active: exit" 0 $?

[ "$fails" = 0 ] && echo "update: all cases pass" || { echo "update: $fails case(s) failed"; exit 1; }
