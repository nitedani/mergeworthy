#!/usr/bin/env bash
# Every check CI runs, in CI's order; run it before each push. Usage: tests/all.sh <repo root>
set -eu
cd "$1"
python3 docs/build-graphs.py --check
bash tests/hooks.sh .
bash tests/word-budget .
bash tests/watcher.sh .
python3 tests/watch-budget.py .
bash tests/loc-breakdown.sh .
bash tests/netns.sh .
