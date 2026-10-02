#!/bin/bash
# build.sh [--all | profile…]: assembles the single file an agent is given (and install-methodology reads):
# dist/methodology-prompt.md with no profile, else dist/methodology-<profile>-<profile>….md.
# Settings start from profiles/defaults.env; each profiles/<name>.env is sourced in order, later ones winning.
set -e
cd "$(dirname "$0")"
if [ "$1" = --all ]; then
  ./build.sh; ./build.sh ci; exit
fi
. profiles/defaults.env
for p; do . "profiles/$p.env"; done
settings=$(sed -n 's/^\([a-z_]*\)=.*/\1/p' profiles/defaults.env | while read -r k; do echo "$k=${!k}"; done)
out=dist/methodology-$(IFS=-; echo "${*:-prompt}").md
mkdir -p dist
{
  {
    while read -r f; do cat "methodology/$f"; done < methodology/ORDER
    echo; cat methodology/part4-failures.md; echo; cat methodology/part2-implement-issue.md; echo; cat methodology/part3-convergence.md
    echo; echo '---'; echo; cat methodology/part5-mechanisms.md; echo
  } | python3 claude/tools/filter.py $settings
  for f in gh-watch.py gh-watch-daemon.sh gh-watch-start post-bash-register.py pre-agent-guard.py tracker-check.sh post-lint.py gate-pass pre-bash-guard.py stop-lint.py pr-steps claude-swap codex-review-model install-methodology methodology-update uninstall-methodology; do
    case "$watcher:$target:$reviewer:$f" in off:*:gh-watch*|off:*:post-bash-register.py|*:ci:*:claude-swap|*:claude:codex-review-model) continue;; esac
    lang=bash; case $f in *.py|claude-swap|codex-review-model|install-methodology) lang=python;; esac
    echo; echo "### \`$f\`"; echo; echo "\`\`\`\`$lang"; cat "$(ls claude/hooks/$f claude/bin/$f claude/watcher/$f 2>/dev/null | head -1)"; echo '````'
  done
} > "$out"
echo "built $out ($(wc -c < "$out") bytes)"
