#!/bin/bash
# local-model/install.sh [--force]: installs the local-model tooling from this folder, the only source.
# - Everything except eval/ goes to ~/local-llm (the llama.cpp build, weights, .api-key, usage/ and claude-config/ live
#   there and are never touched); eval/ goes to ~/local-llm-eval (workspaces and runs stay there).
# - Links claude-local and claude-usage into ~/.local/bin.
# - Refuses to overwrite an installed file that differs from the last install (edited in place): copy the change here,
#   commit, and re-run; --force overwrites anyway.
# Edit here, commit, push and run this in the same step.
set -e
SRC="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
STAMP=~/local-llm/.installed  # sha256 of each file as last installed
force=; [ "${1:-}" = --force ] && force=1
cd "$SRC/.."
# Repo layout -> installed layout: bin/, config/ and prompts/ go flat into ~/local-llm (the scripts find each other
# there); eval/ goes to ~/local-llm-eval.
pairs=$(git ls-files local-model | grep -v '/install.sh$' | while read -r f; do
  r=${f#local-model/}
  case $r in
    eval/*) echo "$f $HOME/local-llm-eval/${r#eval/}" ;;
    bin/*|config/*|prompts/*) echo "$f $HOME/local-llm/${r#*/}" ;;
    *) echo "$f $HOME/local-llm/$r" ;;
  esac
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
# files an earlier install put there that this version no longer has: remove them if unchanged since
awk '{print $2}' "$STAMP" | while read -r dst; do
  echo "$pairs" | awk -v d="$dst" '$2 == d {f=1} END {exit !f}' && continue
  [ -f "$dst" ] && [ "$(sha256sum "$dst" | cut -d' ' -f1)" = "$(awk -v d="$dst" '$2 == d {print $1}' "$STAMP")" ] && rm -f "$dst" && echo "removed $dst"
done
: >"$STAMP.new"
echo "$pairs" | while read -r f dst; do
  mkdir -p "$(dirname "$dst")"; cp -p "$f" "$dst"
  echo "$(sha256sum "$dst" | cut -d' ' -f1) $dst" >>"$STAMP.new"
done
mv "$STAMP.new" "$STAMP"
for c in claude-local claude-usage; do ln -sfn ~/local-llm/$c ~/.local/bin/$c; done
echo "installed $(echo "$pairs" | wc -l) files from $SRC"
