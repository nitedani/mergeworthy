#!/bin/bash
# Prints "TRACKER STALE: ..." for every checkbox in the tracker issue ($TRACKER_REPO#$TRACKER_ISSUE) whose PR state disagrees with it:
# - [ ] on a merged PR, or - [x] on an open one. Merged-but-unreleased items stay [x]. Only PRs count: an item's first
# PR reference (owner/repo#N, #N or a pull URL) is checked; issues are skipped.
# With TRACKER_DECISIONS=<comment id>, also "TRACKER STALE: Decisions comment …" when a tracked PR merged or closed after its last edit.
body=$(gh issue view "${TRACKER_ISSUE:?set TRACKER_ISSUE}" -R "${TRACKER_REPO:?set TRACKER_REPO}" --json body -q .body 2>/dev/null) || exit 0
dec_at=""; [ -n "$TRACKER_DECISIONS" ] && dec_at=$(gh api "repos/$TRACKER_REPO/issues/comments/$TRACKER_DECISIONS" -q .updated_at 2>/dev/null)
echo "$body" | tr -d '\r' | grep -E '^[[:space:]]*[-*] \[( |x|X)\] ' | while IFS= read -r line; do
  box=$(echo "$line" | sed -E 's/^[[:space:]]*[-*] \[(.)\].*/\1/' | tr X x)
  line=$(echo "$line" | sed -E 's#https://github\.com/([^/ ]+/[^/ ]+)/(pull|issues)/([0-9]+)[^ )]*#\1\#\3#g')
  ref=$(echo "$line" | grep -oE '([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?#[0-9]+' | head -1)
  [ -z "$ref" ] && continue
  repo=${ref%#*}; num=${ref#*#}; [ -z "$repo" ] && repo=$TRACKER_REPO
  read -r state closed <<<"$(gh pr view "$num" -R "$repo" --json state,closedAt -q '"\(.state) \(.closedAt // "")"' 2>/dev/null)"
  [ -z "$state" ] && continue
  if [ -n "$dec_at" ] && [ -n "$closed" ] && [[ "$closed" > "$dec_at" ]]; then echo "TRACKER STALE: Decisions comment last edited $dec_at, before $repo#$num was ${state,,} at $closed"; fi
  if [ "$box" = " " ] && [ "$state" = "MERGED" ]; then echo "TRACKER STALE: $repo#$num is MERGED but unchecked"; fi
  if [ "$box" = "x" ] && [ "$state" = "OPEN" ]; then echo "TRACKER STALE: $repo#$num is OPEN but checked"; fi
done
