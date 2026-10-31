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
# stub claude: mergeworthy installed unless $T/claude-none exists; its update fails while $T/claude-fails exists
cat > "$T/bin/claude" <<EOF
#!/bin/sh
echo "claude \$*" >> "$T/calls"
case "\$*" in
  "plugin list --json") if [ -e "$T/claude-none" ]; then echo '[]'; else echo '[{"id": "mergeworthy@mergeworthy", "installPath": "$NEW"}]'; fi ;;
  *update*) [ -e "$T/claude-fails" ] && exit 1 ;;
esac
exit 0
EOF
# stub codex: lists mergeworthy installed while $T/codex-has exists; pnpm records the installer run
cat > "$T/bin/codex" <<EOF
#!/bin/sh
[ "\$*" = "plugin list" ] && [ -e "$T/codex-has" ] && echo "mergeworthy@mergeworthy (installed)"
exit 0
EOF
printf '#!/bin/sh\necho "pnpm $*" >> "%s/calls"\n' "$T" > "$T/bin/pnpm"
# stub systemctl: the units in $T/active are active; a restart of one in $T/breaks leaves it failed, of one in $T/stops
# inactive, and one in $T/retires also writes its folder's `retired`, as its watcher does when it retires
cat > "$T/bin/systemctl" <<EOF
#!/bin/bash
echo "systemctl \$*" >> "$T/calls"
case "\$2" in
  show-environment) exit 0 ;;
  restart) grep -qxF "\$3" "$T/breaks" "$T/stops" && { grep -vxF "\$3" "$T/active" > "$T/active.new"; mv "$T/active.new" "$T/active"; }
    i=\${3#gh-watch@}; grep -qxF "\$3" "$T/retires" && touch "\$(systemd-escape --unescape --path "\${i%.service}")/retired" ;;
  is-active) if grep -qxF "\$3" "$T/active"; then echo active; elif grep -qxF "\$3" "$T/stops"; then echo inactive; exit 3; else echo failed; exit 3; fi ;;
esac
EOF
chmod +x "$T/bin/"*; export PATH="$T/bin:$PATH"

W="$HOME/.mergeworthy/work"; DASH="$W/claude-swap-resume"; BAD="$W/flaky"; IDLE="$W/retired-one"; GONE="$W/deleted"
mkdir -p "$DASH" "$BAD" "$IDLE"
printf '%s\n' "$DASH" "$BAD" "$IDLE" "$GONE" > "$HOME/.claude/gh-watch-dirs.txt"
unit() { echo "gh-watch@$(systemd-escape --path "$1").service"; }
printf '%s\n' "$(unit "$DASH")" "$(unit "$BAD")" "$(unit "$GONE")" > "$T/active"; unit "$BAD" > "$T/breaks"
: > "$T/stops"; : > "$T/retires"; : > "$T/calls"

bash "$R/bin/mergeworthy-update" > "$T/out" 2>&1; check "a unit that doesn't come back fails the update" 1 $?
check "the dashed folder's escaped unit restarted" 1 "$(grep -cxF "systemctl --user restart $(unit "$DASH")" "$T/calls")"
check "no unit restarted under the name list-units --plain prints (\\x2d lost)" 0 "$(grep -c 'restart gh-watch@.*claudex2dswap' "$T/calls")"
check "an inactive folder's unit not started" 0 "$(grep -cF "restart $(unit "$IDLE")" "$T/calls")"
check "a deleted folder's unit not restarted" 0 "$(grep -cF "restart $(unit "$GONE")" "$T/calls")"
check "each restarted unit's state printed" "$(unit "$DASH") active|$(unit "$BAD") failed" "$(grep '^gh-watch@' "$T/out" | paste -sd'|')"
check "the plugin updated" "claude plugin marketplace update mergeworthy|claude plugin update mergeworthy@mergeworthy" "$(grep '^claude plugin \(marketplace \)\?update' "$T/calls" | paste -sd'|')"
check "~/.mergeworthy/current points at the new version" "$NEW" "$(readlink "$HOME/.mergeworthy/current")"

: > "$T/breaks"; unit "$BAD" >> "$T/active"
bash "$R/bin/mergeworthy-update" > "$T/out" 2>&1; check "every unit back active: exit" 0 $?

# a watcher whose every thread closed retires right after its restart: it writes its folder's `retired` and stops its unit
DONE="$W/all-merged"; QUIT="$W/stopped"; mkdir -p "$DONE" "$QUIT"; printf '%s\n' "$DONE" "$QUIT" >> "$HOME/.claude/gh-watch-dirs.txt"
unit "$DONE" | tee -a "$T/active" "$T/stops" > "$T/retires"
bash "$R/bin/mergeworthy-update" > "$T/out" 2>&1; rc=$?; check "a watcher that retired: exit, its state" "0 $(unit "$DONE") retired" "$rc $(grep -F "$(unit "$DONE")" "$T/out")"
unit "$QUIT" | tee -a "$T/active" > "$T/stops"
bash "$R/bin/mergeworthy-update" > "$T/out" 2>&1; rc=$?; check "a watcher stopped without retiring: exit, failure named" "1 failed: $(unit "$QUIT")" "$rc $(grep '^failed:' "$T/out")"

# Codex only: Claude Code is on PATH but has no mergeworthy, and updating it there would fail
touch "$T/claude-none" "$T/claude-fails" "$T/codex-has"; : > "$T/calls"
bash "$R/bin/mergeworthy-update" > "$T/out" 2>&1; check "mergeworthy only in Codex: exit" 0 $?
check "mergeworthy only in Codex: Claude Code not updated, Codex updated" "|pnpm dlx mergeworthy --yes --agents codex" \
  "$(grep '^claude plugin \(marketplace \)\?update' "$T/calls" | paste -sd'|')|$(grep '^pnpm' "$T/calls")"

# in both, Claude Code's update fails: Codex is still updated, the watchers restarted, and the failure named at the end
rm "$T/claude-none"; : > "$T/calls"
bash "$R/bin/mergeworthy-update" > "$T/out" 2>&1; check "a failed Claude Code update: exit" 1 $?
check "a failed Claude Code update: Codex updated, units restarted, failure named" "1 2 failed: the Claude Code update" \
  "$(grep -c '^pnpm' "$T/calls") $(grep -c 'restart gh-watch@' "$T/calls") $(grep '^failed:' "$T/out")"

[ "$fails" = 0 ] && echo "update: all cases pass" || { echo "update: $fails case(s) failed"; exit 1; }
