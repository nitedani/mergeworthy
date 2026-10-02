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
    while read -r f; do cat "src/$f"; done < src/ORDER
    echo; cat src/part4-failures.md; echo; cat src/part2-implement-issue.md; echo; cat src/part3-convergence.md
    echo; echo '---'; echo; cat src/part5-mechanisms.md; echo
  } | python3 filter.py $settings
  for f in gh-watch.py gh-watch-daemon.sh gh-watch-start post-bash-register.py pre-agent-guard.py tracker-check.sh post-lint.py gate-pass pre-bash-guard.py stop-lint.py pr-steps claude-swap codex-review-model install-methodology methodology-update uninstall-methodology; do
    case "$watcher:$target:$reviewer:$f" in off:*:gh-watch*|off:*:post-bash-register.py|*:ci:*:claude-swap|*:claude:codex-review-model) continue;; esac
    lang=bash; case $f in *.py|claude-swap|codex-review-model|install-methodology) lang=python;; esac
    echo; echo "### \`$f\`"; echo; echo "\`\`\`\`$lang"; cat "mechanisms/$f"; echo '````'
  done
} > "$out"
echo "built $out ($(wc -c < "$out") bytes)"
