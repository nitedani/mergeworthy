#!/bin/bash
# local-model/install.sh [--force]: installs the local-model tooling from this folder, the only source.
# - Everything except eval/ goes to ~/local-llm (the llama.cpp build, weights, .api-key, usage/ and claude-config/ live
#   there and are never touched); eval/ goes to ~/local-llm-eval (workspaces and runs stay there).
# - Links claude-local, local-agent and claude-usage into ~/.local/bin, and the sandbox into ~/local-llm-eval/bin.
# - Refuses to overwrite an installed file that differs from the last install (edited in place): copy the change here,
#   commit, and re-run; --force overwrites anyway.
# Edit here, commit, push and run this in the same step.
set -e
SRC="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
STAMP=~/local-llm/.installed  # sha256 of each file as last installed
force=; [ "${1:-}" = --force ] && force=1
cd "$SRC/.."
pairs=$(git ls-files local-model | grep -v '/install.sh$' | while read -r f; do
  r=${f#local-model/}
  case $r in eval/*) echo "$f $HOME/local-llm-eval/${r#eval/}";; *) echo "$f $HOME/local-llm/$r";; esac
done)
touch "$STAMP"
if [ -z "$force" ]; then
  edited=$(echo "$pairs" | while read -r f dst; do
    [ -f "$dst" ] || continue
    last=$(awk -v d="$dst" '$2 == d {print $1}' "$STAMP")
    now=$(sha256sum "$dst" | cut -d' ' -f1)
    if [ -n "$last" ] && [ "$last" != "$now" ]; then echo "$dst"; fi
  done)
  [ -z "$edited" ] || { echo "edited in place since the last install (copy the change into $SRC first, or --force):"; echo "$edited"; exit 1; }
fi
: >"$STAMP.new"
echo "$pairs" | while read -r f dst; do
  mkdir -p "$(dirname "$dst")"; cp -p "$f" "$dst"
  echo "$(sha256sum "$dst" | cut -d' ' -f1) $dst" >>"$STAMP.new"
done
mv "$STAMP.new" "$STAMP"
for c in claude-local local-agent claude-usage; do ln -sfn ~/local-llm/$c ~/.local/bin/$c; done
for s in sandbox gh bridge.py; do ln -sfn ~/local-llm/sandbox/$s ~/local-llm-eval/bin/$s; done
echo "installed $(echo "$pairs" | wc -l) files from $SRC"
