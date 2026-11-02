#!/usr/bin/env bash
# Every check CI runs, in CI's order; run it before each push. Usage: tests/all.sh [repo root]
set -eu
REAP=$(readlink -f "$(dirname "$0")/reap.py")
cd "${1:-$(dirname "$0")/..}"
[ -d node_modules/typescript ] && [ -d cli/node_modules ] || { echo "all.sh: install the dependencies first, \`npm install && npm install --prefix cli\` (\`pnpm install\` in both where npm is disabled): review-context and its tests use mergeworthy's TypeScript, tests/watcher.sh the installer's"; exit 1; }
# tests/refuse first on PATH: a docker a suite finds by PATH lookup is the refusing one (an absolute path or a replaced PATH is not)
export PATH="$PWD/tests/refuse:$PATH" ALL_SH_LEAKED=$(mktemp); trap 'rm -f "$ALL_SH_LEAKED"' EXIT
run() { # a suite; once it and every process it started have exited (tests/reap.py), fail when one of them called docker
  python3 "$REAP" "$@"
  if [ -s "$ALL_SH_LEAKED" ]; then echo "all.sh: '$*' called docker:" >&2; cat "$ALL_SH_LEAKED" >&2; exit 1; fi
}
# The suites share no state (each makes its own temp HOME and repos), so they run at once, each into its own log, printed in
# this order once all end: the run takes as long as its slowest suite, not their sum
SUITES=(
  'python3 docs/build-graphs.py --check'
  'bash tests/hooks.sh .'
  'bash tests/word-budget .'
  'python3 tests/pointers.py .'
  'bash tests/watcher.sh .'
  'bash tests/update.sh .'
  'bash tests/steward.sh .'
  'bash tests/project-learn.sh .'
  'python3 tests/watch-budget.py .'
  'python3 tests/watch-cadence.py .'
  'bash tests/loc-breakdown.sh .'
  'bash tests/disk-sweep.sh .'
  'bash tests/review-context.sh .'
  'bash tests/netns.sh .'
)
LOGS=$(mktemp -d); trap 'rm -rf "$LOGS" "$ALL_SH_LEAKED"' EXIT
# the tree tested: HEAD's, when the worktree holds nothing else (untracked files the tests don't read aside)
tree=$([ -z "$(git status --porcelain --untracked-files=no 2>/dev/null)" ] && git rev-parse -q --verify 'HEAD^{tree}' 2>/dev/null || true)
for i in "${!SUITES[@]}"; do (ALL_SH_LEAKED=$LOGS/$i.leak; : > "$ALL_SH_LEAKED"; run ${SUITES[i]} > "$LOGS/$i" 2>&1; echo $? > "$LOGS/$i.rc") & done  # a docker call is its own suite's
wait
failed=0
for i in "${!SUITES[@]}"; do
  cat "$LOGS/$i"; rc=$(cat "$LOGS/$i.rc")
  [ "$rc" = 0 ] || { echo "all.sh: '${SUITES[i]}' failed (exit $rc)" >&2; failed=1; }
done
[ "$failed" = 0 ] || exit 1
# a green run records the tree it tested: the pre-push hook doesn't run the same tree again (.githooks/pre-push)
[ -z "$tree" ] || { mkdir -p "${XDG_CACHE_HOME:-$HOME/.cache}/mergeworthy/passed" && touch "${XDG_CACHE_HOME:-$HOME/.cache}/mergeworthy/passed/$tree"; }
